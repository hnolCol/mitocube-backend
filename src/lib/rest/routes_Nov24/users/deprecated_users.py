from typing import Any, Dict, List, Type
import warnings

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException

import lib.data as dlib
import lib.data.sql.postgresql as psql

from lib.rest.security import RestPermissionSteward, RestSessionInformation

from config import get_system_settings


router = APIRouter(prefix="/api", tags=["User", "Deprecated"])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)


@router.get("/users/roles", deprecated=True, summary="Returns the available user roles and names")  #, response_model=UseRoleReponseModel)
def rest_get_user_roles(session: RestSessionInformation = Depends(RestPermissionSteward())):  # deprecated: Needs more to return? Who is allowed to do what?
    # user : UserModel = Depends(get_user_from_token)):
    """Returns the user role enumerator."""

    db_conn = None
    try:  ## ToDo: Move Postgresql statements to respective ABC classes, also Deprecated code !
        # if db_cur is None: # db_cur = db_cur_session # db_cur_session: psycopg2.cursor | None = None
        db_conn = psql.PostgreSQLConnection().getConnection()
        db_cur = db_conn.cursor()

        db_cur.execute("""SELECT sec_g.id, sec_g.label FROM sec_permission_groups AS sec_g;""")

        return {db_row[1]: db_row[0] for db_row in db_cur.fetchall()}

    finally:  # fixme: switch to psycopg 3 to be able to use with statements?
        if db_conn:
            psql.PostgreSQLConnection().returnConnection(db_conn)


@router.get("/attributes/user", deprecated=True)  # , response_model=AttributeResponseModel)
def rest_get_user_attributes(session: RestSessionInformation = Depends(RestPermissionSteward())):  # Deprecated: will not be used in the future, at all just returns random dummy data now
    deprecated_api("/api/attributes/user -> lib.rest.routes.users.[users.py].rest_get_user_attributes()")
    user = session.get_user()
    # ToDo: Replace with simple dictionary structure
    # Question: Does not return profile but possible options for affiliation?
    # Before
    # {attributes: List[AttributeModel], attribute_values: List[AttributeValueModel]}
    # Suggesting just a dict with fields for the profile. Currently just mock data, not sure how it really works front end wise.
    # ToDo: Below does not match the Frontent at all, fix it or fix the gui?
    return {"attributes": [{"id": -1, "tag": "ratt_usernames", "text": "Username"},
                           {"id": -2, "tag": "ratt_first_name", "text": "FirstName"},
                           {"id": -3, "tag": "ratt_last_names", "text": "LastName"},
                           {"id": -4, "tag": "ratt_contact", "text": "Contact Detail"},
                           {"id": -5, "tag": "ratt_base64_image", "text": "Image"},
                           {"id": -7, "tag": "ratt_profile", "text": "Profile Information"}],
            "attribute_values": [{"id": -14, "attribute_id": -1 , "tag": "ratt_username:user", "text": "Deprecated", "value": user.get_username()},
                                 {"id": -15, "attribute_id": -2 , "tag": "ratt_username:first", "text": "Hannes", "value": user.get_firstname()},
                                 {"id": -16, "attribute_id": -3 , "tag": "ratt_username:last", "text": "Pfeffer", "value": user.get_lastname()},
                                 {"id": -17, "attribute_id": -4, "tag": "ratt_contact:email", "text": "do_not@use.me", "value": user.get_email()},
                                 {"id": -18, "attribute_id": -5 , "tag": "ratt_base64_image:profile", "text": "Upload Something", "value": user.get_base64_image()},
                                 {"id": -18, "attribute_id": -7, "tag": "ratt_profile:orcid", "text": "ORCiD", "value": user.get_orcid() if user.get_orcid() else "None"},
                                 {"id": -19, "attribute_id": -7, "tag": "ratt_profile:url", "text": "URL", "value": user.get_url() if user.get_url() else "None"},
                                 {"id": -20, "attribute_id": -7, "tag": "ratt_profile:profile_text", "text": "Profile", "value": user.get_profile_text()},
                                 {"id": -21, "attribute_id": -7, "tag": "ratt_profile:research_group", "text": "Research Group", "value": user.get_research_group().get_name() if user.get_research_group() else "No Reserach Group"},
                                 {"id": -22, "attribute_id": -7, "tag": "ratt_profile:last_login", "text": "Research Group", "value": user.get_last_login_on()}]}
