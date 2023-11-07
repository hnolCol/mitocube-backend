# Settings

Settings are handle using pydantics `BaseSettings` which are devided into several submodules. 
Importantly, you can overwrite the standard settings by defining them in the env file. This will overwrite the default. This is in particular 
useful and required once you download an update from the GitHub repository. This will overwrite likely changes made in the settings, but ensures that require 
settings are available.

## Settings to be defined in the env file. 

please note that the type is purely for your information and should be omitted in the env file. 
Upon start, if there is no user database established yet, an account will be auto-generated for the lead_contact_email.

```python

#general settings
app_name : str = "My cool app"
lead_contact_first_name : str = "First Name"
lead_contact_last_name : str = "Last Name"
lead_contact_institute : str = "Your institute" # this name should be availabe in the attributes
lead_contact_group : str = "" # this name should be availabe in the attributes
lead_contact : EmailStr = "your.email@cool.de"
description : str = "MitoCube offers protein-centric searches to explore the expression of a protein in all acquired proteomic datasets."
allowed_email_domains : List[str] = ["@cool-domain.de"]

frontend_build : DirectoryPath = "/.../dist" #front end build that includes the index.html for the frontend build
frontend_build_assets : DirectoryPath . 

#token settings
jwt_key : SecretStr #make it very long and random

jwt_share_key : SecretStr #make it very long and random
share_token_pw : SecretStr #a password that is required in addition to admin rights to create a share token


#mail settings
mail_server : str = "privateemail.com"
mail_port : int = 465
mail_username: str = "support@mitocube.com"
mail_default_sender : EmailStr =  "support@mitocube.com"
mail_password : SecretStr 
mail_from_name : str = "Name that apperas in an email"
mail_cc : List[EmailStr] = ["m.m@email.de"] 
mail_template_dir : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/templates/email" #absolute path


#db settings
attribute_file : FilePath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/attributes/attributes.json" #attribute file must exists
db_datadir : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/data" #path where to store data
db_userdir : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/users" #must exist

db_handler :Literal["pandafiles","postgresql"] = "pandafiles"


db_ip : IPvAnyAddress = "127.0.0.1"
db_user : str 
db_name : str
db_pw : SecretStr
```

## General

- app_name : str  The name of the app, defaults to Hive 
- version : str  Version of the app (backend)
- description : str Description of the app which is displayed in the API documentation
- 



## Token

- valid_timedelta : timedelta specify how long a token is valid.


## Email 

Specify the email settings to connect to your email of choice to send emails to users. 
The app requires a working email configuration to communicate with the users.

- mail_server 
- mail_port 

