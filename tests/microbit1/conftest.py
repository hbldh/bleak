
def pytest_addoption(parser):
    parser.addoption("--nofw", action="store_true", default=False, help="Don't update firmware (already loaded)")
