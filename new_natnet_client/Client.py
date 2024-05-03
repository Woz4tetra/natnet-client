from dataclasses import dataclass, field, FrozenInstanceError, InitVar, asdict
from collections import deque
import struct
from types import NoneType
from typing import Any, Tuple, Dict, Callable
import socket
import logging
from threading import Thread, Lock
from new_natnet_client.NatNetTypes import NAT_Messages, NAT_Data, MoCap
from new_natnet_client.Unpackers import DataUnpackerV3_0, DataUnpackerV4_1


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass(frozen=True)
class Server_info:
  application_name: str
  version: Tuple[int,...]
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
  mocap: MoCap | None = field(init=False, default=None)
  # Flag to control if command thread and data thread should be running
  __running: bool = field(init=False, default=False)
  __command_socket: socket.socket | None = field(init=False, repr=False, default=None)
  __data_socket: socket.socket | None = field(init=False, repr=False, default=None)
  __freeze: bool = field(init=False, repr=False, default=False)

  @property
  def connected(self) -> bool:
    return self.__running

  @property
  def server_info(self) -> Server_info:
    return self.__server_info

  @property
  def server_responses(self) -> deque[int | str]:
    with self.__server_responses_lock:
      return self.__server_responses.copy()

  @property
  def server_messages(self) -> deque[str]:
    with self.__server_messages_lock:
      return self.__server_messages.copy()

  @property
  def buffer_size(self):
    return self.__max_buffer_size

  @buffer_size.setter
  def buffer_size(self, maxlen:int):
    self.__max_buffer_size = maxlen
    with self.__server_messages_lock:
      self.__server_messages = deque(self.__server_messages,maxlen=maxlen)
    with self.__server_responses_lock:
      self.__server_responses = deque(self.__server_responses,maxlen=maxlen)

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

  def __get_message_id(self, data:bytes) -> int:
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
    self.__command_socket.settimeout(2.0)
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

  def __post_init__(self, max_buffer_size):
    self.__running_lock = Lock()
    self.__command_socket_lock = Lock()
    self.__server_info_lock = Lock()
    self.__server_responses_lock = Lock()
    self.__server_messages_lock = Lock()

    self.__max_buffer_size = max_buffer_size
    # Buffer for server responses
    self.__server_responses: deque[int | str] = deque(maxlen=self.__max_buffer_size)
    # Buffer for server messages
    self.__server_messages: deque[str] = deque(maxlen=self.__max_buffer_size)

    self.__server_info: Server_info = Server_info("None", (0,0,0,0), 0,0)

    # TODO: change to dependency injection model based 
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

    self.connect()
    self.__update_unpacker_version()

  def __setattr__(self, name:str, value:Any):
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

  def connect(self):
    if self.__running or not self.__create__command_socket() or not self.__create__data_socket(): return
    logging.info("Client connected")
    self.send_request(NAT_Messages.CONNECT,"")
    self.__running = True

    self.__command_thread = Thread(target=self.__command_thread_function)
    self.__command_thread.start()
    self.__data_thread = Thread(target=self.__data_thread_function)
    self.__data_thread.start()

  def send_request(self, NAT_command:NAT_Messages, command:str) -> int:
    if not self.__running or NAT_command == NAT_Messages.UNDEFINED: return -1
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
      if self.__command_socket is None: return -1
      return self.__command_socket.sendto(data, (self.server_address, self.command_port))

  def send_command(self, command: str):
    res:int = -1
    for _ in range(3):
      res = self.send_request(NAT_Messages.REQUEST, command)
      if res != -1:
        break
    return res != -1

  def __update_unpacker_version(self):
    self.__unpacker = DataUnpackerV3_0
    if (self.__server_info.nat_net_major == 4 and self.__server_info.nat_net_minor >= 1) or self.__server_info.nat_net_major == 0:
      self.__unpacker = DataUnpackerV4_1
    self.__mapped_data_descriptors: Dict[NAT_Data, Callable[[bytes], Tuple[Dict, int]]] = {
      NAT_Data.MARKER_SET: self.__unpacker.unpack_marker_set_description,
      NAT_Data.RIGID_BODY: self.__unpacker.unpack_rigid_body_description,
      NAT_Data.SKELETON: self.__unpacker.unpack_skeleton_description,
      NAT_Data.FORCE_PLATE: self.__unpacker.unpack_force_plate_description,
      NAT_Data.DEVICE: self.__unpacker.unpack_device_description,
      NAT_Data.CAMERA: self.__unpacker.unpack_camera_description,
      NAT_Data.ASSET: self.__unpacker.unpack_asset_description
    }

  def __unpack_mocap_data(self, data:bytes, packet_size:int):
    self.mocap, offset = self.__unpacker.unpack_mocap_data(data)
    return offset


  def __unpack_data_descriptions(self, data:bytes, packet_size:int):
    offset = 0
    dataset_count = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    for i in range(dataset_count):
      t = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      if self.__unpacker == DataUnpackerV4_1:
        size_in_bytes = int.from_bytes( data[offset:(offset:=offset+4)], byteorder='little',  signed=True )
      data_description_type = NAT_Data(t)
      if data_description_type == NAT_Data.UNDEFINED:
        logging.error(f"{data_description_type = } - ID: {t}")
        continue
      d, tmp_offset = self.__mapped_data_descriptors[data_description_type](data[offset:])
      # TODO: Updater de datos
      offset += tmp_offset
    return offset

  def __unpack_server_info(self, data: bytes, __:int) -> int:
    offset = 0
    template = {}
    # Application name info
    application_name, _, _ = data[offset:(offset:=offset+256)].partition(b'\0')
    template['application_name'] = str(application_name, "utf-8")
    # Server Version info
    template['version'] = struct.unpack( 'BBBB', data[offset:(offset:=offset+4)] )
    # NatNet Version info
    template['nat_net_major'], template['nat_net_minor'], _, _ = struct.unpack( 'BBBB', data[offset:(offset:=offset+4)] )
    with self.__server_info_lock:
      self.__server_info = Server_info(**template)
    self.__update_unpacker_version
    return offset

  def __unpack_server_response(self, data:bytes, packet_size:int) -> int:
    if packet_size == 4:
      with self.__server_responses_lock:
        self.__server_responses.append(int.from_bytes(data, byteorder='little',  signed=True ))
      return 4
    response, _, _ = data[:256].partition(b'\0')
    if len(response) < 30:
      # TODO: Unpack bit stream version
      with self.__server_responses_lock:
        self.__server_responses.append(str(response, "utf-8"))
    return len(response)

  def __unpack_server_message(self, data:bytes, __:int):
    message, _, _ = data.partition(b'\0')
    with self.__server_messages_lock:
      self.__server_messages.append(str(message, encoding='utf-8'))
    return len(message) + 1

  def __unpack_unrecognized_request(self, _:bytes, packet_size:int) -> int:
    logging.error(f"{NAT_Messages.UNRECOGNIZED_REQUEST} - {packet_size = }")
    return packet_size

  def __unpack_undefined_nat_message(self, _:bytes, packet_size:int) -> int:
    logging.error(f"{NAT_Messages.UNDEFINED} - {packet_size = }")
    return packet_size

  def __process_message(self, data: bytes):
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

  def shutdown(self):
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

  def __del__(self):
    self.shutdown()