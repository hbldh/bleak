"""
Run Bluetooth LE on Android
"""

import toga


class BleScannerApp(toga.App):
    """A small App to demonstrate Bluetooth LE functionality with bleekWare.

    bleekWare replaces Bleak on the Android platform when working with
    Toga and BeeWare (see the conditional import above).

    This app demonstrates several possibilities to perform a scan and
    read the advertised data.
    """

    def startup(self):
        """Set up the GUI."""
        main_window = toga.MainWindow(title="BLE Scanner Demo App")

        self.main_window = main_window
        main_window.show()


def main():
    return BleScannerApp()
