[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/new-natnet-client)
![PyPI - License](https://img.shields.io/pypi/l/new-natnet-client)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Statically typed: mypy](https://img.shields.io/badge/statically%20typed-mypy-039dfc)

---

natnet client for motive applications with pure python

---

# Installation

```
python -m pip install new-natnet-client
```

# How's

## How it works on the background

1. When you try to connect to the motive application a background thread is started, in this thread is where all the data is received and unpacked.

2. A request for connection is send

3. If the motive application responds then the client starts working as expected. If a timeout value was set and no response was received on time, then the background thread stops.

## How is data represented

The data received is converted to frozen and inmutable instances of the corresponding dataclass

## How to read Motion Capture Data (MoCap) / frames

How stated before all data is received on the background, this means that reader must be synchronize for reading only when new data is received.

There are 2 ways to read:

### 1. Synchronous:

```py
def foo():
    with NatNetClient(NatNetParams(...)) as client: # Create client
        if client is None: return # Make sure client connected successfully
        for frame_data in client.MoCap(): # Start reading data
            ...
```

### 2. Asynchronous:

```py
async def foo():
    with NatNetClient(NatNetParams(...)) as client:
        if client is None: return
        async for frame_data in client.MoCapAsync():
            ...
```

## From NATNET

This package provides the client for using [Optitrack's](https://optitrack.com/) NatNet tracking system, with type hints for python.

The NatNet SDK is a simple Client/Server networking SDK for sending and receiving
data from Motive across networks.  NatNet uses the UDP protocol in conjunction
with either multicasting or point-to-point unicasting for transmitting data.

A list of changes made in each version can be found at the following website: https://www.optitrack.com/support/downloads/developer-tools.html

More about NatNet: https://docs.optitrack.com/developer-tools/natnet-sdk

---

### Disclaimer: I have no relationship with Optitrack

---