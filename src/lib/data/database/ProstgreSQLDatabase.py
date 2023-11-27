
import pandas as pd 
import typing 

try:
    import psycopg2 
except:
    pass 
from lib.data.dataset.ABCDataset import MCDataset 
from lib.data.database.ABCDatabase import MCDatabase
from lib.data.DesignPatterns import SQLConnection 

from config.settings.db import get_db_settings
from config.models.submissions.submissions import SubmissionFromMetaDB

DB_SETTINGS = get_db_settings()

class PostgreSQLConnection(SQLConnection):  # (metaclass=SingletonMeta):
    """Singleton class that opens, shares and closes a shared psycopg2.connection to the configured database."""

    #: Holds the shared connection object.
    # conn = None  # Todo: Figure out type, e.g. psycopg2.connection like does not work

    # __db_ip: str = None
    # __db_name: str = None
    # __db_user: str = None
    # __db_pw: str = None

    def __init__(self):
        """
        The Constructor of DBConnection creates a new psycopg2.connection to the PostgreSQL database that can be shared.

        :raise Errors.
        """
        self.__db_ip =  DB_SETTINGS.db_ip
        self.__db_name = DB_SETTINGS.db_name
        self.__db_user = DB_SETTINGS.db_user
        self.__db_pw = DB_SETTINGS.db_pw
        super().__init__()

    def getDatabaseName(self):
        """"""
        # ToDo: Write documentation
        return self.__db_name

    def openNewConnection(self):
        """
        The method will open and return a new shared psycopg2.connection to the configured database and will close the
        previous shared connection.

        :raise Errors defined at <https://www.psycopg.org/docs/errors.html>.
        :return: connection object
        :rtype: psycopg2.connection
        """
        if self.conn is not None:
            self.conn.close()

        self.conn = self.getIndependentConnection()

        return self.conn

    def closeConnection(self):
        """
        Closes the shared connection.

        :raise Errors defined at <https://www.psycopg.org/docs/errors.html>
        """
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def getConnection(self):
        """
        Returns the currently shared psycopg2.connection object.

        :raise Errors defined at <https://www.psycopg.org/docs/errors.html>
        :return: connection object
        :rtype: psycopg2.connection
        """
        if self.conn is None:
            self.openNewConnection()

        return self.conn

    def getIndependentConnection(self):  # Todo: Turn to static?
        """
        The method will open and return a new psycopg2.connection to the configured database without closing the
        existing connection. The returned connections is not shared and has to be closed manually.

        :raise Errors defined at <https://www.psycopg.org/docs/errors.html>
        :return: connection object
        :rtype: psycopg2.connection
        """
        return psycopg2.connect(host=self.__db_ip, database=self.__db_name,
                                user=self.__db_user, password=self.__db_pw)


