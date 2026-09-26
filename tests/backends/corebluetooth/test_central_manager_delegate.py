import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

import subprocess
import threading

import pytest

# isort: off

if not sys.platform.startswith("darwin"):
    pytest.skip("backend only available on macOS", allow_module_level=True)

from libdispatch import DISPATCH_QUEUE_SERIAL, dispatch_async, dispatch_queue_create

from bleak.backends.corebluetooth import CentralManagerDelegate as module
from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate


class FakeCentralManager:
    """Records calls; a real CBCentralManager would ask the OS for Bluetooth access."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def stopScan(self) -> None:
        self.calls.append(("stopScan", None))

    def setDelegate_(self, delegate: object) -> None:
        self.calls.append(("setDelegate_", delegate))


def make_manager() -> tuple[CentralManagerDelegate, FakeCentralManager]:
    manager = object.__new__(CentralManagerDelegate)
    fake = FakeCentralManager()
    manager.central_manager = fake  # type: ignore[assignment]
    queue = dispatch_queue_create(b"test.corebluetooth", DISPATCH_QUEUE_SERIAL)
    manager._queue = queue  # pyright: ignore[reportPrivateUsage]
    return manager, fake


def test_detach_clears_the_delegate_after_queued_callbacks():
    manager, fake = make_manager()
    started = threading.Event()

    def queued_callback() -> None:
        started.set()
        fake.calls.append(("callback", None))

    queue = manager._queue  # pyright: ignore[reportPrivateUsage]
    dispatch_async(queue, queued_callback)
    started.wait(1)
    manager.detach()

    names = [name for name, _ in fake.calls]
    assert names.index("callback") < names.index("setDelegate_")
    assert fake.calls[-1] == ("setDelegate_", None)


def test_every_live_manager_is_detached_at_exit(monkeypatch: pytest.MonkeyPatch):
    first, first_fake = make_manager()
    second, second_fake = make_manager()
    monkeypatch.setattr(
        module, "_live_managers", module.weakref.WeakSet([first, second])
    )

    module._detach_all_managers()  # pyright: ignore[reportPrivateUsage]

    assert first_fake.calls[-1] == ("setDelegate_", None)
    assert second_fake.calls[-1] == ("setDelegate_", None)


def test_a_failing_manager_does_not_stop_the_others(monkeypatch: pytest.MonkeyPatch):
    broken, _ = make_manager()
    broken.central_manager = None  # type: ignore[assignment]
    working, working_fake = make_manager()
    monkeypatch.setattr(
        module, "_live_managers", module.weakref.WeakSet([broken, working])
    )

    module._detach_all_managers()  # pyright: ignore[reportPrivateUsage]

    assert working_fake.calls[-1] == ("setDelegate_", None)


def test_managers_are_detached_when_the_interpreter_exits():
    """The hook must run at a real interpreter exit, before modules are torn down."""
    script = """
from bleak.backends.corebluetooth import CentralManagerDelegate as module

class Probe:
    def detach(self):
        print("detached", flush=True)

probe = Probe()
module._live_managers.add(probe)
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "detached"
