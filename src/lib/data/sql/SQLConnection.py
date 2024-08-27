from abc import abstractmethod

from lib.designpatterns import SingletonABCMeta


class SQLConnection(metaclass=SingletonABCMeta):  # ABC
    """Singleton class that opens, shares and closes a shared connection to the configured database."""

    def __del__(self):
        """
        Destructor will close the shared psycopg2.connections.

        :raise Errors.
        """
        self.closeAllConnections()

    def __exit__(self):
        """
        Destructor will close the shared psycopg2.connections.

        :raise Errors
        """
        self.closeAllConnections()

    @abstractmethod
    def closeAllConnections(self):
        """
        Closes the shared connection.

        :raise Errors.
        """
        pass

    @abstractmethod
    def getDatabaseName(self) -> str:
        """Returns the name of the database connected to."""
        pass

    @abstractmethod
    def getConnection(self):
        """
        Get a connection from the pool.

        :raise Errors.
        :return: connection object
        :rtype: connection
        """
        pass

    @abstractmethod
    def returnConnection(self, conn):
        """
        Release the connection back to the pool.

        :raise Errors.
        """
        pass
