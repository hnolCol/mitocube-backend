from functools import lru_cache

from pydantic import EmailStr
from pydantic import SecretStr
from pydantic import DirectoryPath
from pydantic_settings import BaseSettings 

from typing import List

class Email(BaseSettings):
    """
    Settings to connect to the email server that
    allows the app to send emails to users, but
    also to the maintainers using the cc_email.
    see class CarbonCopyEmailList
    """
    mail_server : str = "mail.ox.gwdg.de"#"mail.privateemail.com"
    mail_port : int = 587
    mail_username: str
    mail_use_tls_ssl: bool = False
    mail_start_tls : bool = True
    mail_default_sender : EmailStr =  "mitocube@age.mpg.de"
    mail_password : SecretStr 
    mail_use_crendentials : bool = True
    mail_validate_certs : bool = False
    mail_from_name : str = "MitoCube Support"
    mail_cc : List[EmailStr] = ["h.nolte@age.mpg.de","mitocube@age.mpg.de"] #"dominique.diehl@age.mpg.de", 
    mail_template_dir : DirectoryPath
    mail_verification_template : str = "verification_code.html"
    mail_confirmation_template : str = "email_confirmation.html"
    mail_project_state_template : str = "state_changed.html"
    mail_submission_complete_template : str = "submission_complete.html"
    mail_account_generated_template : str = "account_generated.html"
    mail_proteome_added_template : str = "proteome_added.html"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_email_settings():
    """Returns the Email Settings"""
    return Email()