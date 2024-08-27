from abc import ABCMeta
from threading import Lock


class SingletonABCMeta(ABCMeta):
    """Thread-safe Singleton ABC meta-class."""

    #: Holds the singleton instance
    _instances = {}

    #: Lock used for multi-threading
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):  # todo: documentation text as an example only, update!
        """
        Return a list of random ingredients as strings.

        :param kind: Optional "kind" of ingredients.
        :type kind: list[str] or None
        :raise lumache.InvalidKindError: If the kind is invalid.
        :return: The ingredients list.
        :rtype: list[str]
        """
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class SingletonMeta(type):
    """Thread-safe Singleton meta-class."""

    #: Holds the singleton instance
    _instances = {}

    #: Lock used for multi-threading
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):  # todo: documentation text as an example only, update!
        """
        Return a list of random ingredients as strings.

        :param kind: Optional "kind" of ingredients.
        :type kind: list[str] or None
        :raise lumache.InvalidKindError: If the kind is invalid.
        :return: The ingredients list.
        :rtype: list[str]
        """
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]
