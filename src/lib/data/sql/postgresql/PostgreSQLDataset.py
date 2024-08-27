from __future__ import annotations

from typing import Any, Dict, Tuple, List

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLDataset(dlib.ABCDataset):
    def __db_insert(self, use_id: bool = False, write_datatable: bool = False):  # ToDo: Implement write_datatable
        if self.does_exist():  # ToDo: Implement does_exist and matching static function
            raise dlib.ABCDatasetError("Unable to perform database INSERT with PostgreSQLDataset that does already exist in database.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            if self._owner_user is None:
                raise dlib.ABCDatasetError("No owner of the dataset was set!")

            if use_id :
                if self._internal_id is None:
                    raise dlib.ABCDatasetError("No id (db_id) set for PostgreSQLDataset. Unable to perform INSERT with assigned id.")

                db_cur.execute("""INSERT INTO public.datasets(id, instrument_id, project_id, label, created_on, title, contact_email, user_id, research_group_id, state) 
                                    VALUES (%(db_id)s, %(instrument_id)s, %(project_id)s, %(label)s, %(created_on)s, %(title)s, %(email)s, %(user_id)s, %(research_group_id)s, %(state)s) RETURNING id;""",
                               {"db_id": self._internal_id,
                                "instrument_id": self._instrument.get_id() if self._instrument else None,
                                "project_id": self._parent_project.get_id() if self._parent_project else None,
                                "label": self._external_id,
                                "created_on": self._created_on,
                                "title": self._title,
                                "email": self._contact_email,
                                "user_id": self._owner_user.get_id() if self._owner_user else None,
                                "research_group_id": self._owner_group.get_id(),
                                "state": self._state})
            else:
                if self._parent_project:
                    value_project_id = self._parent_project.get_id()
                else:
                    value_project_id = None

                db_cur.execute("""INSERT INTO datasets(instrument_id, project_id, label, created_on, title, user_id, research_group_id, contact_email, state) 
                                    VALUES (%(instrument_id)s, %(project_id)s, %(label)s, %(created_on)s, %(title)s, %(user_id)s, %(research_group_id)s, %(contact_email)s, %(state)s) RETURNING id;""",
                               {"instrument_id": self._instrument.get_id() if self._instrument else None,
                                "project_id": self._parent_project.get_id() if self._parent_project else None,
                                "label": self._external_id,
                                "created_on": self._created_on,
                                "title": self._title,
                                "email": self._contact_email,
                                "user_id": self._owner_user.get_id() if self._owner_user else None,
                                "research_group_id": self._owner_group.get_id(),
                                "contact_email": self._contact_email,
                                "state": self._state})

            self._id = db_cur.fetchone()[0]

            # TODO: Add metatexts
            # self._metatexts = psql.PostgreSQLMetatext.instantiate_from_dataset_id(self._internal_id)
            # TODO: Add Urls
            # self._urls = psql.PostgreSQLUrl.instantiate_from_dataset_id(self._internal_id)

            psql.PostgreSQLTimeline.add_new_dataset_timeline_event(timestamp=self._created_on,
                                                                   user=self._owner_user if self._owner_user else None,
                                                                   state=dlib.TimelineEventState.INFO,
                                                                   text=None,  # ToDo: What text should be saved?
                                                                   event_type=dlib.DatasetTimelineEventType.INITIALISED,
                                                                   dataset_id=self._id)

            if write_datatable:
                if self._data is None:
                    raise dlib.ABCDatasetError("No datable attached to PostgreSQLDataset. Unable to add datasets!")
                elif len(self._data) < 1:
                    raise dlib.ABCDatasetError("Empty list of datasets attached to PostgreSQLDataset. Unable to add datatable!")

                psql.PostgreSQLTimeline.add_new_dataset_timeline_event(timestamp=self._created_on,
                                                                       user=self._owner_user if self._owner_user else None,
                                                                       state=dlib.TimelineEventState.INFO,
                                                                       text=None,  # ToDo: What text should be saved?
                                                                       event_type=dlib.DatasetTimelineEventType.UPLOADED,
                                                                       dataset_id=self._id)  # Question: Second timeline event here for upload at the same time? Or just one?

                raise dlib.ABCDatasetError("Writing attached datable is not implemented yet!")  # ToDo: implement adding dataset

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err
        # INSERT INTO datasets(...) VALUES (...) RETURNING id;"
        pass

    @staticmethod
    def __db_select_db_row(db_id: int | None = None, label: str | None = None) -> Tuple[Any]:
        if db_id is None and label is None:
            raise dlib.ABCDatasetError("No id nor label is set for PostgreSQLDataset. Unable to perform SELECT.")

        try:
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

            psql.PostgreSQLConnection().returnConnection(db_conn)

            return db_row
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def __db_select(self):
        db_row = PostgreSQLDataset.__db_select_db_row(db_id = self._internal_id, label = self._external_id)

        self._internal_id = db_row[0]
        self._external_id = db_row[1]

        self._instrument = psql.PostgreSQLInstrument.create_from_id(db_row[2]) if db_row[2] else None  # ToDo: Update to final method or function
        self._parent_project = psql.PostgreSQLProject.create_from_id(db_row[3], fetch_datasets=False) if db_row[3] else None  # ToDo: Update to final method or function

        self._created_on = db_row[4]
        self._title = db_row[5]
        self._owner_user = psql.PostgreSQLUser.objectify_with_id(db_row[6]) if db_row[6] else None  # ToDo: Update to final method or function
        self._owner_group = psql.PostgreSQLResearchGroup.create_from_id(db_row[7]) if db_row[7] else None  # ToDo: Update to final method or function

        self._contact_email = db_row[8]
        self._state = db_row[9]

        self._metatexts = psql.PostgreSQLMetatext.instantiate_from_dataset_id(self._internal_id)  # ToDo: Update to final method or function
        self._urls = psql.PostgreSQLUrl.objectify_with_dataset_id(self._internal_id)

        self._traits = psql.PostgreSQLTrait.objectify_with_dataset_id(db_id=self._internal_id)  # ToDo: Implement / Update to final method or function

        # ToDo: implement reading datasets
        # self._data = psql.PostgreSQLDataTable.create_from_dataset(dataset=self)  # ToDo: Implement / Update with final method / function
        # self._data = psql.PostgreSQLDataTable.create_from_id(dataset_id=self._internal_id)  # ToDo: Update with final method / function

        obj = cls(db_id=db_id)  # Fixme: This will cause an exception since not all argument are served
        obj.read()

    def __db_update(self, update_metatexts: bool = True, update_urls: bool = True):  # ToDo: Implement write_datatable
        if not self.does_exist():
            raise dlib.ABCDatasetError("Unable to perform database UPDATE on PostgreSQLDataset that does not exist in database.")

        try:
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
                for metatext in self._metatexts:
                    metatext.write()  # Also performs a delete if text is == ""

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

            psql.PostgreSQLTimeline.add_new_dataset_timeline_event(user=self._owner_user if self._owner_user else None,
                                                                   state=dlib.TimelineEventState.INFO,
                                                                   text=None,  # ToDo: What text should be saved?
                                                                   event_type=dlib.DatasetTimelineEventType.UPDATE_META,
                                                                   dataset_id=self._id)

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    @classmethod
    def objectify_with_id(cls, db_id: int) -> dlib.ABCDataset:  # ToDo: inherit it from the parent class, is it possible to overwrite return type? any restrictions form parent class?
        db_row = PostgreSQLDataset.__db_select_db_row(db_id = db_id)

        dataset = cls(internal_id = db_row[0], external_id=db_row[1],
                      data = None,  # ToDo: add final method call
                      parent_project = psql.PostgreSQLProject.create_from_id(db_row[3], fetch_datasets=False) if db_row[3] else None,  # ToDo: Update to final method or function
                      instrument = psql.PostgreSQLInstrument.create_from_id(db_row[2]) if db_row[2] else None,  # ToDo: Update to final method or function
                      created_on = db_row[4],
                      uploaded_on = None,  # ToDo: Figure out
                      state = db_row[9],  # ToDo:  dlib.DatasetState  # ToDo: "state" 5 ?
                      title = db_row[5],
                      owner_user = psql.PostgreSQLUser.objectify_with_id(db_row[6]) if db_row[6] else None, # ToDo: Update to final method or function
                      owner_group = psql.PostgreSQLResearchGroup.create_from_id(db_row[7]) if db_row[7] else None,  # ToDo: Update to final method or function
                      contact_email = db_row[8])
        # metatexts = psql.PostgreSQLMetatext.objectify_with_dataset_id(db_row[0]),  # ToDo: Update to final method or function,
        # urls = self._urls = psql.PostgreSQLUrl.objectify_with_dataset_id(db_row[0])  # ToDo: Implement / Update to final method or function

        # ToDo: implement reading datasets
        # self._traits = psql.PostgreSQLTrait.objectify_with_dataset_id(db_id = self._internal_id)  # ToDo: Implement / Update to final method or function
        # self._data = psql.PostgreSQLDataTable.create_from_dataset(dataset=self)  # ToDo: Implement / Update with final method / function
        # self._data = psql.PostgreSQLDataTable.create_from_id(dataset_id=self._internal_id)  # ToDo: Update with final method / function

        return dataset

    @classmethod
    def objectify_with_label(cls, label: str) -> dlib.ABCDataset:  # ToDo: inherit it from the parent class, is it possible to overwrite return type? any restrictions form parent class?
        db_row = PostgreSQLDataset.__db_select_db_row(label = label)

        dataset = cls(internal_id = db_row[0], external_id = db_row[1],
                      data = None,  # ToDo: add final method call
                      parent_project = psql.PostgreSQLProject.create_from_id(db_row[3], fetch_datasets=False) if db_row[3] else None,  # ToDo: Update to final method or function
                      instrument = psql.PostgreSQLInstrument.create_from_id(db_row[2]) if db_row[2] else None,  # ToDo: Update to final method or function
                      created_on = db_row[4],
                      uploaded_on=None,  # ToDo: Figure out
                      state = db_row[9],  # ToDo:  dlib.DatasetState  # ToDo: "state" 5 ?
                      title = db_row[5],
                      owner_user = psql.PostgreSQLUser.objectify_with_id(db_row[6]) if db_row[6] else None, # ToDo: Update to final method or function
                      owner_group = psql.PostgreSQLResearchGroup.create_from_id(db_row[7]) if db_row[7] else None,  # ToDo: Update to final method or function
                      contact_email = db_row[8])
        # metatexts = psql.PostgreSQLMetatext.objectify_with_dataset_id(db_row[0]),  # ToDo: Update to final method or function,
        # urls = self._urls = psql.PostgreSQLUrl.objectify_with_dataset_id(db_row[0])  # ToDo: Implement / Update to final method or function

        # ToDo: implement reading datasets
        # self._traits = psql.PostgreSQLTrait.objectify_with_dataset_id(db_id = self._internal_id)  # ToDo: Implement / Update to final method or function
        # self._data = psql.PostgreSQLDataTable.create_from_dataset(dataset=self)  # ToDo: Implement / Update with final method / function
        # self._data = psql.PostgreSQLDataTable.create_from_id(dataset_id=self._internal_id)  # ToDo: Update with final method / function

        return dataset

    def does_exist(self):  # ToDo: Inherit from parent class?
        if self._internal_id is None:
            return False
        else:
            return PostgreSQLDataset.does_exist_with_id(self._id)

    @staticmethod
    def does_exist_with_id(db_id: int) -> bool:
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM datasets WHERE id=%(id)s", {"id": db_id})
            does_exist = db_cur.fetchone()[0]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return does_exist

    @staticmethod
    def does_exist_with_ids(db_ids: List[int]) -> Dict[int, bool]:
        return_dict = {}

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT id FROM datasets WHERE id IN %(labels)s;", {"ids": tuple(db_ids)})
            db_rows = db_cur.fetchall()

            found_ids = [db_row[0] for db_row in db_rows]

            for db_id in db_ids:
                return_dict[db_id] = db_id in found_ids

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return return_dict

    @staticmethod
    def does_exist_with_label(label: str) -> bool:
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM datasets WHERE label=%(label)s);", {"label": label})
            does_exist = db_cur.fetchone()[0]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return does_exist

    @staticmethod
    def does_exist_with_labels(labels: List[str]) -> Dict[str, bool]:
        return_dict = {}

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT label FROM datasets WHERE label IN %(labels)s;", {"labels": tuple(labels)})
            db_rows = db_cur.fetchall()

            found_labels = [db_row[0] for db_row in db_rows]

            for str_label in labels:
                return_dict[str_label] = str_label in found_labels

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return return_dict

    def read(self, fetch_datatable: bool = False):
        self.__db_select()

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

    def update_state(self, state: dlib.DatasetState | None, allow_downgrade: bool = False):  # ToDo: Add to parent class
        if not self.does_exist():
            raise dlib.ABCDatasetError("Unable to perform database UPDATE on PostgreSQLDataset that does not exist in database.")

        if state is None:
            state = self._state

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            if allow_downgrade:
                db_cur.execute("""UPDATE datasets SET state = %(state)s WHERE id = %(db_id)s;""",
                               {"db_id": self._internal_id, "state": state})
            else:
                db_cur.execute("""UPDATE datasets SET state = %(state)s WHERE id = %(db_id)s AND state < %(state)s RETURNING id;""",
                               {"db_id": self._internal_id, "state": state})

                if db_cur.rowcount < 0:
                    raise dlib.ABCDatasetError("Unable to perform state update. Is the applied state greater than current state?")

            psql.PostgreSQLTimeline.add_new_dataset_timeline_event(user=self._owner_user if self._owner_user else None,
                                                                   state=dlib.TimelineEventState.INFO,
                                                                   text=None,  # ToDo: What text should be saved?
                                                                   event_type=dlib.DatasetTimelineEventType.UPDATE_STATE,
                                                                   dataset_id=self._id)

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def write(self, write_datatable: bool = False):
        self.__db_insert(use_id=False) if self._internal_id is None else self.__db_update(update_metatexts=True, update_urls=True)

        if write_datatable:
            raise dlib.ABCDatasetError("Writing/Creating datasets for a PostgreSQLDataset is not implemented yet.")  # ToDo: implement write_datatable for dataset
