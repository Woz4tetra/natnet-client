from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
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

        max_buffer_size: (int | None, optional). Size for server messages buffer. Defaults to None
        connection_timeout: (float | None, optional). Time to wait for the server to send back its ServerInfo when using a context, passed to `NatNetClient.connect`. Defaults to None
    """

    server_address: str = '127.0.0.1'
    local_ip_address: str = '127.0.0.1'
    use_multicast: bool = True
    multicast_address: str = '239.255.42.99'
    command_port: int = 1510
    data_port: int = 1511

    max_buffer_size: int | None = None
    connection_timeout: float | None = None
