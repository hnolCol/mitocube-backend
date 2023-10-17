import typing
from abc import ABC, ABCMeta, abstractmethod
from threading import Lock, Thread






class JsonSerializable(ABC):
    """"""
    # ToDo: Write documentation
    # ToDo: Check if there are useful methods one can implement

    @abstractmethod
    def toJson(self) -> typing.Dict[str, typing.Any]:
        """"""
        # ToDo: Write documentation
        pass


class SingletonABCMeta(ABCMeta):  # ToDo: Move SingletonMeta to a different file
    """Thread-safe Singleton ABC meta-class."""

    #: Holds the singleton instance
    _instances = {}

    #: Lock used for multi-threading
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
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


class SingletonMeta(type):  # ToDo: Move SingletonMeta to a different file
    """Thread-safe Singleton meta-class."""

    #: Holds the singleton instance
    _instances = {}

    #: Lock used for multi-threading
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
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



class SQLConnection(metaclass=SingletonABCMeta):  # ABC
    """Singleton class that opens, shares and closes a shared connection to the configured database."""

    #: Holds the shared connection object.
    # conn = None  # Todo: Figure out type, e.g. psycopg2.connection like does not work

    def __init__(self):
        """
        The Constructor of DBConnection creates a new psycopg2.connection to the PostgreSQL database that can be shared.

        :raise Errors.
        """
        self.conn = self.getIndependentConnection()

    def __del__(self):  # ToDo: Use __del__ or __exit__? Look it up
        """
        Destructor will close the shared psycopg2.connection.

        :raise Errors.
        """
        self.closeConnection()
        # if self.conn is not None:
        #     self.conn.close()
        #     self.conn = None

    def __exit__(self):  # ToDo: Use __del__ or __exit__? Look it up
        """
        Destructor will close the shared psycopg2.connection.

        :raise Errors
        """
        self.closeConnection()
        # if self.conn is not None:
        #     self.conn.close()
        #     self.conn = None

    @abstractmethod
    def getDatabaseName(self) -> str:
        """"""
        # ToDo: Write documentation
        pass
    @abstractmethod
    def openNewConnection(self):
        """
        The method will open and return a new shared connection to the configured database and will close the
        previous shared connection.

        :raise Errors.
        :return: connection object
        :rtype: connection
        """
        pass

    @abstractmethod
    def closeConnection(self):
        """
        Closes the shared connection.

        :raise Errors.
        """
        pass

    @abstractmethod
    def getConnection(self):
        """
        Returns the currently shared psycopg2.connection object.

        :raise Errors.
        :return: connection object
        :rtype: connection
        """
        pass

    @abstractmethod
    def getIndependentConnection(self):  # Todo: Turn to static?
        """
        The method will open and return a new connection to the configured database without closing the
        existing connection. The returned connections is not shared and has to be closed manually.

        :raise Errors.
        :return: connection object
        :rtype: connection
        """
        pass