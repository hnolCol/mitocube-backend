from __future__ import annotations

from typing import Any, Dict, Tuple, List, Self

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql

class PostgresSQLGenotype(dlib.ABCGenotype):
    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):
        pass

    @classmethod
    def objectify_with_id(cls, db_id: int, db_cur_session: psycopg2.cursor | None = None) -> PostgresSQLGenotype:
        db_conn = None
        db_cur = db_cur_session

        genotype: PostgresSQLGenotype

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                SELECT trait_node_id, label, name, description, is_selectable, created_by, created_on FROM genotypes WHERE id = %(id)s;
                """, {"db_id": db_id})

            if db_cur.rowcount != 1:
                raise dlib.ABCGenotypeNotFoundError("Provided id or name does not match a single genotype. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()

            genotype = cls(label = db_row[1], name = db_row[2],
                           trait_tree = psql.PostgreSQLTraitTree.objectify_with_root_trait_node_id(db_id = db_row[0], db_cur_session = db_cur_session),
                           created_by = psql.PostgreSQLUser.objectify_with_id(db_id = db_row[5], db_cur_session = db_cur_session),
                           db_id = db_id, description = db_row[3], is_selectable = db_row[4],
                           created_on = db_row[6])

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return genotype

    @classmethod
    def objectify_with_label(cls, label: str, db_cur_session: psycopg2.cursor | None = None) -> PostgresSQLGenotype:
        db_conn = None
        db_cur = db_cur_session

        genotype: PostgresSQLGenotype

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                SELECT trait_node_id, id, name, description, is_selectable, created_by, created_on FROM genotypes WHERE label = %(label)s;
                """, {"label": label})

            if db_cur.rowcount != 1:
                raise dlib.ABCGenotypeNotFoundError("Provided id or name does not match a single genotype. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()

            genotype = cls(label = label, name = db_row[2],
                           trait_tree = psql.PostgreSQLTraitTree.objectify_with_root_trait_node_id(db_id = db_row[0], db_cur_session = db_cur_session),
                           created_by = psql.PostgreSQLUser.objectify_with_id(db_id = db_row[5], db_cur_session = db_cur_session),
                           db_id = db_row[1], description = db_row[3], is_selectable = db_row[4],
                           created_on = db_row[6])

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return genotype

    @classmethod
    def objectify_with_dataset_id(cls, dataset_id: int, db_cur_session: psycopg2.cursor | None = None) -> Dict[str, PostgresSQLGenotype]:
        db_conn = None
        db_cur = db_cur_session

        genotypes: Dict[str, PostgresSQLGenotype] = {}

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                SELECT g.trait_node_id, id, name, description, is_selectable, created_by, created_on, label 
                    FROM genotypes AS g LEFT JOIN nm_genotypes_datasets AS nm ON nm.genotype_id = g.id
                    WHERE nm.dataset_id = %(dataset_id)s;
                """, {"dataset_id": dataset_id})

            if db_cur.rowcount < 1:
                raise dlib.ABCGenotypeNotFoundError("Provided id or name does not match a single genotype. Number of returned rows = {n}".format(n=db_cur.rownumber))

            for db_row in db_cur.fetchall():
                genotypes[db_row[7]] = cls(label = db_row[7], name = db_row[2], db_id = db_row[1],
                                           trait_tree = psql.PostgreSQLTraitTree.objectify_with_root_trait_node_id(db_id = db_row[0], db_cur_session = db_cur_session),
                                           created_by = psql.PostgreSQLUser.objectify_with_id(db_id = db_row[5], db_cur_session = db_cur_session),
                                           description = db_row[3], is_selectable = db_row[4],
                                           created_on = db_row[6])

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return genotypes

    @classmethod
    def objectify_with_dataset_label(cls, dataset_label: str, db_cur_session: psycopg2.cursor | None = None) -> Dict[str, PostgresSQLGenotype]:
        db_conn = None
        db_cur = db_cur_session

        genotypes: Dict[str, PostgresSQLGenotype] = {}

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                SELECT g.trait_node_id, g.id, g.name, g.description, g.is_selectable, g.created_by, g.created_on, g.label 
                    FROM genotypes AS g 
                        LEFT JOIN nm_genotypes_datasets AS nm ON nm.genotype_id = g.id
                        LEFT JOIN datasets AS d ON d.id = nm.dataset_id
                    WHERE d.label = %(dataset_label)s;
                """, {"dataset_label": dataset_label})

            if db_cur.rowcount < 1:
                raise dlib.ABCGenotypeNotFoundError("Provided id or name does not match a single genotype. Number of returned rows = {n}".format(n=db_cur.rownumber))

            for db_row in db_cur.fetchall():
                genotypes[db_row[7]] = cls(label = db_row[7], name = db_row[2], db_id = db_row[1],
                                           trait_tree = psql.PostgreSQLTraitTree.objectify_with_root_trait_node_id(db_id = db_row[0], db_cur_session = db_cur_session),
                                           created_by = psql.PostgreSQLUser.objectify_with_id(db_id = db_row[5], db_cur_session = db_cur_session),
                                           description = db_row[3], is_selectable = db_row[4],
                                           created_on = db_row[6])

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return genotypes

    @classmethod
    def objectify_with_sample_id(cls, sample_id: int, db_cur_session: psycopg2.cursor | None = None) -> Dict[str, PostgresSQLGenotype]:
        db_conn = None
        db_cur = db_cur_session

        genotypes: Dict[str, PostgresSQLGenotype] = {}

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                SELECT g.trait_node_id, g.id, g.name, g.description, g.is_selectable, g.created_by, g.created_on, g.label 
                    FROM genotypes AS g LEFT JOIN nm_genotypes_samples AS nm ON nm.genotype_id = g.id
                    WHERE nm.sample_id = %(sample_id)s;
                """, {"sample_id": sample_id})

            if db_cur.rowcount < 1:
                raise dlib.ABCGenotypeNotFoundError("Provided id or name does not match a single genotype. Number of returned rows = {n}".format(n=db_cur.rownumber))

            for db_row in db_cur.fetchall():
                genotypes[db_row[7]] = cls(label = db_row[7], name = db_row[2], db_id = db_row[1],
                                           trait_tree = psql.PostgreSQLTraitTree.objectify_with_root_trait_node_id(db_id = db_row[0], db_cur_session = db_cur_session),
                                           created_by = psql.PostgreSQLUser.objectify_with_id(db_id = db_row[5], db_cur_session = db_cur_session),
                                           description = db_row[3], is_selectable = db_row[4],
                                           created_on = db_row[6])

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return genotypes

    @classmethod
    def objectify_with_sample_label(cls, sample_label: str, dataset_id: int, db_cur_session: psycopg2.cursor | None = None) -> Dict[str, PostgresSQLGenotype]:
        db_conn = None
        db_cur = db_cur_session

        genotypes: Dict[str, PostgresSQLGenotype] = {}

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                SELECT g.trait_node_id, id, name, description, is_selectable, created_by, created_on, label 
                    FROM genotypes AS g 
                        LEFT JOIN nm_genotypes_samples AS nm ON nm.genotype_id = g.id
                        LEFT JOIN samples AS s ON s.id = nm.sample_id
                    WHERE s.label = %(sample_label)s AND s.dataset_id = %(dataset_id)s;
                """, {"sample_label": sample_label, "dataset_id": dataset_id})

            if db_cur.rowcount < 1:
                raise dlib.ABCGenotypeNotFoundError("Provided id or name does not match a single genotype. Number of returned rows = {n}".format(n=db_cur.rownumber))

            for db_row in db_cur.fetchall():
                genotypes[db_row[7]] = cls(label = db_row[7], name = db_row[2], db_id = db_row[1],
                                           trait_tree = psql.PostgreSQLTraitTree.objectify_with_root_trait_node_id(db_id = db_row[0], db_cur_session = db_cur_session),
                                           created_by = psql.PostgreSQLUser.objectify_with_id(db_id = db_row[5], db_cur_session = db_cur_session),
                                           description = db_row[3], is_selectable = db_row[4],
                                           created_on = db_row[6])

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return genotypes

    def write_to_db(self):
        pass