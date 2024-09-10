from dataclasses import dataclass, field, asdict, InitVar
from collections import deque
import struct
from typing import Tuple, ClassVar, Generator, AsyncGenerator, Protocol
import socket
import logging
import threading
import asyncio
import time

import new_natnet_client.NatNetTypes as NNT
import new_natnet_client.Unpackers as Unpackers


@dataclass(slots=True, frozen=True)
class ServerInfo:
    application_name: str
    version: Tuple[int, ...]
    nat_net_major: int
    nat_net_minor: int


@dataclass(slots=True, frozen=True, kw_only=True)
class NatNetParams:
    """
    This class represents an example dataclass.

    Args:
        server_address: (str, optional). Defaults to "127.0.0.1"
        local_ip_address: (str, optional). Defaults to "127.0.0.1"
        use_multicast: (bool, optional). Defaults to True
        multicast_address: (str, optional). Defaults to "239.255.42.99"
        command_port: (int, optional). Defaults to 1510
        data_port: (int, optional). Defaults to 1511

        max_buffer_size: (int | None, optional). Size for server responses and messages buffers. Defaults to None
        connection_timeout: (float | None, optional). Time to wait for the server to send back its ServerInfo when using a context, passed to `NatNetClient.connect`. Defaults to None
    """

    server_address: str = "127.0.0.1"
    local_ip_address: str = "127.0.0.1"
    use_multicast: bool = True
    multicast_address: str = "239.255.42.99"
    command_port: int = 1510
    data_port: int = 1511

    max_buffer_size: int | None = None
    connection_timeout: float | None = None


class NatNetClientI(Protocol):
    @property
    def params(self) -> NatNetParams: ...
    @property
    def server_info(self) -> ServerInfo: ...
    @property
    def last_new_data_time(self) -> int:
        """Time when last mocap data was received, set using time.time_ns

        Returns:
            int: time
        """
        ...

    @property
    def last_mocap_data(self) -> None | NNT.MoCap:
        """last mocap data received

        Returns:
            None|NatNetTypes.MoCap: MoCap data or None if no data has been received
        """
        ...

    @property
    def server_responses(self) -> deque[int | str]:
        """server responses

        Returns:
            deque[int|str]: copy of the internal server responses buffer
        """
        ...

    @property
    def server_messages(self) -> deque[str]:
        """server messages

        Returns:
            deque[str]: copy of the internal server messages buffer
        """
        ...

    @property
    def descriptors(self) -> NNT.Descriptors | None: ...
    def MoCap(self, timeout: float | None = None) -> Generator[NNT.MoCap, None, None]:
        """A generator used for iterating over new motion capture data received

        Args:
            timeout (float|None, optional): If no new data is received in a period of timeout the generator will stop. Defaults to None.

        Yields:
            Generator[NNT.MoCap,None,None]: Generator used for iterating

        Example:
            >>> with NatNetClient(NatNetParams(...)) as client:
            >>>     if client is not None:
            >>>         for frame in client.MoCap():
            >>>             print(frame)
        """
        ...

    async def MoCapAsync(
        self, timeout: float | None = None
    ) -> AsyncGenerator[NNT.MoCap, None]:
        """The async version of MoCap

        Args:
            timeout (float|None, optional): If no new data is received in a period of timeout the generator will stop. Defaults to None.

        Returns:
            AsyncGenerator[NNT.MoCap, None]: Async generator used for iterating

        Raises:
            asyncio.InvalidStateError: If you try to use the same client over 2 different event loops at the same time

        Example:
        >>> async def main():
        >>>     with NatNetClient(NatNetParams(...)) as client:
        >>>         if client is None:return
        >>>         async for frame in client.MoCap():
        >>>             print(frame)
        >>> asyncio.run(main())
        """
        ...

    def connect(self, timeout: float | None = None) -> bool:
        """Tries to connect to the NatNetServer, sends a CONNECT request to the server

        Args:
            timeout (float|None, optional): Time to wait for the server to send back its ServerInfo. Defaults to None.

        Returns:
            bool: whether the ServerInfo was received before the
        """
        ...

    def shutdown(self) -> None:
        """Closes the connection made before

        Raises:
            RuntimeError. If there is no connection
        """
        ...

    def send_request(self, NAT_command: NNT.NAT_Messages, command: str) -> int:
        """send request to the server

        Args:
            NAT_command (NNT.NAT_Messages): Message type
            command (str): Command to send

        Returns:
            int: data send by the socket

        Raises:
            RuntimeError. If there is no connection or the NAT_Message is UNDEFINED
        """
        ...

    def send_command(self, command: str) -> bool:
        """send an string command with 3 tries

        Args:
            command (str): Command to send

        Returns:
            bool: whether sending the command was successful
        """
        ...


