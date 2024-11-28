from __future__ import annotations

from contextlib import suppress
from typing import Any, Dict, Tuple, List

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLDataset(dlib.ABCDataset):
    def __db_insert(self, use_id: bool = False, write_datatable: bool = False, db_cur_session: psycopg2.cursor | None = None):  # ToDo: Implement write_datatable
        if self.does_exist():  # ToDo: Implement does_exist and matching static function
            raise dlib.ABCDatasetError("Unable to perform database INSERT with PostgreSQLDataset that does already exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if self._owner_user is None:
                raise dlib.ABCDatasetError("No owner of the dataset was set!")

            if use_id :
                if self._internal_id is None:
                    raise dlib.ABCDatasetError("No id (db_id) set for PostgreSQLDataset. Unable to perform INSERT with assigned id.")

                db_cur.execute("""INSERT INTO datasets(id, instrument_id, project_id, label, created_on, title, contact_email, user_id, research_group_id, state) 
                                    VALUES (%(db_id)s, %(instrument_id)s, %(project_id)s, %(label)s, %(created_on)s, %(title)s, %(contact_email)s, %(user_id)s, %(research_group_id)s, %(state)s) RETURNING id;""",
                               {"db_id": self._internal_id,
                                "instrument_id": self._instrument.get_id() if self._instrument else None,
                                "project_id": self._parent_project.get_id() if self._parent_project else None,
                                "label": self._external_id,
                                "created_on": self._created_on,
                                "title": self._title,
                                "contact_email": self._contact_email,
                                "user_id": self._owner_user.get_id() if self._owner_user else None,
                                "research_group_id": self._owner_group.get_id() if self._owner_group else None,
                                "state": self._state})
            else:
                db_cur.execute("""INSERT INTO datasets(instrument_id, project_id, label, created_on, title, user_id, research_group_id, contact_email, state) 
                                    VALUES (%(instrument_id)s, %(project_id)s, %(label)s, %(created_on)s, %(title)s, %(user_id)s, %(research_group_id)s, %(contact_email)s, %(state)s) RETURNING id;""",
                               {"instrument_id": self._instrument.get_id() if self._instrument else None,
                                "project_id": self._parent_project.get_id() if self._parent_project else None,
                                "label": self._external_id,
                                "created_on": self._created_on,
                                "title": self._title,
                                "user_id": self._owner_user.get_id() if self._owner_user else None,
                                "research_group_id": self._owner_group.get_id() if self._owner_group else None,
                                "contact_email": self._contact_email,
                                "state": self._state})

            self._internal_id = db_cur.fetchone()[0]

            if self._metatexts:
                for metatext_tag, metatext in self._metatexts.items():
                    metatext.set_dataset_id(dataset_id = self._internal_id)
                    metatext.write_to_db(db_cur_session=db_cur)

            if self._urls:
                for url in self._urls:
                    url.set_dataset_id(dataset_id = self._internal_id)
                    url.append_to_dataset(db_cur_session=db_cur)

            psql.PostgreSQLTimeline.add_new_dataset_timeline_event(timestamp=self._created_on,
                                                                   user=self._owner_user if self._owner_user else None,
                                                                   state=dlib.TimelineEventState.INFO,
                                                                   text="Import via install & migration script.",  # ToDo: What text should be saved?
                                                                   event_type=dlib.DatasetTimelineEventType.INITIATED,
                                                                   dataset_id=self._internal_id,
                                                                   db_cur_session=db_cur)  # ToDo: Another event downstream?

            if write_datatable and self._data:
                self._data.write_to_db(db_cur_session=db_cur)

                psql.PostgreSQLTimeline.add_new_dataset_timeline_event(timestamp=self._created_on,
                                                                       user=self._owner_user if self._owner_user else None,
                                                                       state=dlib.TimelineEventState.INFO,
                                                                       text="Data table import via install & migration script.",  # ToDo: What text should be saved?
                                                                       event_type=dlib.DatasetTimelineEventType.UPLOADED,
                                                                       dataset_id=self._internal_id,
                                                                       db_cur_session=db_cur)  # Question: Second timeline event here for upload at the same time? Or just one?
            elif write_datatable:
                raise dlib.ABCDatasetError("No datable attached to PostgreSQLDataset. Unable to add datasets!")

            if db_conn:
                # db_conn.rollback()  # ToDo: swap me at the end!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    @staticmethod
    def __db_select_db_row(db_id: int | None = None, label: str | None = None, db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        if db_id is None and label is None:
            raise dlib.ABCDatasetError("No id nor label is set for PostgreSQLDataset. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if db_id:
                db_cur.execute("""SELECT id, label, instrument_id, project_id, created_on, title, 
                                        user_id, research_group_id, contact_email, state 
                                    FROM datasets WHERE id = %(db_id)s;""", {"db_id": db_id})
            else:
                db_cur.execute("""SELECT id, label, instrument_id, project_id, created_on, title, 
                                        user_id, research_group_id, contact_email, state 
                                    FROM datasets WHERE label = %(label)s;""", {"label": label})

            db_row = db_cur.fetchone()

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    def __db_select(self, db_cur_session: psycopg2.cursor | None = None):
        db_row = PostgreSQLDataset.__db_select_db_row(db_id = self._internal_id,
                                                      label = self._external_id,
                                                      db_cur_session = db_cur_session)

        self._internal_id = db_row[0]
        self._external_id = db_row[1]

        self._instrument = psql.PostgreSQLInstrument.objectify_with_id(db_row[2]) if db_row[2] else None
        self._parent_project = psql.PostgreSQLProject.objectify_with_id(db_row[3], fetch_datasets=False) if db_row[3] else None

        self._created_on = db_row[4]
        self._title = db_row[5]
        self._owner_user = psql.PostgreSQLUser.objectify_with_id(db_row[6]) if db_row[6] else None
        self._owner_group = psql.PostgreSQLResearchGroup.objectify_with_id(db_row[7]) if db_row[7] else None  #

        self._contact_email = db_row[8]
        self._state = db_row[9]

        self._metatexts = psql.PostgreSQLMetatext.objectify_with_dataset_id(self._internal_id)
        self._urls = psql.PostgreSQLUrl.objectify_with_dataset_id(self._internal_id)

        self._trait_values = psql.PostgreSQLTraitValue.objectify_with_dataset_id(db_id=self._internal_id)

        self._data = psql.PostgreSQLDataTable.objectify_with_dataset_id(dataset_id=db_row[0])

        raise dlib.ABCDatasetError("Not Finished yet!")

    def __db_update(self, update_metatexts: bool = True, update_urls: bool = True, db_cur_session: psycopg2.cursor | None = None):  # ToDo: Implement write_datatable
        if not self.does_exist():
            raise dlib.ABCDatasetError("Unable to perform database UPDATE on PostgreSQLDataset that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""UPDATE datasets SET instrument_id = %(instrument_id)s, project_id = %(project_id)s, 
                                     title =  %(title)s, contact_email = %(email)s, user_id = %(user_id)s, 
                                     research_group_id = %(research_group_id)s WHERE id = %(db_id)s;""",
                           {"db_id": self._internal_id,
                            "project_id": self._parent_project.get_id() if self._parent_project else None,
                            "title": self._title,
                            "email": self._contact_email,
                            "user_id": self._owner_user.get_id() if self._owner_user else None,
                            "research_group_id": self._owner_group.get_id()})

            if update_metatexts and self._metatexts:
                for tag, metatext in self._metatexts.items():
                    metatext.write_to_db()  # Also performs a delete if text is == ""

                    # Question: Is the following save to do while iterating?
                    if len(metatext.get_text()) < 1:
                        del self._metatexts[metatext.get_tag()]  # Fixme: Expected type 'SupportsIndex | slice', got 'str' instead

                if len(self._metatexts) < 1:
                    self._metatexts = None

            if update_urls:
                psql.PostgreSQLUrl.remove_all_from_dataset(self._internal_id)
                if self._urls:
                    for url in self._urls:
                        url.append_to_dataset()

            psql.PostgreSQLTimeline.add_new_dataset_timeline_event(user = self._owner_user if self._owner_user else None,
                                                                   state = dlib.TimelineEventState.INFO,
                                                                   text = None,  # ToDo: What text should be saved?
                                                                   event_type = dlib.DatasetTimelineEventType.UPDATE_META,
                                                                   dataset_id = self._internal_id)

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    @classmethod
    def objectify_with_id(cls, db_id: int) -> PostgreSQLDataset:  # ToDo: inherit it from the parent class, is it possible to overwrite return type? any restrictions form parent class?
        # Fixme: Add option to only select certain features
        db_row = PostgreSQLDataset.__db_select_db_row(db_id = db_id)

        trait_values = {}
        with suppress(dlib.ABCTraitValueNotFoundError):
            trait_values = psql.PostgreSQLTraitValue.objectify_with_dataset_id(db_id = db_row[0])

        dataset = cls(internal_id = db_row[0], external_id = db_row[1],
                      data = psql.PostgreSQLDataTable.objectify_with_dataset_id(dataset_id = db_id),
                      parent_project = psql.PostgreSQLProject.objectify_with_id(db_row[3], fetch_datasets=False) if db_row[3] else None,
                      instrument = psql.PostgreSQLInstrument.objectify_with_id(db_row[2]) if db_row[2] else None,
                      created_on = db_row[4],
                      state = db_row[9],  # ToDo:  dlib.DatasetState  # ToDo: "state" 5 ?
                      title = db_row[5],
                      owner_user = psql.PostgreSQLUser.objectify_with_id(db_row[6]) if db_row[6] else None,
                      owner_group = psql.PostgreSQLResearchGroup.objectify_with_id(db_row[7]) if db_row[7] else None,
                      contact_email = db_row[8],
                      metatexts = psql.PostgreSQLMetatext.objectify_with_dataset_id(db_row[0]),
                      urls = psql.PostgreSQLUrl.objectify_with_dataset_id(dataset_id = db_row[0]),
                      trait_values = trait_values)

        return dataset

    @classmethod
    def objectify_with_label(cls, label: str) -> PostgreSQLDataset:  # ToDo: inherit it from the parent class, is it possible to overwrite return type? any restrictions form parent class?
        # Fixme: Add option to only select certain features
        db_row = PostgreSQLDataset.__db_select_db_row(label = label)

        trait_values = {}
        with suppress(dlib.ABCTraitValueNotFoundError):
            trait_values = psql.PostgreSQLTraitValue.objectify_with_dataset_id(db_id = db_row[0])

        dataset = cls(internal_id = db_row[0], external_id = db_row[1],
                      data = psql.PostgreSQLDataTable.objectify_with_dataset_id(dataset_id=db_row[0]),
                      parent_project = psql.PostgreSQLProject.objectify_with_id(db_id=db_row[3], fetch_datasets=False) if db_row[3] else None,
                      instrument = psql.PostgreSQLInstrument.objectify_with_id(db_id=db_row[2]) if db_row[2] else None,
                      created_on = db_row[4],
                      state = db_row[9],
                      title = db_row[5],
                      owner_user = psql.PostgreSQLUser.objectify_with_id(db_id=db_row[6]) if db_row[6] else None,
                      owner_group = psql.PostgreSQLResearchGroup.objectify_with_id(db_id=db_row[7]) if db_row[7] else None,
                      contact_email = db_row[8],
                      metatexts = psql.PostgreSQLMetatext.objectify_with_dataset_id(db_row[0]),
                      urls = psql.PostgreSQLUrl.objectify_with_dataset_id(dataset_id = db_row[0]),
                      trait_values = trait_values)

        return dataset

    @classmethod
    def objectify_with_dataset(cls, dataset: dlib.ABCDataset) -> PostgreSQLDataset:  # Fixme: Add option to only select certain features

        # def migrate_obj(obj, id, target_class) -> target_class:
        #     if object is target_class:
        #         return obj
        #     else:
        #       return obj._objectify_with_id(id)

        # Question, FixMe: hard copy of some objects? e.g. data, and remove links to old dataset?
        new_dataset = cls(internal_id = None, external_id = dataset._external_id,
                          data = dataset._data,  # ToDo: objectify with sql type if needed? dataset._data.set_parent_dataset(self)
                          parent_project = dataset._parent_project,  # ToDo: objectify with sql type if needed?
                          instrument = dataset._instrument,  # ToDo: objectify with sql type if needed?
                          created_on = dataset._created_on,
                          state = dataset._state,
                          title = dataset._title,
                          owner_user = dataset._owner_user,  # ToDo: objectify with sql type if needed?
                          owner_group = dataset._owner_group,  # ToDo: objectify with sql type if needed?
                          contact_email = dataset._contact_email,
                          metatexts = dataset._metatexts,  # ToDo: objectify with sql type if needed?
                          urls = dataset._urls,  # ToDo: objectify with sql type if needed?
                          trait_values = dataset._trait_values)  # ToDo: objectify with sql type if needed?

        return new_dataset

    @staticmethod
    def get_full_dataset_list(db_cur_session: psycopg2.cursor | None = None) -> Dict[str, int]:
        datasets_ids: Dict[str, int] = {}

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

                db_cur.execute("SELECT id, label FROM datasets ORDER BY created_on DESC;")  # Question: Any particular sorting? here newest first

                db_rows = db_cur.fetchall()

                for row in db_rows:
                    datasets_ids[row[1]] = row[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return datasets_ids

    def does_exist(self, db_cur_session: psycopg2.cursor | None = None):  # ToDo: Inherit from parent class?
        if self._internal_id is None:
            return False
        else:
            return PostgreSQLDataset.does_exist_with_id(self._internal_id, db_cur_session=db_cur_session)

    @staticmethod
    def does_exist_with_id(db_id: int, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM datasets WHERE id=%(id)s", {"id": db_id})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    @staticmethod
    def does_exist_with_ids(db_ids: List[int], db_cur_session: psycopg2.cursor | None = None) -> Dict[int, bool]:
        return_dict = {}

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT id FROM datasets WHERE id IN %(labels)s;", {"ids": tuple(db_ids)})
            db_rows = db_cur.fetchall()

            found_ids = [db_row[0] for db_row in db_rows]

            for db_id in db_ids:
                return_dict[db_id] = db_id in found_ids

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return return_dict

    @staticmethod
    def does_exist_with_label(label: str, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM datasets WHERE label=%(label)s);", {"label": label})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    @staticmethod
    def does_exist_with_labels(labels: List[str], db_cur_session: psycopg2.cursor | None = None) -> Dict[str, bool]:
        return_dict = {}

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT label FROM datasets WHERE label IN %(labels)s;", {"labels": tuple(labels)})
            db_rows = db_cur.fetchall()

            found_labels = [db_row[0] for db_row in db_rows]

            for str_label in labels:
                return_dict[str_label] = str_label in found_labels

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return return_dict

    def read(self, fetch_datatable: bool = False, db_cur_session: psycopg2.cursor | None = None):
        self.__db_select(db_cur_session=db_cur_session)

        if fetch_datatable:
            raise dlib.ABCDatasetError("Fetching the database for a PostgreSQLDataset is not implemented yet.")  # ToDo: implement fetch_datatable for dataset
        else:
            self._data = None

    def set_metatexts(self, metatexts: List[dlib.ABCMetatext] | None):
        if self._internal_id is None or self._metatexts is None:  # It is most likely not in the database, just treat it as simple set
            super(PostgreSQLDataset, self).set_metatexts(metatexts)
        else:  # Something is most likely in the database
            if metatexts is None and self._metatexts is not None:
                for metatext in self._metatexts:
                    metatext.set_text("")  # Overwrite text with "" to delete them with the next write (in PostgreSQLMetatext)
            else:
                for existing_key in self._metatexts.keys():
                    if existing_key in metatexts:  # set new metatext
                        self._metatexts[existing_key] = metatexts[existing_key]
                    else:  # set text to "" for DELETE if they are gone
                        self._metatexts[existing_key] = ""

                for key in metatexts.keys():  # Add missing metatexts
                    if key not in self._metatexts:
                        self._metatexts[key] = metatexts[key]

    def update_state(self, state: dlib.DatasetState | None, allow_downgrade: bool = False, db_cur_session: psycopg2.cursor | None = None):  # ToDo: Add to parent class
        if not self.does_exist():
            raise dlib.ABCDatasetError("Unable to perform database UPDATE on PostgreSQLDataset that does not exist in database.")

        if state is None:
            state = self._state

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if allow_downgrade:
                db_cur.execute("""UPDATE datasets SET state = %(state)s WHERE id = %(db_id)s;""",
                               {"db_id": self._internal_id, "state": state})
            else:
                db_cur.execute("""UPDATE datasets SET state = %(state)s WHERE id = %(db_id)s AND state < %(state)s;""",
                               {"db_id": self._internal_id, "state": state})

                if db_cur.rowcount < 0:
                    raise dlib.ABCDatasetError("Unable to perform state update. Is the applied state greater than current state?")

            psql.PostgreSQLTimeline.add_new_dataset_timeline_event(user=self._owner_user if self._owner_user else None,
                                                                   state=dlib.TimelineEventState.INFO,
                                                                   text=None,  # ToDo: What text should be saved?
                                                                   event_type=dlib.DatasetTimelineEventType.UPDATE_STATE,
                                                                   dataset_id=self._id)

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def write_to_db(self, write_datatable: bool = True, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(use_id=False, write_datatable=write_datatable, db_cur_session=db_cur_session) if self._internal_id is None else self.__db_update(update_metatexts=True, update_urls=True, db_cur_session=db_cur_session)
