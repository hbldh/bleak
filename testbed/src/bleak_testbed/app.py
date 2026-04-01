import toga


class BleakTestbedApp(toga.App):
    def startup(self):
        """Set up the GUI."""
        main_window = toga.MainWindow(title="Bleak Testbed")

        self.main_window = main_window
        main_window.show()


def main():
    return BleakTestbedApp()
