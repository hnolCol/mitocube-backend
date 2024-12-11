import asyncio 
from typing import Dict, List, Tuple
from neo4j import Driver, Result 

from lib.data.database.abstract.Users import UserABC 

from config.enums.users.roles import UserRolesEnum 
from config.models.user import UserModel, UserModelForRegistration

from config.settings.general import get_general_settings 
from config.settings.email import get_email_settings

from services.encryption import create_password_hash 
from services.random_generators import get_random_string 
from services.mail import async_send_email

GENERAL_SETTINGS = get_general_settings()
EMAIL_SETTINGS = get_email_settings()

def transform_query_result(result):
    "Transforms the result into a list of data."
    return result.data()[0]["query_result"]

class Neo4JUser(UserABC):
    
    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver 
        
        
    def get_tags(self, limit: int = None) -> List[str]:
        
        query = (
            "MATCH (u:User) "
            "RETURN u.tag ORDER BY u.created_at "
        )    
        if limit is not None:
            query += "LIMIT $limit"
            
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, limit = limit)
        return r 
    
    def check(self) -> None:
        self._check_user()    
    
    def _check_user(self):
        ""
        if self.count() == 0:
            auto_pw = get_random_string(10)
            lead_contact = UserModel(
                password=create_password_hash(auto_pw),
                firstname=GENERAL_SETTINGS.lead_contact_first_name,
                lastname=GENERAL_SETTINGS.lead_contact_last_name,
                email=GENERAL_SETTINGS.lead_contact,
                research_group=GENERAL_SETTINGS.lead_contact_group,
                institute=GENERAL_SETTINGS.lead_contact_institute,
                role=UserRolesEnum.ADMIN,
                is_lead_admin=True
                )
            self.add_user(lead_contact)
            print("Lead user created...")
            asyncio.run(async_send_email(
                            subject="Lead Account Generated",
                            email_to=[lead_contact.email],
                            body={
                                "app_name" : GENERAL_SETTINGS.app_name,
                                "first_name" : GENERAL_SETTINGS.lead_contact_first_name,
                                "password" : auto_pw
                            },
                            template_mame=EMAIL_SETTINGS.mail_account_generated_template,
                            include_setting_cc=True))                    
            
        
    def add_user(self, user : UserModelForRegistration):
        ""
        ##check if user exists 
        if self.get_user_by_email(email = user.email) is not None:
            raise ValueError("User with email exists already.")
        
        self.add_users(users = [user])
        
    def add_users(self, users : List[UserModel]):
        """Adds users to the database from a list of users

        Parameters
        ----------
        users : List[UserModel]
            The users to be added using the common pydantic UserModel. 
        """
        user_props = [{"tag" : user.tag, 
                       "props" : {**user.model_dump(exclude=["password"], exclude_none=True),
                                "password" : user.password.get_secret_value(),
                                "s" : " ".join([user.firstname,user.lastname,user.email]).lower()
                        }} for user in users]
                       
        query = (
            "UNWIND $props as user_prop "
            "MERGE (u:User {tag : user_prop.tag}) "
            "ON CREATE "
            "SET u += user_prop.props, u.created_at = timestamp() "
            "ON MATCH "
            "SET u += user_prop.props"
            
        )
        
        self._driver.execute_query(query, props = user_props, routing_="w")
        
        # self.factory.create_multiple_nodes(
        #     NodeLabelModel(cypher_label="u",label="User"), 
        #     nodes = user_nodes)
    
    def block_user_by_tag(self, tag : str) -> bool:
        """Blocks a user. The user is not able to login. 

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        bool
            _description_
        """
        cypher_query = (
            "MATCH (u:User {tag : $tag}) "
            "SET u.allow_login = False "
        )
        try:
            _ = self._driver.execute_query(cypher_query , 
                                        database_="neo4j", 
                                        routing_="w", 
                                        tag = tag)
        except Exception as e:
            print("Query finding resulted in an error " + str(e))
            return False
        return True
    
    def count(self) -> int:
        ""
        query = (
            "MATCH (u:User) "
            "RETURN count(u) "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return r[0]

    def delete_user(self, tag: str) -> bool:
        return super().delete_user(tag)
    
    
    def is_user_allowed(self, tag : str) -> Tuple[bool,UserModel|None]:
        ""
        user = self.get_user_by_tag(tag)
        if user is None or not user.allow_login:
            return False, None
        return True, user
    
    def is_user(self, tag : str) -> bool:
        """Checks if the tag is associated with a user
        in the database. 

        Parameters
        ----------
        tag : str
            user tag.

        Returns
        -------
        bool
            If a  user with the given tag exists in the database.
        """
        return self.get_user_by_tag(tag) is not None
        
    def get_users(self) -> List[UserModel]:
        """Returns alls user in the database. 

        Returns
        -------
        List[UserModel]
            The user found in the database. 
        """
        query = (
            "MATCH (u:User) "
            "RETURN properties(u) "
        )
        r = self._driver.execute_query(query,routing_="r",database_="neo4j",result_transformer_= Result.value)
        return [UserModel(**ri) for ri in r]
    
    def get_user_by_email(self, email : str) -> UserModel|None:
        ""
        cypher_query = (
            "MATCH (u:User) "
            "WHERE u.email = $email "
            "RETURN properties(u) "
        )
        try:
            u = self._driver.execute_query(cypher_query , 
                                        database_="neo4j", 
                                        routing_="r", 
                                        result_transformer_= Result.value,
                                        email = email
                                        )
        except Exception as e:
            print("Query finding resulted in an error " + str(e))
            return None
        if len(u) == 0: return 
        return UserModel(**u[0])

    def get_user_by_tag(self, tag : str) -> UserModel|None:
        """Returns the user by its tag if a user with 
        the tag exists. 

        Parameters
        ----------
        tag : str
            The unique tag that is associated with the user. 

        Returns
        -------
        UserModel|None
            The user or None if the no user was found using the 
            given tag.
        """
        user = self.get_users_by_tags(tags=[tag])
        if len(user) == 0: return None 
        return user[0]
    
    def get_users_by_tags(self, tags : List[str] = None) -> List[UserModel]:
        """Returns a list of users by a list of tags.
        If a user is not in the database, it is simply ignored.

        Parameters
        ----------
        tags : List[str]
            The list of tags to find users for. 

        Returns
        -------
        List[UserModel]
            The list of users found by the tag. If a user is not 
            in the database (e.g. no tag associated with a user)
            then it is simply ignored. 
        """
        if tags is None: return self.get_users()
        query = (
            "MATCH (u:User) "
            "WHERE u.tag in $tags "
            "RETURN properties(u) "
        )
        
        users = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tags=tags)        
        return [UserModel(**u) for u in users]
       
        
    
    
    def find_user(self, query : str, limit : int = 10) -> List[UserModel]:
        """Finds user by 'query' string. The result is limited to a number of
        users given by 'limit'.

        Parameters
        ----------
        query : str
            The query string used to filter the data. 
        limit : int, optional
            The maximum of users that should be returned, by default 10

        Returns
        -------
        List[UserModel]
            List of users that match the query string. The maximum length
            is limit (default 10) but can be smaller if less user match.
        """
        cypher_query = (
            "MATCH (u:User) "
            "WHERE u.s CONTAINS $query_string "
            "RETURN collect(u)[0..$limit] as query_result " 
        )
        try:
            users = self._driver.execute_query(cypher_query , 
                                        database_="neo4j", 
                                        routing_="r", 
                                        result_transformer_= transform_query_result,
                                        query_string = query.lower(),
                                        limit = limit)
        except Exception as e:
            print("Query finding resulted in an error " + str(e))
            return []
        return [UserModel(**u, label = u["tag"]) for u in users]

    def update(self, tag: str, user_props: Dict) -> bool:
        return super().update(tag, user_props)