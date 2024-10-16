from __future__ import annotations

from typing import Any, Dict, Tuple, List

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql

from config import get_system_settings

# DB_SETTINGS = get_db_settings()  # Setup proper config

# class PostgreSQLDatabase(dlib.CachedDatabase):  # ToDo: Move some functions to a DatabaseStat Class to keep it clean?
class PostgreSQLDatabase(dlib.ABCDatabase):  # ToDo: Move some functions to a DatabaseStat Class to keep it clean?
    @staticmethod
    def query_trait_ids(trait_query: str | None = None,  # searches texts in traits
                        trait_tags: List[str] | None = None,
                        for_filter: bool = True,
                        for_dataset: bool = True,
                        for_genotype: bool = True,
                        for_sample: bool = True,
                        for_performance: bool = True,
                        db_cur_session: psycopg2.cursor | None = None) -> List[id]:

        if trait_query is None and trait_tags is None:
            raise dlib.ABCAttributeError("Unable to query for trait_ids without the arguments trait_query or trait_tags.")

        db_conn = None
        db_cur = db_cur_session

        trait_ids: List[int] = []

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            str_condition = None

            if trait_tags:
                str_condition = "a.tag || ':' || t.tag = ANY(%(trait_tags)s)"

            if trait_query:
                str_condition = str_condition + " OR " if str_condition else ""  # Question: OR or AND? Configurable?
                str_condition = str_condition + "t.tag LIKE %(trait_query)s OR t.text LIKE %(trait_query)s OR t.description LIKE %(trait_query)s"

            sql_statement = """
                SELECT DISTINCT t.id 
                    FROM traits AS t
                        LEFT JOIN attributes AS a ON a.id = t.attribute_id
                    WHERE 
                        ({condition}) 
                        AND
                        (a.allow_as_filter = %(for_filter)s OR 
                         a.allow_for_dataset = %(for_dataset)s OR 
                         allow_for_genotype = %(for_genotype)s OR 
                         allow_for_performance = %(for_sample)s OR 
                         allow_for_sample = %(for_performance)s);
                """.format(condition = str_condition)

            if trait_query:
                trait_query = "%" + trait_query if not trait_query.startswith("%") else trait_query
                trait_query = trait_query + "%" if not trait_query.endswith("%") else trait_query

            db_cur.execute(sql_statement,
                           {"trait_tags": trait_tags,
                            "trait_query": trait_query,
                            "for_filter": for_filter,
                            "for_dataset": for_dataset,
                            "for_genotype": for_genotype,
                            "for_sample": for_sample,
                            "for_performance": for_performance})

            db_rows = db_cur.fetchall()

            for db_row in db_rows:
                trait_ids.append(db_row[0])

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return trait_ids

    @staticmethod
    def query_datasets_ids(query: str | None = None,  # searches texts in traits but also dataset and metatexts
                           states: List[int] | None = None,
                           feature_keys: List[str] | None = None,
                           trait_tags: List[str] | None = None,
                           trait_ids: List[int] | None = None,
                           genotype_labels: List[str] | None = None,  # ToDo: implement genotype_labels / Genotypes first
                           usernames: List[str] | None = None,
                           limit_to_n: int | None = None,
                           limit_offset: int = 0,
                           db_cur_session: psycopg2.cursor | None = None) -> Tuple[List[id], List[str]]:
        db_conn = None
        db_cur = db_cur_session
        sql_constructed = []

        dataset_ids: List[int] = []
        dataset_labels: List[str] = []

        if query or trait_tags:
            identified_trait_ids = PostgreSQLDatabase.query_trait_ids(trait_query=query,
                                                                      trait_tags=trait_tags,
                                                                      for_filter=False, for_dataset=True,
                                                                      for_genotype=False, for_sample=True,
                                                                      for_performance=False,
                                                                      db_cur_session=db_cur_session)
        else:
            identified_trait_ids = []

        if trait_ids and len(trait_ids) > 0:
            identified_trait_ids = trait_ids + identified_trait_ids

        if query:
            query = "%" + query if not query.startswith("%") else query
            query = query + "%" if not query.endswith("%") else query

            sql_constructed.append("SELECT DISTINCT dataset_id AS id FROM metatexts WHERE text LIKE %(query)s \n")

        if identified_trait_ids and len(identified_trait_ids) > 0:
            identified_trait_ids = list(set(identified_trait_ids))
            sql_constructed.append("SELECT DISTINCT d.id AS id FROM datasets AS d "
                                   "LEFT JOIN nm_traits_datasets AS nm ON nm.dataset_id = d.id "
                                   "WHERE nm.trait_id = ANY(%(identified_trait_ids)s) \n"
                                   "UNION \n"
                                   "SELECT DISTINCT s.dataset_id AS id "
                                   "FROM samples AS s "
                                   "LEFT JOIN nm_traits_samples AS nm ON nm.sample_id = s.id "
                                   "WHERE nm.trait_id = ANY(%(identified_trait_ids)s) \n")

        if usernames and len(usernames) > 0:
            sql_constructed.append("SELECT DISTINCT d.id AS id "
                                   "FROM sec_users AS u "
                                   "LEFT JOIN datasets AS d ON d.user_id = u.id "
                                   "WHERE u.username = ANY(%(usernames)s) \n")

        if feature_keys and len(feature_keys) > 0:
            sql_constructed.append("SELECT DISTINCT v.dataset_id AS id "
                                   "FROM feature_pgs AS f "
                                   "LEFT JOIN feature_pg_values AS v ON f.id = v.feature_id "
                                   "WHERE f.label = ANY(%(feature_keys)s) \n")

        if len(sql_constructed) > 0:
            sql_constructed = "UNION \n".join(sql_constructed)
            sql_constructed = "ds.id = ANY({})".format(sql_constructed)
        else:
            sql_constructed = ""

        if query:
            if len(sql_constructed) > 0:
                sql_constructed = "ds.label LIKE %(query)s OR ds.title LIKE %(query)s OR \n{} ".format(sql_constructed)
            else:
                sql_constructed = "ds.label LIKE %(query)s OR ds.title LIKE %(query)s \n"

        if states and len(states) > 0:
            if len(sql_constructed) > 0:
                sql_constructed = "ds.state = ANY(%(states)s) AND ( \n{}) ".format(sql_constructed)
            else:
                sql_constructed = "ds.state = ANY(%(states)s) "

        if len(sql_constructed) > 0:
            sql_constructed = "SELECT ds.id AS id, ds.label AS label \nFROM datasets AS ds \nWHERE {} ".format(sql_constructed)
        else:
            sql_constructed = "SELECT ds.id AS id, ds.label AS label \nFROM datasets AS ds "

        if limit_to_n and limit_to_n > 0 and limit_offset >= 0:
            sql_constructed = "{}\nLIMIT %(limit_to_n)s OFFSET %(limit_offset)s;".format(sql_constructed)
        else:
            sql_constructed = "{};".format(sql_constructed)

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute(sql_constructed, {"query": query,
                                             "states": states,
                                             "usernames": usernames,
                                             "feature_keys": feature_keys,
                                             "identified_trait_ids": identified_trait_ids,
                                             "limit_to_n": limit_to_n,
                                             "limit_offset": limit_offset})

            db_rows = db_cur.fetchall()

            for db_row in db_rows:
                dataset_ids.append(db_row[0])
                dataset_labels.append(db_row[1])

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return dataset_ids, dataset_labels
