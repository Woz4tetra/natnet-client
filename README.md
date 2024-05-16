[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/new-natnet-client)
![PyPI - License](https://img.shields.io/pypi/l/new-natnet-client)


This package provides the client for using [Optitrack's](https://optitrack.com/) NatNet tracking system, with type hints for python.

The NatNet SDK is a simple Client/Server networking SDK for sending and receiving
data from Motive across networks.  NatNet uses the UDP protocol in conjunction
with either multicasting or point-to-point unicasting for transmitting data.

A list of changes made in each version can be found at the following website: https://www.optitrack.com/support/downloads/developer-tools.html

More about NatNet: https://docs.optitrack.com/developer-tools/natnet-sdk

---
I have no relationship with Optitrack
---
![image](https://github.com/IgnaciodelaTorreArias/natnet-client/assets/91571670/ca288adb-9b39-4f49-9012-5f3a3a5b8300)

When firs started the client has default parameters.
Once the client is created, inmediatly after it will try to connect, if it was succesful the property *conected* will be set.

Once the client is set it will start receiving data, probably the data you want to access is MoCap (Motion Capture) which is data send every frame. This data is stored has a property and used as an iterable.

The data in this properties depends both on the natnet version used by the Motive app and its configuration.
You can also send requests or commands with the respective methods, the responses and messages from the server (Motive app) will be stored has a queue, with a maximum size of buffer_size which is pased when you first start the client.
