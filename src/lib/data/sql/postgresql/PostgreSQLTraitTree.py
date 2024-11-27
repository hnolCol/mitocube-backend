from __future__ import annotations

from typing import Any, Dict, List, Tuple, Self

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql

class PostgreSQLTraitTree(dlib.ABCTraitTree):
    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            nodes: List[psql.PostgreSQLTraitNode] = [self._root]  # Fixme: Is it possible to cast here? Or necessary to overwrite the existing constructor, parameter and method to fix type?

            while len(nodes) > 0:
                node = nodes.pop(0)
                if node.get_children():
                    nodes.extend(node.get_children())  # Fixme: Chast or fix method (see comment above)
                node.write_to_db(db_cur_session = db_cur_session)

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    @staticmethod
    def get_all_root_nodes(db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLTraitTree]:
        db_conn = None
        db_cur = db_cur_session

        root_nodes: List[PostgreSQLTraitTree] = []

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT id FROM trait_nodes WHERE parent_node_id IS NULL;")

            for db_row in db_cur.fetchall():
                root_nodes.append(PostgreSQLTraitTree.objectify_with_root_trait_node_id(db_id = db_row[0], db_cur_session = db_cur_session))

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return root_nodes

    @staticmethod
    def get_all_trees_with_children(db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLTraitTree]:  # ToDo: implement get_all_trees_with_children(...)
        raise dlib.ABCTraitTreeError("get_all_trees_with_children(...) is not implemented yet")

    @staticmethod
    def query_tree_with_traits(traits: List[dlib.ABCTrait], db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLTraitTree]:  # ToDo: implement query_tree_with_traits(...)
        raise dlib.ABCTraitTreeError("query_tree_with_traits(...) is not implemented yet")

    @staticmethod
    def query_trees_with_label(search_term: str, db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLTraitTree]:  # ToDo: implement query_trees_with_label(...)
        raise dlib.ABCTraitTreeError("query_trees_with_label(...) is not implemented yet")

    @classmethod
    def objectify_with_root_trait_node_id(cls, db_id: int, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLTraitTree:
        db_conn = None
        db_cur = db_cur_session

        tree_nodes: Dict[int, psql.PostgreSQLTraitNode] = {}

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                WITH RECURSIVE trait_tree AS ( 
                    SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value FROM trait_nodes n 
                        WHERE n.id = %(db_id)s 
                    UNION SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value FROM trait_nodes n 
                            INNER JOIN trait_tree rc ON rc.id = n.parent_node_id) 
                SELECT id, trait_id, parent_node_id, name, trait_value FROM trait_tree;
                """, {"db_id": db_id})

            for db_row in db_cur.fetchall():
                tree_nodes[db_row[0]] = psql.PostgreSQLTraitNode(trait = psql.PostgreSQLTrait.objectify_with_id(db_id = db_row[1], db_cur_session = db_cur_session),
                                                                 db_id = db_row[0],
                                                                 parent_node = tree_nodes[db_row[2]] if db_row[2] else None,
                                                                 name = db_row[3],
                                                                 value = db_row[4])
                if db_row[2]:
                    tree_nodes[db_row[2]].add_child(tree_nodes[db_row[0]])

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return PostgreSQLTraitTree(root = tree_nodes[db_id])

    @classmethod
    def objectify_with_dataset_id(cls, db_id: int, db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLTraitTree]:
        db_conn = None
        db_cur = db_cur_session

        tree_nodes: Dict[int, psql.PostgreSQLTraitNode] = {}
        trees: List[PostgreSQLTraitTree] = []

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                WITH RECURSIVE trait_tree AS ( 
                    SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value 
                        FROM trait_nodes n 
                            LEFT JOIN nm_traits_datasets AS nm ON nm.trait_node_id = n.id 
                            LEFT JOIN datasets AS d ON nm.dataset_id = d.id  ---- d.label 
                        WHERE nm.dataset_id = %(db_id)s 
                    UNION SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value 
                        FROM trait_nodes n 
                            LEFT JOIN nm_traits_datasets AS nm ON nm.trait_node_id = n.id 
                            LEFT JOIN datasets AS d ON nm.dataset_id = d.id  ---- d.label 
                            INNER JOIN trait_tree rc ON rc.id = n.parent_node_id) 
                SELECT id, trait_id, parent_node_id, name, trait_value FROM trait_tree;
                """, {"db_id": db_id})

            for db_row in db_cur.fetchall():
                tree_nodes[db_row[0]] = psql.PostgreSQLTraitNode(trait = psql.PostgreSQLTrait.objectify_with_id(db_id = db_row[1], db_cur_session = db_cur_session),
                                                                 db_id = db_row[0],
                                                                 parent_node = tree_nodes[db_row[2]] if db_row[2] else None,
                                                                 name = db_row[3],
                                                                 value = db_row[4])
                if db_row[2]:
                    tree_nodes[db_row[2]].add_child(tree_nodes[db_row[0]])
                else:
                    trees.append(PostgreSQLTraitTree(root=tree_nodes[db_row[0]]))

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return trees

    @classmethod
    def objectify_with_dataset_label(cls, label: str, db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLTraitTree]:
        db_conn = None
        db_cur = db_cur_session

        tree_nodes: Dict[int, psql.PostgreSQLTraitNode] = {}
        trees: List[PostgreSQLTraitTree] = []

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                WITH RECURSIVE trait_tree AS ( 
                    SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value 
                        FROM trait_nodes n 
                            LEFT JOIN nm_traits_datasets AS nm ON nm.trait_node_id = n.id 
                            LEFT JOIN datasets AS d ON nm.dataset_id = d.id  ---- d.label 
                        WHERE d.label = %(label)s 
                    UNION SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value 
                        FROM trait_nodes n 
                            LEFT JOIN nm_traits_datasets AS nm ON nm.trait_node_id = n.id 
                            LEFT JOIN datasets AS d ON nm.dataset_id = d.id  ---- d.label 
                            INNER JOIN trait_tree rc ON rc.id = n.parent_node_id) 
                SELECT id, trait_id, parent_node_id, name, trait_value FROM trait_tree;
                """, {"label": label})

            for db_row in db_cur.fetchall():
                tree_nodes[db_row[0]] = psql.PostgreSQLTraitNode(trait = psql.PostgreSQLTrait.objectify_with_id(db_id = db_row[1], db_cur_session = db_cur_session),
                                                                 db_id = db_row[0],
                                                                 parent_node = tree_nodes[db_row[2]] if db_row[2] else None,
                                                                 name = db_row[3],
                                                                 value = db_row[4])
                if db_row[2]:
                    tree_nodes[db_row[2]].add_child(tree_nodes[db_row[0]])
                else:
                    trees.append(PostgreSQLTraitTree(root=tree_nodes[db_row[0]]))

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return trees

    @classmethod
    def objectify_with_sample_id(cls, sample_id: int, db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLTraitTree]:
        db_conn = None
        db_cur = db_cur_session

        tree_nodes: Dict[int, psql.PostgreSQLTraitNode] = {}
        trees: List[PostgreSQLTraitTree] = []

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                WITH RECURSIVE trait_tree AS ( 
                    SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value 
                        FROM trait_nodes n 
                            LEFT JOIN nm_traits_samples AS nm ON nm.trait_node_id = n.id 
                            LEFT JOIN samples AS s ON nm.sample_id = s.id  ---- s.label, s.dataset_id 
                        WHERE nm.sample_id = %(sample_id)s 
                    UNION SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value 
                        FROM trait_nodes n 
                            LEFT JOIN nm_traits_samples AS nm ON nm.trait_node_id = n.id 
                            LEFT JOIN samples AS s ON nm.sample_id = s.id  ---- s.label, s.dataset_id 
                            INNER JOIN trait_tree rc ON rc.id = n.parent_node_id) 
                SELECT id, trait_id, parent_node_id, name, trait_value FROM trait_tree;
                """, {"sample_id": sample_id})

            for db_row in db_cur.fetchall():
                tree_nodes[db_row[0]] = psql.PostgreSQLTraitNode(trait = psql.PostgreSQLTrait.objectify_with_id(db_id = db_row[1], db_cur_session = db_cur_session),
                                                                 db_id = db_row[0],
                                                                 parent_node = tree_nodes[db_row[2]] if db_row[2] else None,
                                                                 name = db_row[3],
                                                                 value = db_row[4])
                if db_row[2]:
                    tree_nodes[db_row[2]].add_child(tree_nodes[db_row[0]])
                else:
                    trees.append(PostgreSQLTraitTree(root=tree_nodes[db_row[0]]))

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return trees

    @classmethod
    def objectify_with_sample_label(cls, dataset_id: int, label: str, db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLTraitTree]:
        db_conn = None
        db_cur = db_cur_session

        tree_nodes: Dict[int, psql.PostgreSQLTraitNode] = {}
        trees: List[PostgreSQLTraitTree] = []

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""
                WITH RECURSIVE trait_tree AS ( 
                    SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value 
                        FROM trait_nodes n 
                            LEFT JOIN nm_traits_samples AS nm ON nm.trait_node_id = n.id 
                            LEFT JOIN samples AS s ON nm.sample_id = s.id  ---- s.label, s.dataset_id 
                        WHERE s.label = %(label)s AND s.dataset_id = %(dataset_id)s 
                    UNION SELECT n.id, n.trait_id, n.parent_node_id, n.name, n.trait_value 
                        FROM trait_nodes n 
                            LEFT JOIN nm_traits_samples AS nm ON nm.trait_node_id = n.id 
                            LEFT JOIN samples AS s ON nm.sample_id = s.id  ---- s.label, s.dataset_id 
                            INNER JOIN trait_tree rc ON rc.id = n.parent_node_id) 
                SELECT id, trait_id, parent_node_id, name, trait_value FROM trait_tree;
                """, {"label": label, "dataset_id": dataset_id})

            for db_row in db_cur.fetchall():
                tree_nodes[db_row[0]] = psql.PostgreSQLTraitNode(trait = psql.PostgreSQLTrait.objectify_with_id(db_id = db_row[1], db_cur_session = db_cur_session),
                                                                 db_id = db_row[0],
                                                                 parent_node = tree_nodes[db_row[2]] if db_row[2] else None,
                                                                 name = db_row[3],
                                                                 value = db_row[4])
                if db_row[2]:
                    tree_nodes[db_row[2]].add_child(tree_nodes[db_row[0]])
                else:
                    trees.append(PostgreSQLTraitTree(root=tree_nodes[db_row[0]]))

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return trees

    def write_to_db(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(db_cur_session = db_cur_session)

    def remove_from_db(self, db_cur_session: psycopg2.cursor | None = None):  # ToDo: Implement remove_from_db(...)
        raise dlib.ABCTraitTreeError("remove_from_db(...) is not implemented yet")




