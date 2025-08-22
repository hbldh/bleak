class MockPlatform:
    def __getattr__(self, name):
        return None

    def __call__(self):
        return None

def __getattr__(name):
    return MockPlatform()
