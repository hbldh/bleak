class MockType:
    """A generic mock class that can be subscribed."""

    def __getitem__(self, item):
        return self


def __getattr__(name):
    """Dynamically creates and returns a MockType for any requested attribute."""
    # This will handle common typing names like List, Dict, Optional, Any, etc.
    return MockType()

