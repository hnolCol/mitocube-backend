from typing import Any, Dict, List, Type
from datetime import datetime
import warnings

import lib.data as dlib

import psycopg2
import lib.data.sql.postgresql as psql

from fastapi import APIRouter, Depends, HTTPException

from lib.rest.security import RestPermissionSteward, RestSessionInformation


router = APIRouter(prefix="/api/instruments",
                   tags=["Instruments", ""])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)

@router.get("", deprecated = True)  # ToDo: Create PRM
def rest_get_instruments(session: RestSessionInformation = Depends(RestPermissionSteward())):
    db_instruments: Type[dlib.ABCInstrument] = dlib.ABCInstrument.get_class()

    return [{"id": instrument.get_id(),
             "attribute_id": instrument.get_id(),  # Deprecated
             "attribute_tag": instrument.get_label(),  # Deprecated
             "text": instrument.get_name(),
             "tag": instrument.get_label(),  # Deprecated, use label
             "label": instrument.get_label(),
             "value": instrument.get_label(),
             "description": instrument.get_description(),
             "feature": "None"} for instrument in db_instruments.get_instruments()]  # Deprecated

@router.get("/{instrument_tag}/stats")  # ToDo: Create PRM Implement Function
def rest_get_instrument_stat(instrument_tag : str,
                             session: RestSessionInformation = Depends(RestPermissionSteward())):

    try:  ## ToDo: Move Postgresql statements to ABCInstrument class, also Deprecated code !
        # if db_cur is None: # db_cur = db_cur_session # db_cur_session: psycopg2.cursor | None = None
        db_conn = psql.PostgreSQLConnection().getConnection()
        db_cur = db_conn.cursor()

        db_cur.execute("""  SELECT NULL AS id, 'n_all_datasets' AS var, COUNT(*) AS n FROM datasets AS ds  WHERE ds.state >= %(state_measuring)s
                            UNION SELECT ms.id AS id, 'n_datasets' AS var, COUNT(*) AS n 
                                FROM datasets AS ds LEFT JOIN instruments AS ms ON ms.id = ds.instrument_id
                                WHERE ds.state >= %(state_paused)s AND ms.label = %(ms)s GROUP BY ms.id
                            UNION SELECT ms.id AS id, 'n_measuring' AS var, COUNT(*) AS n 
                                FROM datasets AS ds LEFT JOIN instruments AS ms ON ms.id = ds.instrument_id
                                WHERE ds.state >= %(state_measuring)s AND ms.label = %(ms)s GROUP BY ms.id
                            UNION SELECT ms.id AS id, 'n_published' AS var, COUNT(*) AS n 
                                FROM datasets AS ds LEFT JOIN instruments AS ms ON ms.id = ds.instrument_id
                                WHERE ds.state >= %(state_published)s AND ms.label = %(ms)s GROUP BY ms.id
                            UNION SELECT ms.id AS id, 'n_samples_dataset' AS var, COUNT(*) AS n FROM datasets AS ds
                                LEFT JOIN samples AS s ON ds.id = s.dataset_id
                                LEFT JOIN instruments AS ms ON ms.id = ds.instrument_id
                            WHERE ds.state = %(state_paused)s AND ms.label = %(ms)s GROUP BY ms.id;
                            """,
                       {"state_paused": int(dlib.DatasetState.PAUSED),
                        "state_measuring": int(dlib.DatasetState.MEASURING),
                        "state_published": int(dlib.DatasetState.ACTIVE),
                        "ms": instrument_tag})  # Fixme, change state  to dlib.DatasetState.MEASURING

        stats_instrument = {db_row[1]: db_row[2] for db_row in db_cur.fetchall()}

        db_cur.execute("""SELECT ds.id, ds.label FROM datasets AS ds 
                                LEFT JOIN instruments AS ms ON ms.id = ds.instrument_id
                            WHERE ms.label = %(ms)s ORDER BY ds.created_on DESC;""",
                       {"ms": instrument_tag})
        dataset_labels = [db_row[1] for db_row in db_cur.fetchall()]

        instrument_first_timestamp = None
        if len(dataset_labels) > 0:
            db_cur.execute("""SELECT tl.event_on FROM dataset_timeline_events AS tl LEFT JOIN datasets AS ds ON ds.id = tl.dataset_id 
                                WHERE ds.label = ANY(%(labels)s) AND tl.type = %(event_type)s ORDER BY ds.created_on DESC LIMIT 1;""",
                           {"event_type": str(dlib.DatasetTimelineEventType.DATASET_MEASURED),
                            "labels": dataset_labels})  # ToDo, create TimeLineClass Method # Fixme, check if this works above

            instrument_first_timestamp = db_cur.fetchone()[0] if db_cur.rowcount > 0 else None

    finally:  # fixme: switch to psycopg 3 to be able to use with statements?
        if db_conn:
            psql.PostgreSQLConnection().returnConnection(db_conn)


    return {"is_measuring": stats_instrument["n_measuring"] > 0 if "n_measuring" in stats_instrument.keys() else False,
            "is_measuring_submission": stats_instrument["n_measuring"] > 0 if "n_measuring" in stats_instrument.keys() else False,  # Question: What is the difference to above?
            "number_samples": stats_instrument["n_samples_dataset"] if "n_samples_dataset" in stats_instrument.keys() else 0,
            "first_use": instrument_first_timestamp.timestamp() if instrument_first_timestamp else None,  # Bug, can be None/Null if never used and Frontend shows earliest possible UNIX date
            "submissions": dataset_labels,  # List[Dict] Question ??? What format really? Confusing in the old code.
            "number_datasets": stats_instrument["n_datasets"] if "n_datasets" in stats_instrument.keys() else 0,
            "number_datasets_published": stats_instrument["n_published"] if "n_published" in stats_instrument.keys() else 0,
            "relative_number_datasets": stats_instrument["n_datasets"] / stats_instrument["n_all_datasets"] if all(key in stats_instrument.keys() for key in ("n_datasets" , "n_all_datasets")) and stats_instrument["n_all_datasets"] > 0 else 0}
