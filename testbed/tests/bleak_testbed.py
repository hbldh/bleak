import os
import sys
import tempfile
from functools import partial
from pathlib import Path
from threading import Thread

import coverage
import pytest
import toga


def get_coverage_dir() -> Path:
    """Get the directory to store coverage data in."""
    if sys.platform == "android":
        # On Android, we need to store the coverage data in a directory that the app has
        # write access to, and can be accessed after the app has been closed.
        from bleak.backends.android.utils import context

        # /storage/emulated/0/Android/data/com.bleak.testbed.bleak_testbed/files
        return Path(str(context.getExternalFilesDir("")))
    else:
        return Path(tempfile.gettempdir())


class BleakTestbedApp(toga.App):
    def startup(self):
        """Set up the GUI."""
        main_window = toga.MainWindow(title="Bleak Testbed App")

        self.main_window = main_window
        main_window.show()


def run_tests(cov: coverage.Coverage):
    # Determine any args to pass to pytest. If there aren't any,
    # default to running the whole test suite.
    args = sys.argv[1:]
    if len(args) == 0:
        args = ["tests"]

    temp_dir = tempfile.gettempdir()
    cov_dir = get_coverage_dir()
    os.environ["COVERAGE_FILE"] = str(cov_dir / ".coverage")
    returncode = pytest.main(
        [
            # Turn up verbosity
            "-vv",
            # Disable color
            "--color=no",
            # Run all async tests and fixtures using pytest-asyncio.
            "--asyncio-mode=auto",
            "--override-ini",
            "asyncio_default_fixture_loop_scope=function",
            # Overwrite the cache directory to somewhere writable
            "-o",
            f"cache_dir={temp_dir}/.pytest_cache",
            # JUnit XML report
            f"--junitxml={cov_dir / 'junit.xml'}",
            "-o",
            "junit_family=legacy",
        ]
        + args,
    )

    cov.stop()
    cov.save()
    cov.html_report(directory=str(cov_dir / "htmlcov"), ignore_errors=True)
    cov.xml_report(outfile=str(cov_dir / "coverage.xml"), ignore_errors=True)

    print(f">>>>>>>>>> EXIT {returncode} <<<<<<<<<<")


def main():
    project_path = Path(__file__).parent.parent
    os.chdir(project_path)

    # Start coverage tracking.
    # This needs to happen in the main thread, before the app has been created
    cov = coverage.Coverage(
        # Don't store any coverage data
        data_file=None,
        branch=True,
        source_pkgs=["bleak"],
    )
    cov.start()

    app = BleakTestbedApp("BleakTestbed", "com.bleak.testbed.bleak_testbed")

    thread = Thread(target=partial(run_tests, cov=cov))

    # Queue a background task to run that will start the main thread. We do this,
    # instead of just starting the thread directly, so that we can make sure the App has
    # been fully initialized, and the event loop is running.
    app.loop.call_soon_threadsafe(thread.start)

    # Start the test app
    app.main_loop()


if __name__ == "__main__":
    main()
