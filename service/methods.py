"""Forked Methods from jsonrpcserver"""
from jsonrpcserver.methods import Methods as _Methods
from .background import BackgroundTask


class Methods(_Methods):  # pylint: disable=too-many-ancestors
    """
    Holds a list of methods.
    """
    def __setitem__(self, key, value):
        # Method must be callable
        if not callable(value) and not issubclass(value, BackgroundTask):
            raise TypeError('%s is not callable or a task class' % type(value))
        self._items[key] = value


method_instance = Methods()  # pylint: disable=invalid-name
