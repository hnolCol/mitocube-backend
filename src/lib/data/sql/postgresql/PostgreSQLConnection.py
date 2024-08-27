from config import get_system_settings

from lib.data.sql.SQLConnection import SQLConnection

try:
    from psycopg2 import pool
except:
    pass


# DB_SETTINGS = get_db_settings()  # Setup proper config


class PostgreSQLConnection(SQLConnection):  # (metaclass=SingletonMeta):
    """Singleton class that opens, shares and closes a shared psycopg2.connection to the configured database."""

    def __init__(self):
        """
        The Constructor of DBConnection creates a new psycopg2.pool.ThreadedConnectionPool to the PostgreSQL database that can be shared.

        :raise Errors.
        """
        CONF = get_system_settings()

        print(CONF)

        self.__db_ip: str = CONF.db_ip
        self.__db_port: str = CONF.db_port
        self.__db_name: str = CONF.db_name.get_secret_value()
        self.__db_user: str = CONF.db_user.get_secret_value()
        self.__db_pw: str = CONF.db_pw.get_secret_value()

        # https://pynative.com/psycopg2-python-postgresql-connection-pooling/#h-threadedconnectionpool
        self.__db_pool = pool.ThreadedConnectionPool(minconn=CONF.db_pool_connections_n_min,
                                                     maxconn=CONF.db_pool_connections_n_max,
                                                     user=self.__db_user,
                                                     password=self.__db_pw,
                                                     host=self.__db_ip,
                                                     port=self.__db_port,
                                                     database=self.__db_name)

    def getDatabaseName(self):
        """Returns the name of the database connected to."""
        # ToDo: Write documentation
        return self.__db_name

    def closeAllConnections(self):
        """
        Closes the shared connection.

        :raise Errors.
        """
        self.__db_pool.closeall()

    def getConnection(self):
        """
        Returns a shared psycopg2.connection object from the pool.

        :raise Errors defined at <https://www.psycopg.org/docs/errors.html>
        :return: connection object
        :rtype: psycopg2.connection
        """
        return self.__db_pool.getconn()

    def getPoolObject(self):
        """
        Returns the pool object created by this class.

        :raise Errors defined at <https://www.psycopg.org/docs/errors.html>
        :return: pool object
        :rtype: psycopg2.connection
        """
        return self.__db_pool

    def returnConnection(self, conn):
        """
        Release the connection back to the pool.

        :raise Errors.
        """
        self.__db_pool.putconn(conn)
