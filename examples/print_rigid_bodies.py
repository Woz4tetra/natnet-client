import time

from natnet_client.Client import NatNetClient, NatNetParams


def main() -> None:
    with NatNetClient(
        NatNetParams(server_address='10.201.1.72', local_ip_address='0.0.0.0')
    ) as client:
        print(client.server_info)
        requested_time = time.perf_counter()
        for frame_data in client.MoCap():
            print(f'Response time: {time.perf_counter() - requested_time}')
            print(frame_data.rigid_body_data.rigid_bodies)
            requested_time = time.perf_counter()
            # time.sleep(0.01)


if __name__ == '__main__':
    main()