@dataclass
class NatNetClient(NatNetClientI):
    logger: ClassVar[logging.Logger] = logging.getLogger("NatNet")

    init_params: InitVar[NatNetParams]

    _server_info: ServerInfo = field(init=False)
    _command_socket: socket.socket = field(init=False, repr=False)
    _data_socket: socket.socket = field(init=False, repr=False)
    _bg_thread: threading.Thread = field(init=False)
    _loop: asyncio.AbstractEventLoop = field(init=False)
    _ready: threading.Event = field(init=False, default_factory=threading.Event)
    _server_ready: threading.Event = field(init=False, default_factory=threading.Event)
    # _server_ready_async: asyncio.Event = field(init=False, default_factory=asyncio.Event)
    _stop: asyncio.Event = field(init=False, default_factory=asyncio.Event)

    _server_responses_lock: threading.Lock = field(
        init=False, default_factory=threading.Lock
    )
    _server_messages_lock: threading.Lock = field(
        init=False, default_factory=threading.Lock
    )

    # Motion capture values synchronization
    _last_new_data_time: int = field(init=False, default=-1)
    _mocap: NNT.MoCap | None = field(init=False, default=None)
    _mocap_synchronous_event: threading.Event = field(
        init=False, default_factory=threading.Event
    )
    _mocap_loop: asyncio.AbstractEventLoop | None = field(init=False, default=None)
    _mocap_asynchronous_event: asyncio.Event = field(
        init=False, default_factory=asyncio.Event
    )

    _descriptors: NNT.Descriptors | None = field(init=False, default=None)
    _can_change_bitstream: bool = field(init=False, default=False)

    def __post_init__(self, init_params: NatNetParams) -> None:
        self._params = init_params
        self._server_responses_lock = threading.Lock()
        self._server_messages_lock = threading.Lock()
        self._server_responses: deque[int | str] = deque(
            maxlen=self._params.max_buffer_size
        )
        self._server_messages: deque[str] = deque(maxlen=self._params.max_buffer_size)

    # TODO: Add bitstream change support

    @property
    def params(self) -> NatNetParams:
        return self._params

    @property
    def server_info(self) -> ServerInfo:
        return self._server_info

    @property
    def last_new_data_time(self) -> int:
        return self._last_new_data_time

    @property
    def last_mocap_data(self) -> None | NNT.MoCap:
        return self._mocap

    @property
    def server_responses(self) -> deque[int | str]:
        with self._server_responses_lock:
            return self._server_responses.copy()

    @property
    def server_messages(self) -> deque[str]:
        with self._server_messages_lock:
            return self._server_messages.copy()

    @property
    def descriptors(self) -> NNT.Descriptors | None:
        return self._descriptors

    def MoCap(self, timeout: float | None = None) -> Generator[NNT.MoCap, None, None]:
        while self._mocap_synchronous_event.wait(timeout):
            yield self._mocap  # type: ignore
            self._mocap_synchronous_event.clear()

    async def MoCapAsync(
        self, timeout: float | None = None
    ) -> AsyncGenerator[NNT.MoCap, None]:
        if self._mocap_loop is None:
            asyncio.InvalidStateError("Only one event loop can read at a time")
        self._mocap_loop = asyncio.get_running_loop()
        try:
            while await asyncio.wait_for(
                self._mocap_asynchronous_event.wait(), timeout
            ):
                yield self._mocap  # type: ignore
                self._mocap_asynchronous_event.clear()
        except asyncio.TimeoutError:
            return
        finally:
            self._mocap_loop = None
            self._mocap_asynchronous_event.clear()

    @staticmethod
    def create_socket(ip: str, proto: int, port: int = 0) -> socket.socket | None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, proto)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # Connect to the IP with a dynamically assigned port
            sock.setblocking(False)
            sock.bind((ip, port))
            return sock
        except socket.error as msg:
            NatNetClient.logger.error(msg)
            sock.close()
            return None

    def _create_command_socket(self) -> None:
        ip = self._params.local_ip_address
        proto = socket.IPPROTO_UDP
        if self._params.use_multicast:
            # Let system decide protocol
            proto = 0
        self._command_socket = self.create_socket(ip, proto)  # type: ignore
        if self._command_socket is None:
            self.logger.error(
                "Error while creating command socket.\nCheck Motive/Server mode requested mode agreement.\n%s",
                self._params,
            )
            return
        if self._params.use_multicast:
            # set to broadcast mode
            self._command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def _create_data_socket(self) -> None:
        ip = "0.0.0.0"
        proto = socket.IPPROTO_UDP
        port = 0
        if self._params.use_multicast:
            proto = 0
            port = self._params.data_port
        self._data_socket = self.create_socket(ip, proto, port)  # type: ignore
        if self._data_socket is None:
            self.logger.error(
                "Error while creating data socket.\nCheck Motive/Server mode requested mode agreement.\n%s",
                self._params,
            )
            return
        if (
            self._params.use_multicast
        ):
            self._data_socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(self._params.multicast_address)
                + socket.inet_aton(self._params.local_ip_address),
            )

    async def _start_data(self):
        asyncio.create_task(self._data_task())
        if not self._params.use_multicast:
            asyncio.create_task(self._keep_alive_task())

    def connect(self, timeout: float | None = None) -> bool:
        if self._ready.is_set():
            raise RuntimeError("You are already connected")
        self._create_command_socket()
        if self._command_socket is None:
            return False
        self.logger.debug("command socket created")
        self._create_data_socket()
        if self._data_socket is None:
            self._command_socket.close()
            return False
        self.logger.debug("data socket created")
        self.logger.info("Client connected")
        self._bg_thread = threading.Thread(
            target=asyncio.run, args=(self._main_task(),)
        )
        self._bg_thread.start()
        self._ready.wait()
        self.send_request(NNT.NAT_Messages.CONNECT, "")
        connected = self._server_ready.wait(timeout)
        if not connected:
            self.shutdown()
        else:
            asyncio.run_coroutine_threadsafe(self._start_data(), self._loop)
        return connected

    def shutdown(self) -> None:
        if not self._ready.is_set():
            raise RuntimeError("You are not connected")
        self.logger.info("Shuting down client")
        self._ready.clear()
        self._loop.call_soon_threadsafe(self._stop.set)
        self._bg_thread.join()
        self._command_socket.close()
        self._data_socket.close()
        self._server_ready.clear()
        self.logger.info("Client shutdown")

    def __enter__(self) -> NatNetClientI | None:
        if not self.connect(self._params.connection_timeout):
            return None
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self._ready.is_set():
            return
        self.shutdown()

    async def _send_request(self, data: bytes) -> int:
        return await self._loop.sock_sendto(
            self._command_socket,
            data,
            (self._params.server_address, self._params.command_port),
        )

    def send_request(self, NAT_command: NNT.NAT_Messages, command: str) -> int:
        if not self._ready.is_set():
            raise RuntimeError("You are not connected")
        if NAT_command is NNT.NAT_Messages.UNDEFINED:
            raise RuntimeError("You cannot send an UNDEFINED request")
        packet_size: int = 0
        if (
            NAT_command is NNT.NAT_Messages.KEEP_ALIVE
            or NAT_command is NNT.NAT_Messages.REQUEST_MODEL_DEF
            or NAT_command is NNT.NAT_Messages.REQUEST_FRAME_OF_DATA
        ):
            command = ""
        elif NAT_command is NNT.NAT_Messages.REQUEST:
            packet_size = len(command) + 1
        elif NAT_command is NNT.NAT_Messages.CONNECT:
            tmp_version = [4, 1, 0, 0]
            command = (
                "Ping".ljust(265, "\x00")
                + chr(tmp_version[0])
                + chr(tmp_version[1])
                + chr(tmp_version[2])
                + chr(tmp_version[3])
                + "\x00"
            )
        packet_size = len(command) + 1
        data = NAT_command.value.to_bytes(2, byteorder="little", signed=True)
        data += packet_size.to_bytes(2, byteorder="little", signed=True)
        data += command.encode("utf-8")
        data += b"\0"
        future = asyncio.run_coroutine_threadsafe(self._send_request(data), self._loop)
        return future.result()

    def send_command(self, command: str) -> bool:
        res: int = -1
        for _ in range(3):
            res = self.send_request(NNT.NAT_Messages.REQUEST, command)
            if res != -1:
                break
        return res != -1

    def _update_unpacker_version(self) -> None:
        """
        Changes unpacker version based on server's bit stream version
        """
        self._unpacker = Unpackers.DataUnpackerV3_0
        if (
            self._server_info.nat_net_major == 4
            and self._server_info.nat_net_minor >= 1
        ) or self._server_info.nat_net_major == 0:
            self._unpacker = Unpackers.DataUnpackerV4_1
        self._server_ready.set()

    def _unpack_mocap_data(self, data: bytes, packet_size: int) -> None:
        self._last_new_data_time = time.time_ns()
        self._mocap = self._unpacker.unpack_mocap_data(data)
        self._mocap_synchronous_event.set()
        if self._mocap_loop is not None:
            self._mocap_loop.call_soon_threadsafe(self._mocap_asynchronous_event.set)

    def _unpack_data_descriptions(self, data: bytes, packet_size: int) -> None:
        self._descriptors = self._unpacker.unpack_descriptors(data)

    def _unpack_server_info(self, data: bytes, packet_size: int) -> None:
        offset = 0
        application_name_bytes, _, _ = data[
            offset : (offset := offset + 256)
        ].partition(b"\0")
        application_name = str(application_name_bytes, "utf-8")
        version = struct.unpack("BBBB", data[offset : (offset := offset + 4)])
        nat_net_major, nat_net_minor, _, _ = struct.unpack(
            "BBBB", data[offset : (offset := offset + 4)]
        )
        self._server_info = ServerInfo(
            application_name, version, nat_net_major, nat_net_minor
        )
        self._update_unpacker_version()
        if nat_net_major >= 4 and self._params.use_multicast is False:
            self._can_change_bitstream = True

    def _unpack_server_response(self, data: bytes, packet_size: int) -> None:
        if packet_size == 4:
            with self._server_responses_lock:
                self._server_responses.append(
                    int.from_bytes(data, byteorder="little", signed=True)
                )
            return
        response_bytes, _, _ = data[:256].partition(b"\0")
        if len(response_bytes) > 30:
            return
        response = response_bytes.decode("utf-8")
        messageList = response.split(",")
        if len(messageList) > 1 and messageList[0] == "Bitstream":
            nn_version = messageList[1].split(".")
            template = asdict(self._server_info)
            if len(nn_version) > 1:
                template["nat_net_major"] = int(nn_version[0])
                template["nat_net_minor"] = int(nn_version[1])
                self._server_info = ServerInfo(**template)
                self._update_unpacker_version()
        with self._server_responses_lock:
            self._server_responses.append(response)

    def _unpack_server_message(self, data: bytes, packet_size: int) -> None:
        message, _, _ = data.partition(b"\0")
        with self._server_messages_lock:
            self._server_messages.append(str(message, encoding="utf-8"))

    def _unpack_unrecognized_request(self, _: bytes, packet_size: int) -> None:
        self.logger.debug(
            "%s - packet_size: %i", NNT.NAT_Messages.UNRECOGNIZED_REQUEST, packet_size
        )

    def _unpack_undefined_nat_message(self, _: bytes, packet_size: int) -> None:
        self.logger.debug(
            "%s - packet_size: %i", NNT.NAT_Messages.UNDEFINED, packet_size
        )

    def _process_message(self, data: bytes) -> None:
        offset = 0
        message_id = int.from_bytes(
            data[offset : (offset := offset + 2)], byteorder="little", signed=True
        )
        message = NNT.NAT_Messages(message_id)
        packet_size = int.from_bytes(
            data[offset : (offset := offset + 2)], byteorder="little", signed=True
        )
        if message is NNT.NAT_Messages.FRAME_OF_DATA:
            self._unpack_mocap_data(data[offset:], packet_size)
        elif message is NNT.NAT_Messages.MODEL_DEF:
            self._unpack_data_descriptions(data[offset:], packet_size)
        elif message is NNT.NAT_Messages.SERVER_INFO:
            self._unpack_server_info(data[offset:], packet_size)
        elif message is NNT.NAT_Messages.RESPONSE:
            self._unpack_server_response(data[offset:], packet_size)
        elif message is NNT.NAT_Messages.MESSAGE_STRING:
            self._unpack_server_message(data[offset:], packet_size)
        elif message is NNT.NAT_Messages.UNRECOGNIZED_REQUEST:
            self._unpack_unrecognized_request(data[offset:], packet_size)
        elif message is NNT.NAT_Messages.UNDEFINED:
            self._unpack_undefined_nat_message(data[offset:], packet_size)

    async def _main_task(self) -> None:
        self._loop = asyncio.get_running_loop()
        asyncio.create_task(self._command_task())
        self._ready.set()
        await self._stop.wait()

    async def _data_task(self) -> None:
        data = bytes()
        self.logger.info("Data task started")
        recv_buffer_size = 64 * 1024
        while True:
            try:
                data = await asyncio.wait_for(
                    self._loop.sock_recv(self._data_socket, recv_buffer_size), 3
                )
            except asyncio.TimeoutError:
                self.logger.debug("Data socket timeout")
                data = bytes()
            except Exception as msg:
                self.logger.error("Data error %s: %s", self._params, msg)
                data = bytes()
            if len(data):
                self._process_message(data)

    async def _command_task(self) -> None:
        data = bytes()
        self.logger.info("Command task")
        recv_buffer_size = 64 * 1024
        while True:
            try:
                data = await asyncio.wait_for(
                    self._loop.sock_recv(self._command_socket, recv_buffer_size), 3
                )
            except asyncio.TimeoutError:
                self.logger.debug("Command socket timeout")
                data = bytes()
            except Exception as msg:
                self.logger.error("Command error %s: %s", self._params, msg)
                data = bytes()
            if len(data):
                self._process_message(data)

    async def _keep_alive_task(self) -> None:
        self.logger.info("Command thread start")
        keep_alive = b"\n\x00\x00\x00\x00"
        while True:
            await self._loop.sock_sendto(
                self._command_socket,
                keep_alive,
                (self._params.server_address, self._params.command_port),
            )
            await asyncio.sleep(3)
