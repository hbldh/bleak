import asyncio

import bleak
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

# bind bleak's python logger into kivy's logger before importing python module using logging
from kivy.logger import Logger  # isort: skip
import logging  # isort: skip

logging.Logger.manager.root = Logger


class ExampleApp(App):
    def __init__(self):
        super().__init__()
        self.label = None
        self.running = True

    def build(self):
        self.scrollview = ScrollView(do_scroll_x=False, scroll_type=["bars", "content"])
        self.label = Label(font_size="10sp")
        self.scrollview.add_widget(self.label)
        return self.scrollview

    def line(self, text, empty=False):
        Logger.info("example:" + text)
        if self.label is None:
            return
        text += "\n"
        if empty:
            self.label.text = text
        else:
            self.label.text += text

    def on_stop(self):
        self.running = False

    async def example(self):
        while self.running:
            try:
                self.line("scanning")
                scanned_devices = await bleak.BleakScanner.discover(1)
                self.line("scanned", True)

                if len(scanned_devices) == 0:
                    raise bleak.exc.BleakError("no devices found")

                for device in scanned_devices:
                    self.line(f"{device.name} ({device.address})")

                for device in scanned_devices:
                    self.line(f"Connecting to {device.name} ...")
                    try:
                        async with bleak.BleakClient(device) as client:
                            for service in client.services:
                                self.line(f"  service {service.uuid}")
                                for characteristic in service.characteristics:
                                    self.line(
                                        f"  characteristic {characteristic.uuid} {hex(characteristic.handle)} ({len(characteristic.descriptors)} descriptors)"
                                    )
                    except bleak.exc.BleakError as e:
                        self.line(f"  error {e}")
                        asyncio.sleep(10)
            except bleak.exc.BleakError as e:
                self.line(f"ERROR {e}")
                await asyncio.sleep(1)
        self.line("example loop terminated", True)


async def main(app):
    await asyncio.gather(app.async_run("asyncio"), app.example())


if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)

    # app running on one thread with two async coroutines
    app = ExampleApp()
    asyncio.run(main(app))
