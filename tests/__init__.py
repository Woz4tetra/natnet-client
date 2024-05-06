import time
from new_natnet_client.Client import NatNetClient

if __name__ == "__main__":
  client = NatNetClient()
  if client.connected:
    print(client.server_info)
    while input("Out? [N/y]").upper() != 'Y':
      requested_time = time.time_ns()
      frame_data = client.MoCap
      print(f"Response time: {time.time_ns()-requested_time}")
      if frame_data is not None:
        print(frame_data.rigid_body_data.rigid_bodies)
      else:
        print("Frame not received")
    client.shutdown()
  else:
    print("Client didn't connect")