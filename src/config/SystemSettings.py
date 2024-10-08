from typing import Any, Callable, Set, List, Literal, Optional

from functools import lru_cache

from pydantic import BaseModel, EmailStr, DirectoryPath, HttpUrl, FilePath, SecretStr, IPvAnyAddress
from pydantic_settings import BaseSettings, SettingsConfigDict

# Question: does it also allow to write .env if settings changes?
'''
> python3 -m pip install python-dotenv

from dotenv import set_key  # https://github.com/theskumar/python-dotenv  # pydantic_settings never calls set_key
from pathlib import Path
env_file_path = Path("/path/to/new/.env")
env_file_path.touch(mode=0o600, exist_ok=False)  # Create the file if it does not exist.
set_key(dotenv_path=env_file_path, key_to_set="USERNAME", value_to_set="John")  
set_key(dotenv_path=env_file_path, key_to_set="EMAIL", value_to_set="abc@gmail.com")  
'''

class SystemSettings(BaseSettings):
    """System Settings"""
    model_config = SettingsConfigDict(case_sensitive = True,
                                      env_file=(".env", ".env.prod"),
                                      env_file_encoding="utf-8",
                                      extra="forbid")

    # general Settings
    app_name: str = "Nova MitoCube"
    app_description: str = "MitoCube backend "
    backend_version: str = "0.0.1 (Caterpillar)"
    allowed_middleware_url: str = "https://127.0.0.1:5000"
    # service_backend_url: str = "https://127.0.0.1:5000"
    dir_assets: str = "/home/andreaslindner/Projects/MitoCube/GitHub/mitocube-frontend/dist/assets"

    # mail settings
    mail_default_sender: str = "immunocube@gmail.com"
    mail_server: SecretStr = "smtp.googlemail.com"
    mail_port: int = 465
    mail_use_tls_ssl: str = "True"
    mail_start_tls: str = "False"
    mail_username: SecretStr = "immunocube@gmail.com"
    mail_password: SecretStr = "dsjKfl42!shFsDhgs?rjrcLyx!lI1cvj69ghoeijfndx"  # "mlbazxurazxqsvvs"
    mail_use_credentials: bool = True
    mail_validate_certs: bool = False
    mail_from_name: str = "MitoCube Support"
    mail_cc: List[EmailStr] = ["andreas.lindner@uni-bonn.de"] #"dominique.diehl@age.mpg.de",   # Fixme: change string
    mail_template_dir: DirectoryPath = "/home/andreaslindner/Projects/MitoCube/GitHub/mitocube-backend/resources/templates/email"  # Fixme: change string
    mail_template_verification: str = "verification_code.html"
    mail_template_confirmation: str = "email_confirmation.html"
    mail_template_project_state: str = "state_changed.html"
    mail_template_submission_complete: str = "submission_complete.html"
    mail_template_account_generated: str = "account_generated.html"

    # db settings
    db_handler: Literal["panda_files", "postgresql"] = "postgresql"

    # db file settings
    path_annotations: DirectoryPath = "/home/andreaslindner/Projects/MitoCube/DB_Interface_2024/resources"  # Fixme: Change string ... "/home/andreaslindner/Projects/MitoCube/GitHub/mitocube-backend/resources/features"
    path_features: DirectoryPath = "/home/andreaslindner/Projects/MitoCube/DB_Interface_2024/resources/features"  # Fixme: Change string

    # db settings: postgresql
    db_ip: Optional[IPvAnyAddress] = "127.0.0.1"  # ToDo: create validation conditions if db_handler is postgresql? Good idea. I would use the @field_validator function which is also availabe in  pydantic Settings
    db_port: Optional[int] = 5432
    db_user: Optional[SecretStr] = "immunocube"  # None
    db_name: Optional[SecretStr] = "ImmunoCubeV3"  # None
    db_pw: Optional[SecretStr] = "jflw$4Uv%9j8X4?jpeXuXYZgjpr!de2"  # None
    db_pool_connections_n_min: int = 4
    db_pool_connections_n_max: int = 16
    db_max_dataset_cached : int = 100


@lru_cache(maxsize=129, typed=False)  # Question: saves the last 128 calls, default value, currently no problem but no change of config possible!
def get_system_settings():
    return SystemSettings()
