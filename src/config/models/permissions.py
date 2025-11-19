from pydantic import BaseModel, field_validator, model_validator
from typing import Optional 

from config.enums.users.roles import UserRolesEnum

class PermissionBaseModel(BaseModel):
    """Base model for permissions."""
    user_tag : str 
    role : UserRolesEnum = UserRolesEnum.GUEST #minimum role to access the resource
    tag : Optional[str] = None #tag of the resource, if None, the permission applies to all resources of this type 
    archive : bool = False #if True, the resource is archived and should not be shown in lists
    edit : bool = False #if True, the resource can be edited, otherwise it is read-only
    delete : bool = False #if True, the resource can be deleted, otherwise it cannot
    create : bool = False #if True, new resources of this type can be created
    comment : bool = False #if True, comments can be added to the resource 
    download : bool = False #if True, the resource can be downloaded 
    upload : bool = False #if True, the resource can be uploaded 
    state_change : bool = False #if True, the state of the resource can be changed (e.g. from measuring to published) 
    update : bool = False #if True, the resource can be updated with new data
    
    @model_validator(mode="after")
    def validate_state_change(self):
        """Validates that state_change is only True if edit is also True."""
        if self.state_change and not self.edit:
            raise ValueError("state_change can only be True if edit is also True")
        if self.state_change and not self.upload:
            raise ValueError("state_change can only be True if upload is also True")
        return self


class PermissionResponseModel(PermissionBaseModel):
    """Response model for permissions."""        