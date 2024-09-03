import time
import logging
import asyncio

from new_natnet_client.Client import NatNetClient, NatNetParams

async def time_test1():
    with NatNetClient(NatNetParams(...)) as client:
        if client is None: return
        total_time = 0
        num_requests = 0
        requested_time = time.time_ns()
        async for _ in client.MoCapAsync():
            response_time = time.time_ns()-requested_time
            total_time += response_time
            num_requests += 1
            if num_requests == 1_000: return
            print(f"{response_time = } | median = {total_time/num_requests}")
            requested_time = time.time_ns()

def time_test2():
    with NatNetClient(NatNetParams(...)) as client:
        if client is None: return
        total_time = 0
        num_requests = 0
        requested_time = time.time_ns()
        for _ in client.MoCap():
            response_time = time.time_ns()-requested_time
            total_time += response_time
            num_requests += 1
            if num_requests == 1_000: return
            print(f"{response_time = } | median = {total_time/num_requests}")
            requested_time = time.time_ns()

def main():
    with NatNetClient(NatNetParams(...)) as client:
        if client is None: return
        print(client.server_info)
        requested_time = time.time_ns()
        for frame_data in client.MoCap():
            print(f"Response time: {time.time_ns()-requested_time}")
            if input("Out? [N/y]").upper() == 'Y': break
            print(frame_data.rigid_body_data.rigid_bodies)
            requested_time = time.time_ns()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    NatNetClient.logger.setLevel(logging.INFO)

    main()
    asyncio.run(time_test1())
    input()
    time_test2()