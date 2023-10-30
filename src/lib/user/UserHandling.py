

from config.models.user import User, UserRolesEnum 
from services.encryption import create_password_hash
from typing import List, Tuple

from config.models.user import AdminUserView, UsersAdminResponse

fake_DB : List[User] = [
    User(
        id = 1,
        label = "asd7123a",
        firstname="Hendrik",
        lastname="Nolte",
        email="h.nolte@age.mpg.de",
        password=create_password_hash("Hallo"),
        institute="MPI",
        email_verified=True, 
        research_group="Langer", 
        role=UserRolesEnum.ADMIN),
    User(id=2,
        label = "asdth23a",
        firstname="Emil",
        lastname="Nolte",
        email="nolte@instantclue.de",
        password=create_password_hash("Hallo"),
        institute="CECAD",
        email_verified=True, 
        research_group="Krueger", 
        role=UserRolesEnum.ADMIN)]


class UserDB:


    def get_users(self) -> List[User]:
        """"""
        return fake_DB

    def get_user_by_id(self, id):
        ""
        users = [user for user in fake_DB if user.id == id]
        if len(users) == 0:
            return False, None
        return True, users[0]
    
    def get_user_by_label(self, user_label):
        ""
        users = [user for user in fake_DB if user.label == user_label]
        if len(users) == 0:
            return False, None
        return True, users[0]
    
    def get_user_by_email(self, email : str) -> User:
        ""
        users = [user for user in fake_DB if user.email == email]
        if len(users) == 0:
            return False, None
        return True, users[0]
    
    def get_number_of_users(self) -> int:
        return len(fake_DB)

UserDB = UserDB() #ensure it is like a singleton 