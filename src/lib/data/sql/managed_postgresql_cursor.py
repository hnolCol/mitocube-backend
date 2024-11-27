from contextlib import contextmanager

import lib.data.sql.postgresql as psql

# Example how to use:
# def db_insert(self, db_cur_session: psycopg2.cursor | None = None):
#    with managed_db_cursor(db_cur_session) as db_cur:
#        # Do something here
#        pass

@contextmanager
def managed_db_cursor(db_cur=None):  # ToDo: check if this works, https://docs.python.org/3/library/contextlib.html
    db_conn = None
    try:
        if db_cur is None:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

        yield db_cur

        if db_conn:
            db_conn.commit()
    except Exception as err:
        if db_conn:
            db_conn.rollback()
        raise err
    finally:
        if db_conn:
            psql.PostgreSQLConnection().returnConnection(db_conn)