class PostgreSQLDatabase(MCDatabase):
    """"""
    # Todo: Write documentation

    def contains(self, datasetIds: typing.List) -> int:
        """"""
        # Todo: Write documentation
        db_conn = None
        db_cur = None
        try:
            db_in = PostgreSQLConnection()
            db_conn = db_in.getConnection()
            db_cur = db_conn.cursor()

            str_test = "' ,'".join(datasetIds)
            db_cur.execute(f"SELECT COUNT(*) FROM datasets WHERE label IN ('{str_test}');")
            db_row = db_cur.fetchone()
            db_cur.close()

            return db_row[0]
        except Exception as err:
            if db_cur is not None:
                db_cur.close()
            raise err

    def getAttributeTable(self) -> pd.DataFrame:
        """"""
        # Todo: Write documentation
        db_conn = None
        db_cur = None
        try:
            db_in = PostgreSQLConnection()
            db_conn = db_in.getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT a.id AS attribute_id, a.parent_id AS attribute_parent_id, a.tag AS attribute_tag, "
                           "       a.name AS attribute, a.priority, a.allow_as_filter, a.allow_for_dataset, "
                           "       a.allow_for_measurement, a.allow_for_users, a.allow_for_qc, av.id AS value_id, "
                           "       av.tag AS value_tag, av.name AS value, av.details "
                           "   FROM attributes AS a "
                           "       LEFT JOIN attribute_values AS av ON a.id = av.attribute_id "
                           "LEFT JOIN nm_dataset_attribute_value AS nm ON nm.attribute_value_id = av.id;")

            db_rows = pd.DataFrame(db_cur.fetchall(), columns=["attribute_id", "attribute_parent_id", "attribute_tag",
                                                               "attribute", "priority", "allow_as_filter",
                                                               "allow_for_dataset", "allow_for_measurement",
                                                               "allow_for_users", "allow_for_qc", "value_id",
                                                               "value_tag", "value", "details"])

            db_cur.close()
            return db_rows
        except Exception as err:
            if db_cur is not None:
                db_cur.close()
            raise err

    def getDatasetAttributeJSON(self, tag: str = "") -> typing.Dict:
        """"""
        # Todo: Write documentation
        db_conn = None
        db_cur = None
        try:
            db_in = PostgreSQLConnection()
            db_conn = db_in.getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT DISTINCT a.id AS attribute_id, a.parent_id AS attribute_parent_id, a.tag AS attribute_tag, "
                           "       a.name AS attribute, a.priority, a.allow_as_filter, a.allow_for_dataset, "
                           "       a.allow_for_measurement, a.allow_for_users, a.allow_for_qc, av.id AS value_id, "
                           "       av.tag AS value_tag, av.name AS value, av.details "
                           "   FROM attributes AS a "
                           "       LEFT JOIN attribute_values AS av ON a.id = av.attribute_id "
                           "LEFT JOIN nm_dataset_attribute_value AS nm ON nm.attribute_value_id = av.id "
                           f"WHERE av.tag = '{tag}' AND a.allow_for_dataset;")

            db_rows = pd.DataFrame(db_cur.fetchall(), columns=["attribute_id", "attribute_parent_id", "attribute_tag",
                                                               "attribute", "priority", "allow_as_filter",
                                                               "allow_for_dataset", "allow_for_measurement",
                                                               "allow_for_users", "allow_for_qc", "value_id",
                                                               "value_tag", "value", "details"])

            db_cur.close()

            if db_rows.shape[0] == 0:
                raise Exception(f"No match for the attribute_value with the tag '{tag}'.")
            elif db_rows.shape[0] > 1:
                raise Exception(f"No unique for the attribute_value with the tag '{tag}'.")

            return MCDataset.buildAttributesJsonItem(db_id=db_rows["attribute_id"].iloc[0],
                                                     attribute_parent_id=db_rows["attribute_parent_id"].iloc[0],
                                                     attribute_tag=tag,
                                                     attribute=db_rows["attribute"].iloc[0],
                                                     priority=db_rows["priority"].iloc[0],
                                                     allow_as_filter=db_rows["allow_as_filter"].iloc[0],
                                                     value_id=db_rows["value_id"].iloc[0],
                                                     tag=db_rows["value_tag"].iloc[0],
                                                     value=db_rows["value"].iloc[0],
                                                     details=db_rows["details"].iloc[0])
        except Exception as err:
            if db_cur is not None:
                db_cur.close()
            raise err

    def getSampleAttributeJSON(self, grouping_json: typing.Dict = {}) -> typing.Dict:
        """"""
        # Todo: Write documentation
        db_conn = None
        db_cur = None
        try:
            db_in = PostgreSQLConnection()
            db_conn = db_in.getConnection()
            db_cur = db_conn.cursor()

            str_del = "' ,'"
            str_attributes = str_del.join(grouping_json.keys())


            db_cur.execute("SELECT a.id AS attribute_id, a.parent_id AS attribute_parent_id, a.tag AS attribute_tag, "
                           "       a.name AS attribute, a.priority, a.allow_as_filter, a.allow_for_dataset, "
                           "       a.allow_for_measurement, a.allow_for_users, a.allow_for_qc, av.id AS value_id, "
                           "       av.tag AS value_tag, av.name AS value, av.details "
                           "               FROM attributes AS a "
                           "                   LEFT JOIN attribute_values AS av ON a.id = av.attribute_id "
                           "            LEFT JOIN nm_dataset_attribute_value AS nm ON nm.attribute_value_id = av.id "
                           f"            WHERE av.tag IN ('{str_attributes}') AND a.allow_for_measurement;")

            db_rows = pd.DataFrame(db_cur.fetchall(), columns=["attribute_id", "attribute_parent_id", "attribute_tag",
                                                               "attribute", "priority", "allow_as_filter",
                                                               "allow_for_dataset", "allow_for_measurement",
                                                               "allow_for_users", "allow_for_qc", "value_id",
                                                               "value_tag", "value", "details"])

            if(len(db_rows["attribute_tag"].unique()) != 1):
                raise Exception("Attribute tags are not unique! Check group definition.")

            json_groups = {}
            for ix, attribute in db_rows.iterrows():
                json_groups[attribute["value_tag"]] = MCDataset.buildSampleAttributesJsonGroup(db_id=attribute["value_id"],
                                                                                               tag=attribute["value_tag"],
                                                                                               value=attribute["value"],
                                                                                               details=attribute["details"],
                                                                                               samples=grouping_json[attribute["value_tag"]])

            return MCDataset.buildSampleAttributesJsonItem(db_id=db_rows["attribute_id"].iloc[0],
                                                           attribute_parent_id=db_rows["attribute_parent_id"].iloc[0],
                                                           attribute=db_rows["attribute"].iloc[0],
                                                           priority=db_rows["priority"].iloc[0],
                                                           allow_as_filter=db_rows["allow_as_filter"].iloc[0],
                                                           grouping_json=json_groups)
        except Exception as err:
            if db_cur is not None:
                db_cur.close()
            raise err

    def getAllDataIDs(self, sort_createdOn_desc: bool = False) -> typing.List[str]:
        """"""
        # Todo: Write documentation
        db_conn = None
        db_cur = None
        try:
            db_in = PostgreSQLConnection()
            db_conn = db_in.getConnection()
            db_cur = db_conn.cursor()

            str_sort_direction = "DESC" if sort_createdOn_desc else "ASC"

            db_cur.execute(f"SELECT label FROM datasets AS ds ORDER BY created_on {str_sort_direction};")
            db_rows = [value[0] for value in db_cur.fetchall()]

            db_cur.close()
            return db_rows  # ToDo: returns List[Tuple[Any, ...]] instead of List[]
        except Exception as err:
            if db_cur is not None:
                db_cur.close()
            raise err

    def getDataIDs(self, n_limit: int = 42, n_offset: int = 0, sort_createdOn_desc: bool = False) -> typing.List[str]:
        """"""
        # Todo: Write documentation
        db_conn = None
        db_cur = None
        try:
            db_in = PostgreSQLConnection()
            db_conn = db_in.getConnection()
            db_cur = db_conn.cursor()

            str_sort_direction = "DESC" if sort_createdOn_desc else "ASC"

            db_cur.execute("SELECT label FROM datasets AS ds "
                           f"   ORDER BY created_on {str_sort_direction} "
                           f"   LIMIT {n_limit} OFFSET {n_offset};")
            db_rows = [value[0] for value in db_cur.fetchall()]
            db_cur.close()

            return db_rows
        except Exception as err:
            if db_cur is not None:
                db_cur.close()
            raise err

    def getJSONDatasets(self, labels: typing.List[str] = []) -> typing.Dict[str, SubmissionFromMetaDB]:
        """"""
        # Todo: Write documentation
        datasets = {}
        labels_toQuery = []
        if len(labels) < 1:
            labels = self.getAllDataIDs()

        for label in labels:
            if label in self._cached_datasets:
                datasets[label] = {"id": self._cached_datasets[label]._id,
                                   "label": self._cached_datasets[label]._label,
                                   "email": self._cached_datasets[label]._contact_email,
                                   "state": self._cached_datasets[label]._state,
                                   "instrument": self._cached_datasets[label]._instrument,
                                   "title": self._cached_datasets[label]._title,
                                   "experimentator": self._cached_datasets[label]._experimentator,
                                   "group_name": self._cached_datasets[label]._name_group,
                                   "date_created_on": self._cached_datasets[label]._created_on,
                                   "date_uploaded_on": self._cached_datasets[label]._uploaded_on}
            else:
                labels_toQuery.append(label)

        if len(labels_toQuery) > 0:
            db_conn = None
            db_cur = None

            try:
                db_in = PostgreSQLConnection()
                db_conn = db_in.getConnection()
                db_cur = db_conn.cursor()

                str_labels_toQuery = "', '".join(labels_toQuery)
                db_cur.execute("SELECT d.id, d.label, d.contact_email, d.state, "
                               "       d.instrument_id, i.label, i.name, i.description, "
                               "       d.title, d.experimentator, d.name_group, d.created_on, d.uploaded_on "
                               "    FROM datasets AS d "
                               "        LEFT JOIN instruments AS i ON d.instrument_id = i.id "
                               f"    WHERE d.label IN ('{str_labels_toQuery}');")
                for db_row in db_cur:
                    datasets[db_row[1]] = {"id": db_row[0],
                                           "label": db_row[1],
                                           "email": db_row[2],
                                           "state": db_row[3],
                                           "instrument": MCDataset.buildInstrumentJson(db_id=db_row[4],
                                                                                       label=db_row[5],
                                                                                       name=db_row[6],
                                                                                       description=db_row[7]),
                                           "title": db_row[8],
                                           "experimentator": db_row[9],
                                           "group_name": db_row[10],
                                           "date_created_on": db_row[11],
                                           "date_uploaded_on": db_row[12]}

                db_cur.close()
            except Exception as err:
                if db_cur is not None:
                    db_cur.close()
                raise err

        return datasets

    def getNumberOfDatasets(self) -> int:
        """"""
        # Todo: Write documentation
        db_conn = None
        db_cur = None

        try:
            db_in = PostgreSQLConnection()
            db_conn = db_in.getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT COUNT(*) FROM datasets;")
            db_row = db_cur.fetchone()
            db_cur.close()

            return db_row[0]
        except Exception as err:
            if db_cur is not None:
                db_cur.close()
            raise err

    def getSize(self) -> int:
        """"""
        # Todo: Write documentation
        db_conn = None
        db_cur = None
        try:
            db_in = PostgreSQLConnection()
            db_conn = db_in.getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute(f"SELECT pg_database_size('{db_in.getDatabaseName()}') - "
                           "pg_total_relation_size('sec_tokens') - "
                           "pg_total_relation_size('sec_users') - "
                           "pg_total_relation_size('nm_users_attribute_value');")
            db_row = db_cur.fetchone()
            db_cur.close()

            return db_row[0]
        except Exception as err:
            if db_cur is not None:
                db_cur.close()
            raise err
