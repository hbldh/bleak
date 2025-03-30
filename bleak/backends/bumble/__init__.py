# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Victor Chavez
"""Bumble backend."""
import os
from enum import Enum
from typing import Dict, Final, Optional

from bumble.controller import Controller
from bumble.link import LocalLink
from bumble.transport import Transport, open_transport

transports: Dict[str, Transport] = {}
_link: Final = LocalLink()
_scheme_delimiter: Final = ":"

_env_transport_cfg: Final = os.getenv("BLEAK_BUMBLE")
_env_host_mode: Final = os.getenv("BLEAK_BUMBLE_HOST")


class TransportScheme(Enum):
    """The transport schemes supported by bumble.

    https://google.github.io/bumble/transports
    """

    SERIAL = "serial"
    """: The serial transport implements sending/receiving HCI
    packets over a UART (a.k.a serial port).
    """
    UDP = "udp"
    """: The UDP transport is a UDP socket, receiving packets on a specified port number,
    and sending packets to a specified host and port number.
    """
    TCP_CLIENT = "tcp-client"
    """: The TCP Client transport uses an outgoing TCP connection.
    """
    TCP_SERVER = "tcp-server"
    """: The TCP Server transport uses an incoming TCP connection.
    """
    WS_CLIENT = "ws-client"
    """: The WebSocket Client transport is WebSocket connection
    to a WebSocket server over which HCI packets are sent and received.
    """
    WS_SERVER = "ws-server"
    """: The WebSocket Server transport is WebSocket server that accepts
    connections from a WebSocket client. HCI packets are sent and received over the connection.
    """
    PTY = "pty"
    """: The PTY transport uses a Unix pseudo-terminal device to communicate
    with another process on the host, as if it were over a serial port.
    """
    FILE = "file"
    """: The File transport allows opening any named entry on a filesystem
    and use it for HCI transport I/O. This is typically used to open a PTY,
    or unix driver, not for real files.
    """
    VHCI = "vhci"
    """: The VHCI transport allows attaching a virtual controller
    to the Bluetooth stack on operating systems that offer a
    VHCI driver (Linux, if enabled, maybe others).
    """
    HCI_SOCKET = "hci-socket"
    """: An HCI Socket can send/receive HCI packets to/from a
    Bluetooth HCI controller managed by the host OS.
    This is only supported on some platforms (currently only tested on Linux).
    """
    USB = "usb"
    """: The USB transport interfaces with a local Bluetooth USB dongle.
    """
    ANDROID_NETSIM = "android-netsim"
    """: The Android "netsim" transport either connects, as a host, to a
    Netsim virtual controller ("host" mode), or acts as a virtual
    controller itself ("controller" mode) accepting host connections.
    """

    @classmethod
    def from_string(cls, value: str) -> "TransportScheme":
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"'{value}' is not a valid TransportScheme")


class BumbleTransportCfg:
    """Transport configuration for bumble.

    Args:
            scheme (TransportScheme): The transport scheme supported by bumble.
            args (Optional[str]): The arguments used to initialize the transport.
                See https://google.github.io/bumble/transports/index.html
    """

    def __init__(self, scheme: TransportScheme, args: Optional[str] = None):
        self.scheme: Final = scheme
        self.args: Final = args

    def __str__(self):
        return f"{self.scheme.value}:{self.args}" if self.args else self.scheme.value


def get_default_transport_cfg() -> BumbleTransportCfg:
    if _env_transport_cfg:
        scheme_val, *args = _env_transport_cfg.split(_scheme_delimiter, 1)
        return BumbleTransportCfg(
            TransportScheme.from_string(scheme_val), args[0] if args else None
        )

    return BumbleTransportCfg(TransportScheme.TCP_SERVER, "127.0.0.1:1234")


def get_default_host_mode() -> bool:
    return True if _env_host_mode else False


async def start_transport(
    cfg: BumbleTransportCfg, host_mode: bool = get_default_host_mode()
) -> Transport:
    transport_cmd = str(cfg)
    if transport_cmd not in transports.keys():
        transports[transport_cmd] = await open_transport(transport_cmd)
        if not host_mode:
            Controller(
                "ext",
                host_source=transports[transport_cmd].source,
                host_sink=transports[transport_cmd].sink,
                link=_link,
            )
    return transports[transport_cmd]


def get_link():
    # Assume all transports are linked
    return _link
