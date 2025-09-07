class ABC(object):
    pass

def abstractmethod(func):
    """
    A decorator that raises an exception if the method is not implemented
    in a subclass.
    """
    def wrapper(*args, **kwargs):
        raise NotImplementedError(
            f"Abstract method '{func.__name__}' not implemented"
        )
    return wrapper
