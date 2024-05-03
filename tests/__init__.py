from new_natnet_client.Client import NatNetClient

if __name__ == "__main__":
  client = NatNetClient()
  if client.connected:
    print(client.server_info)
    while input("Out? [N/y]").upper() != 'Y':
      if client.mocap is not None:
        print(client.mocap.rigid_body_data.rigid_bodies)
      else:
        print("Frame not received")
    client.shutdown()
  else:
    print("Client didn't connect")