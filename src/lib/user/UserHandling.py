
import asyncio
import os 
import time 

from typing import List, Tuple
from fastapi import BackgroundTasks

from config.exceptions.HTTPExceptions import user_registration_failed, user_not_found
from config.settings.db import get_db_settings 
from config.settings.general import get_general_settings
from config.settings.email import get_email_settings

from config.models.user import AdminUserView, UsersAdminResponse, UserModelForRegistration, UserModelForUpdate
from config.models.user import UserModel, UserRolesEnum 

from services.encryption import create_password_hash
from services.random_generators import get_random_string
from services.paths.utils import check_dir_exists, join_path
from services.mail import  async_send_email
from services.json import read_json, save_json


DB_SETTINGS = get_db_settings()
GENERAL_SETTINGS = get_general_settings()
EMAIL_SETTINGS = get_email_settings()

# fake_DB : List[UserModel] = [
#     UserModel(
#         id = 1,
#         label = "asd7123a",
#         firstname="Hendrik",
#         lastname="Nolte",
#         email="h.nolte@age.mpg.de",
#         password=create_password_hash("Hallo"),
#         institute="MPI",
#         email_verified=True, 
#         research_group="Langer", 
#         role=UserRolesEnum.ADMIN),
#     UserModel(id=2,
#         label = "asdth23a",
#         firstname="Emil",
#         lastname="Nolte",
#         email="nolte@instantclue.de",
#         password=create_password_hash("Hallo"),
#         institute="CECAD",
#         email_verified=True, 
#         research_group="Krueger", 
#         role=UserRolesEnum.ADMIN)]


class UserDB:
    """
    PROTOTYPE USER DB 
    
    could break if multiple changes to the db happen at the same type
    TODO: add lock and moe to sql 
    """
    def __init__(self) -> None:
        
        user_dir = DB_SETTINGS.db_userdir
        
        exists, self.user_dir = check_dir_exists(user_dir) #create the dir if not existance
        self._load_users()

    def _get_file_path(self) -> str:
        """"""
        return join_path(self.user_dir,"users.json")

    def _load_users(self):

        user_db_file = self._get_file_path()
        if not os.path.exists(user_db_file):
            auto_pw = get_random_string(10)
            ## create lead contact
            lead_contact = UserModel(
                id = 0,
                password=create_password_hash(auto_pw),
                firstname=GENERAL_SETTINGS.lead_contact_first_name,
                lastname=GENERAL_SETTINGS.lead_contact_last_name,
                email=GENERAL_SETTINGS.lead_contact,
                research_group=GENERAL_SETTINGS.lead_contact_group,
                institute=GENERAL_SETTINGS.lead_contact_institute,
                role=UserRolesEnum.ADMIN
                )
            
            self.DB = [lead_contact]
            self._save_db()
            #send mail and await (this increases the time, but should just run the very first time the app is initiated.)
            asyncio.run(async_send_email(subject="Lead Account Generated",
                            email_to=[lead_contact.email],
                            body={
                                "app_name" : GENERAL_SETTINGS.app_name,
                                "first_name" : GENERAL_SETTINGS.lead_contact_first_name,
                                "password" : auto_pw
                            },
                            template_mame=EMAIL_SETTINGS.mail_account_generated_template,
                            include_setting_cc=True))                    
        else:
            self.DB = [UserModel(**user_props) for user_props in read_json(user_db_file)]
    

    def _update(self) -> List[UserModel]:
        """Updates Users and returns the DB"""
        self._load_users()
        return self.DB 

    def _save_db(self):
        """Save the db to a file"""
        user_db_file = self._get_file_path()
        DB = [user.model_dump(exclude_none=True) for user in self.DB]
        for n,user in enumerate(self.DB):
            DB[n]["password"] = user.password.get_secret_value()
        save_json(DB,user_db_file)


    def add_user(self, user_props : UserModelForRegistration):
        """Add user to db - user model for registration contains a randomly generated password."""
        DB = self._update()
        #check user email in db, return error
        exists, user = self.get_user_by_email(email=user_props.email)
        if exists : raise user_registration_failed
        next_id = max([user.id for user in DB])
        pw_hash = create_password_hash(user_props.password)
        user_props_from_request = user_props.model_dump(exclude=["password"])
        to_add_user = UserModel(id = next_id+1,password=pw_hash,**user_props_from_request)
        DB.append(to_add_user)
        self._save_db()


    def block_user_by_label(self, user_label : str) -> None:
        """"""
        DB = self._update()
        exists, user_to_block = self.get_user_by_label(user_label)
        if not exists: user_not_found
        user_to_block.allow_login = False 
        #ugly update TO DO update by user index
        self.DB = [user if user.label != user_to_block.label else user_to_block for user in self.DB]
        self._save_db()


    def delete_user_by_label(self, user_label : str):
        """"""
        self._update()
        exists, userInDB = self.get_user_by_label(user_label)
        if exists:
            self.DB = [user for user in self.DB if user.label != userInDB.label]
            self._save_db()

    def get_users(self) -> List[UserModel]:
        """"""
        self._update()
        return self._update()

    def get_user_by_id(self, id):
        ""
        self._update()
        users = [user for user in self.DB if user.id == id]
        if len(users) == 0:
            return False, None
        return True, users[0]
    
    def get_user_by_label(self, user_label):
        ""
        self._update()
        users = [user for user in self.DB if user.label == user_label]
        if len(users) == 0:
            return False, None
        return True, users[0]
    
    def get_user_by_email(self, email : str) -> UserModel:
        ""
        self._update()
        users = [user for user in self.DB if user.email == email]
        if len(users) == 0:
            return False, None
        return True, users[0]
    
    def get_number_of_users(self) -> int:
        self._update()
        return len(self.DB)
    

    def update_user_by_label(self,user_label : str, user_props : UserModelForUpdate):
        """Update a user in the DB by the user_label using a user_props"""
        DB = self._update()
        user_props_updated = None
        for userIdx, user in enumerate(DB):
            if user.label == user_label:
                user_props_updated = {**user.model_dump(exclude_none=True),**user_props.model_dump(exclude_none=True)}
                break 
        if user_props_updated is None:
            raise ValueError("Error while finding user.....")
        #handle error if user cannot be constructed.
        updated_user = UserModel(**user_props_updated)
    
        DB[userIdx] = updated_user
        self._save_db()

    def update_user_password_by_label(self, user_label : str, password : str):
        """Updates a user's password.

        Parameters
        ----------
        user_label : str
            The user label, a unique id given for each user. 
        password : str
            Plain string password.
        """
        user_props = None
        pw_hash = create_password_hash(password)
        DB = self._update()
        for userIdx, user in enumerate(DB):
            if user.label == user_label:
                user_props = user.model_dump(exclude_none=True,exclude=["password","updated_on"])
                break 
        if user_props is None:
            raise ValueError("Error while finding user.....")
        
        updated_user = UserModel(**user_props, password=pw_hash, updated_on=time.time())
        DB[userIdx] = updated_user
        self._save_db()
        
        

UserDB = UserDB() #ensure it is like a singleton 