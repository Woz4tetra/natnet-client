import time
from new_natnet_client.Client import NatNetClient

if __name__ == "__main__":
  client = NatNetClient()
  with client:
    if client.connected:
      print(client.server_info)
      requested_time = time.time_ns()
      for frame_data in client.MoCap:
        print(f"Response time: {time.time_ns()-requested_time}")
        if input("Out? [N/y]").upper() == 'Y': break
        print(frame_data.rigid_body_data.rigid_bodies)
        requested_time = time.time_ns()
    else:
      print("Client didn't connect")