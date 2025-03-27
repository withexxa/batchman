import functools
from types import MethodType


class autoinit:
    """
    Decorator that automatically initializes the first argument if it's a class.

    Example:
        @autoinit
        def my_method(self, x, y):
            return self.value + x + y

        # Can be called as:
        MyClass.my_method(1, 2)  # Will create instance automatically
        my_instance.my_method(1, 2)  # Works normally with instance
    """

    def __init__(self, f):
        self.f = f
        functools.update_wrapper(self, f)

    def __get__(self, obj, cls=None):
        if obj is None:
            return MethodType(self.f, cls())

        return MethodType(self.f, obj)
