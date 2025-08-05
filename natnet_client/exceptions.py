from natnet_client.natnet_params import NatNetParams


class NatNetClientNotConnectedError(Exception):
    def __init__(self, params: NatNetParams):
        self.params = params
        super().__init__('NatNetClient not connected')