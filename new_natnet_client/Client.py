from dataclasses import dataclass, field, FrozenInstanceError, InitVar, asdict
from collections import deque
import struct
from types import NoneType, TracebackType
from typing import Any, Optional, Tuple, Dict, Callable, Iterator, Type
import socket
import logging
from threading import Thread, Lock
from new_natnet_client.NatNetTypes import NAT_Messages, NAT_Data, MoCap, Descriptors
from new_natnet_client.Unpackers import DataUnpackerV3_0, DataUnpackerV4_1
from copy import copy, deepcopy
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass(slots=True)
class Server_info:
  application_name: str
  version: Tuple[int, ...]
  nat_net_major: int
  nat_net_minor: int

@dataclass(kw_only=True)
class NatNetClient:
  server_address: str = "127.0.0.1"
  local_ip_address: str = "127.0.0.1"
  use_multicast: bool = True
  multicast_address: str ="239.255.42.99"
  command_port: int = 1510
  data_port: int = 1511
  max_buffer_size: InitVar[int] = 255
  __mocap_bytes: bytes | None = field(init=False, default=None)
  __new_data_flag: bool = field(init=False, default=False)
  __descriptors: Descriptors = field(init=False, default_factory=Descriptors)
  __can_change_bitstream: bool = field(init=False, default=False)
  __running: bool = field(init=False, default=False)
  __command_socket: socket.socket | None = field(init=False, repr=False, default=None)
  __data_socket: socket.socket | None = field(init=False, repr=False, default=None)
  __freeze: bool = field(init=False, repr=False, default=False)

  # TODO: Add bitstream change support

  @property
  def connected(self) -> bool:
    return self.__running

  @property
  def server_info(self) -> Server_info:
    with self.__server_info_lock:
      return copy(self.__server_info)

  @property
  def MoCap(self) -> Iterator[MoCap]:
    if  self.__mocap_bytes is None: raise StopIteration
    while True:
      with self.__mocap_bytes_lock:
        if self.__new_data_flag:
          yield self.__unpacker.unpack_mocap_data(self.__mocap_bytes)

  @property
  def server_responses(self) -> deque[int | str]:
    with self.__server_responses_lock:
      return self.__server_responses.copy()

  @property
  def server_messages(self) -> deque[str]:
    with self.__server_messages_lock:
      return self.__server_messages.copy()

  @property
  def buffer_size(self) -> int:
    """
      Buffer size for messages/responses queues
    """
    return self.__max_buffer_size

  @buffer_size.setter
  def buffer_size(self, max_len: int) -> None:
    self.__max_buffer_size = max_len
    with self.__server_messages_lock:
      self.__server_messages = deque(self.__server_messages,maxlen=max_len)
    with self.__server_responses_lock:
      self.__server_responses = deque(self.__server_responses,maxlen=max_len)

  @property
  def frozen_descriptors(self) -> Descriptors:
    return deepcopy(self.__descriptors)
  
  @property
  def descriptors(self) -> Descriptors:
    return self.__descriptors

  @staticmethod
  def create_socket(ip: str, proto: int, port: int = 0) -> socket.socket | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, proto)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
      # Connect to the IP with a dynamically assigned port
      sock.bind((ip, port))
      sock.settimeout(3)
      return sock
    except socket.error as msg:
      logging.error(msg)
      sock.close()

  def __get_message_id(self, data: bytes) -> int:
    message_id = int.from_bytes( data[0:2], byteorder='little',  signed=True )
    return message_id

  def __create__command_socket(self) -> bool:
    ip = self.local_ip_address
    proto = socket.IPPROTO_UDP
    if self.use_multicast:
      ip = ''
      # Let system decide protocol
      proto = 0
    self.__command_socket = self.create_socket(ip, proto)
    if type(self.__command_socket) == NoneType:
      logging.info(f"Command socket. Check Motive/Server mode requested mode agreement.  {self.use_multicast = } ")
      return False
    if self.use_multicast:
      # set to broadcast mode
      self.__command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    return True

  def __create__data_socket(self) -> bool:
    ip = ''
    proto = socket.IPPROTO_UDP
    port = 0
    if self.use_multicast:
      ip = self.local_ip_address
      proto = 0
      port = self.data_port
    self.__data_socket = self.create_socket(ip, proto, port)
    if type(self.__data_socket) == NoneType:
      logging.info(f"Data socket. Check Motive/Server mode requested mode agreement.  {self.use_multicast = } ")
      return False
    if self.use_multicast or self.multicast_address != "255.255.255.255":
      self.__data_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.multicast_address) + socket.inet_aton(self.local_ip_address))
    return True

  def __post_init__(self, max_buffer_size: int) -> None:
    self.__running_lock = Lock()
    self.__command_socket_lock = Lock()
    self.__server_info_lock = Lock()
    self.__server_responses_lock = Lock()
    self.__server_messages_lock = Lock()
    self.__mocap_bytes_lock = Lock()

    self.__max_buffer_size = max_buffer_size
    # Buffer for server responses
    self.__server_responses: deque[int | str] = deque(maxlen=self.__max_buffer_size)
    # Buffer for server messages
    self.__server_messages: deque[str] = deque(maxlen=self.__max_buffer_size)

    self.__server_info: Server_info = Server_info("None", (0,0,0,0), 0,0)
    
    # Map unpacking methods with respective messages
    self.__mapped: Dict[NAT_Messages, Callable[[bytes,int], int] ] = {
      NAT_Messages.FRAME_OF_DATA: self.__unpack_mocap_data,
      NAT_Messages.MODEL_DEF: self.__unpack_data_descriptions,
      NAT_Messages.SERVER_INFO: self.__unpack_server_info,
      NAT_Messages.RESPONSE: self.__unpack_server_response,
      NAT_Messages.MESSAGE_STRING: self.__unpack_server_message,
      NAT_Messages.UNRECOGNIZED_REQUEST: self.__unpack_unrecognized_request,
      NAT_Messages.UNDEFINED: self.__unpack_undefined_nat_message
    }

    self.__update_unpacker_version()

  def __setattr__(self, name: str, value: Any) -> None:
    if self.__freeze and name in (
      "server_address",
      "local_ip_address",
      "use_multicast",
      "multicast_address",
      "command_port",
      "data_port",
    ):
      raise FrozenInstanceError("This attribute can't be changed because client is already connected")
    super().__setattr__(name, value)

  def connect(self) -> None:
    if self.__running or not self.__create__command_socket() or not self.__create__data_socket(): return
    logging.info("Client connected")
    self.__running = True
    self.__data_thread = Thread(target=self.__data_thread_function)
    self.__data_thread.start()
    self.__command_thread = Thread(target=self.__command_thread_function)
    self.__command_thread.start()
    time.sleep(1) # wait to get threads running for receiving data
    self.send_request(NAT_Messages.CONNECT,"")

  def __enter__(self):
    self.connect()
    return self

  def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
    if self.__running:
      self.shutdown()

  def send_request(self, NAT_command: NAT_Messages, command: str) -> int:
    """
      Send request to server
      
      Returns:
      ---
        int: number of bytes send, (-1) if something went wrong
    """
    if type(self.__command_socket) == NoneType or NAT_command == NAT_Messages.UNDEFINED: return -1
    packet_size: int = 0
    if  NAT_command == NAT_Messages.KEEP_ALIVE or \
        NAT_command == NAT_Messages.REQUEST_MODEL_DEF or \
        NAT_command == NAT_Messages.REQUEST_FRAME_OF_DATA:
      command = ""
    elif NAT_command == NAT_Messages.REQUEST:
      packet_size = len(command) + 1
    elif NAT_command == NAT_Messages.CONNECT:
      tmp_version = [4,1,0,0]
      command = ("Ping".ljust(265, '\x00') + \
                  chr(tmp_version[0]) + \
                  chr(tmp_version[1]) + \
                  chr(tmp_version[2]) + \
                  chr(tmp_version[3]) + \
                  '\x00')
      packet_size = len(command) + 1
    data = NAT_command.value.to_bytes(2, byteorder="little", signed=True)
    data += packet_size.to_bytes(2, byteorder='little',  signed=True)
    data += command.encode("utf-8")
    data += b'\0'
    with self.__command_socket_lock:
      return self.__command_socket.sendto(data, (self.server_address, self.command_port))

  def send_command(self, command: str) -> bool:
    """
      Tries to send the command 3 times

      Returns:
        bool: whether the was send successfully
    """
    res:int = -1
    for _ in range(3):
      res = self.send_request(NAT_Messages.REQUEST, command)
      if res != -1:
        break
    return res != -1

  def __update_unpacker_version(self) -> None:
    """
      Changes unpacker version based on server's bit stream version
    """
    self.__unpacker = DataUnpackerV3_0
    with self.__server_info_lock:
      if (self.__server_info.nat_net_major == 4 and self.__server_info.nat_net_minor >= 1) or self.__server_info.nat_net_major == 0:
        self.__unpacker = DataUnpackerV4_1

  def __unpack_mocap_data(self, data: bytes, packet_size: int) -> int:
    with self.__mocap_bytes_lock:
      self.__new_data_flag = True
      self.__mocap_bytes = data
    return packet_size

  def __unpack_data_descriptions(self, data: bytes, packet_size: int) -> int:
    offset = 0
    dataset_count = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    size_in_bytes = -1
    for _ in range(dataset_count):
      tag = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      data_description_type = NAT_Data(tag)
      if self.__unpacker == DataUnpackerV4_1:
        size_in_bytes = int.from_bytes( data[offset:(offset:=offset+4)], byteorder='little',  signed=True )
      match data_description_type:
        case NAT_Data.MARKER_SET:
          description, tmp_offset = self.__unpacker.unpack_marker_set_description(data[offset:])
          self.__descriptors.marker_set_description.update(description)
        case NAT_Data.RIGID_BODY:
          description, tmp_offset = self.__unpacker.unpack_rigid_body_description(data[offset:])
          self.__descriptors.rigid_body_description.update(description)
        case NAT_Data.SKELETON:
          description, tmp_offset = self.__unpacker.unpack_skeleton_description(data[offset:])
          self.__descriptors.skeleton_description.update(description)
        case NAT_Data.FORCE_PLATE:
          description, tmp_offset = self.__unpacker.unpack_force_plate_description(data[offset:])
          self.__descriptors.force_plate_description.update(description)
        case NAT_Data.DEVICE:
          description, tmp_offset = self.__unpacker.unpack_device_description(data[offset:])
          self.__descriptors.device_description.update(description)
        case NAT_Data.CAMERA:
          description, tmp_offset = self.__unpacker.unpack_camera_description(data[offset:])
          self.__descriptors.camera_description.update(description)
        case NAT_Data.ASSET:
          description, tmp_offset = self.__unpacker.unpack_asset_description(data[offset:])
          self.__descriptors.asset_description.update(description)
        case NAT_Data.UNDEFINED:
          logging.error(f"ID: {tag} - Size: {size_in_bytes}")
          continue
      offset += tmp_offset
    return offset

  def __unpack_server_info(self, data: bytes, __: int) -> int:
    offset = 0
    application_name, _, _ = data[offset:(offset:=offset+256)].partition(b'\0')
    application_name = str(application_name, "utf-8")
    version = struct.unpack( 'BBBB', data[offset:(offset:=offset+4)] )
    nat_net_major, nat_net_minor, _, _ = struct.unpack( 'BBBB', data[offset:(offset:=offset+4)] )
    with self.__server_info_lock:
      self.__server_info = Server_info(application_name, version, nat_net_major, nat_net_minor)
    self.__update_unpacker_version
    if nat_net_major >= 4 and self.use_multicast == False:
      self.__can_change_bitstream = True
    return offset

  def __unpack_server_response(self, data: bytes, packet_size: int) -> int:
    if packet_size == 4:
      with self.__server_responses_lock:
        self.__server_responses.append(int.from_bytes(data, byteorder='little',  signed=True ))
      return 4
    response, _, _ = data[:256].partition(b'\0')
    if len(response) < 30:
      response = response.decode('utf-8')
      if response.startswith('Bitstream'):
        messageList = response.split(',')
        if len(messageList) > 1 and messageList[0] == 'Bitstream':
          nn_version = messageList[1].split('.')
          with self.__server_info_lock:
            template = asdict(self.__server_info)
          if len(nn_version) > 1:
            template["nat_net_major"] = int(nn_version[0])
            template["nat_net_minor"] = int(nn_version[1])
            with self.__server_info_lock:
              self.__server_info = Server_info(**template)
            self.__update_unpacker_version()
      with self.__server_responses_lock:
        self.__server_responses.append(response)
    return len(response)

  def __unpack_server_message(self, data: bytes, __: int) -> int:
    message, _, _ = data.partition(b'\0')
    with self.__server_messages_lock:
      self.__server_messages.append(str(message, encoding='utf-8'))
    return len(message) + 1

  def __unpack_unrecognized_request(self, _: bytes, packet_size: int) -> int:
    logging.error(f"{NAT_Messages.UNRECOGNIZED_REQUEST} - {packet_size = }")
    return packet_size

  def __unpack_undefined_nat_message(self, _: bytes, packet_size: int) -> int:
    logging.error(f"{NAT_Messages.UNDEFINED} - {packet_size = }")
    return packet_size

  def __process_message(self, data: bytes) -> None:
    offset = 0
    message_id = NAT_Messages(self.__get_message_id(data[offset:(offset:=offset+2)]))
    packet_size = int.from_bytes( data[offset:(offset:=offset+2)], byteorder='little', signed=True)
    if message_id not in self.__mapped:
      return
    self.__mapped[message_id](data[offset:], packet_size)

  def __data_thread_function(self) -> None:
    data = bytes()
    logging.info("Data thread start")
    recv_buffer_size=64*1024
    run = True
    while run:
      with self.__running_lock:
        run = self.__running
      try:
        if self.__data_socket is None: return
        data = self.__data_socket.recv(recv_buffer_size)
      except socket.timeout:
        pass
      except socket.error as msg:
        logging.error(f"Data thread {self.local_ip_address}: {msg}")
        data = bytes()
      if len(data):
        self.__process_message(data)
    logging.info("Data thread stopped")

  def __command_thread_function(self) -> None:
    data = bytes()
    logging.info("Command thread start")
    recv_buffer_size=64*1024
    run = True
    while run:
      with self.__running_lock:
        run = self.__running
      try:
        with self.__command_socket_lock:
          if self.__command_socket is None: return
          data = self.__command_socket.recv(recv_buffer_size)
      except socket.timeout:
        data = bytes()
      except socket.error as msg:
        logging.error(f"Command thread {self.local_ip_address}: {msg}")
        data = bytes()
      if len(data):
        self.__process_message(data)
    logging.info("Command thread stopped")

  def shutdown(self) -> None:
    logging.info(f"Shuting down client {self.server_address}")
    with self.__running_lock:
      self.__running = False
    with self.__command_socket_lock:
      if self.__command_socket is not None:
        self.__command_socket.close()
    if self.__data_socket is not None:
      self.__data_socket.close()
    self.__command_socket = None
    self.__data_socket = None
    self.__data_thread.join()
    self.__command_thread.join()
    self.__freeze = False

  def __del__(self) -> None:
    self.shutdown()