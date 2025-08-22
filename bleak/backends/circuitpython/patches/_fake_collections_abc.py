class MockCollections:
    def __getattr__(self, name):
        return None

    def __call__(self):
        return None

def __getattr__(name):
    return MockCollections()

class Callable:
    def __getitem__(self, item):
        return self

class Iterator:
    def __getitem__(self, item):
        return self

class Coroutine:
    def __getitem__(self, item):
        return self

class Hashable:
    def __getitem__(self, item):
        return self
