
# Backend

# Installation

## Create virtual environment

 - Python 3.11

# Install requirements 

```
pip3 install -r requirments.txt 
```

## Settings

Settings are handle using pydantics `BaseSettings` which are devided into several submodules. 
Importantly, you can overwrite the standard settings by defining them in the env file. This will overwrite the default. This is in particular useful once you download an update from the GitHub repository. This will otherwise overwrite likely changes made in the settings, but also ensures that require 
settings are available (compared to moving settings to another folder). Due to the developmental stage, __settings are likely to change__.

### Settings should to be defined in the env file. 

please note that the type is purely for your information and should be omitted in the env file. 
Upon start, if there is no user database established yet, an account will be auto-generated for the lead_contact_email. Therefore the information must be 
entered before.
The definition of the settings in the .env file in combination with ```pydantic``` ensures that upon an update of the app, you wont have to update all the settings again. 


#### Required Settings 

The following settings are required for a funcational app. Please inspect the settings yourself and add any that you would like to alter.

```python

#general settings
app_name : str = "My cool app"
lead_contact_first_name : str = "First Name"
lead_contact_last_name : str = "Last Name"
lead_contact_institute : str = "Your institute" # this name should be availabe in the attributes
lead_contact_group : str = "" # this name should be availabe in the attributes
lead_contact : EmailStr = "your.email@cool.de"
description : str = "The app offers protein-centric searches to explore the expression of a protein in all acquired proteomic datasets."
allowed_email_domains : List[str] = ["@cool-domain.de"] #users with different domain are not allowed for registration 
#please find more informaton about the frontend in the frontend repository 
frontend_build : DirectoryPath = "/.../dist" #front end build that includes the index.html for the frontend build
frontend_build_assets : DirectoryPath . # assets 

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

NUMPY==1.25.1
#db settings==1.25.1
attribute_file : FilePath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/attributes/attributes.json" #attribute file must exists
db_datadir : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/data" #path where to store data
db_userdir : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/users" #must exist

db_handler :Literal["pandafiles","postgresql"] = "pandafiles"

db_ip : IPvAnyAddress = "127.0.0.1"
db_user : str 
db_name : str
db_pw : SecretStr
```



## Starting the backend

For a first test it is useful to start the FastAPI backend directly from the virtual env. 
- activate the virtual env (```source/env/bin/activate```)
- pydantic will throw an error if the settings are of a wrong type 
- Upon start, the lead user will be created using the settings. If your email settings are correctly defined, a auto generated password will be send to the ```lead_contact``` email adress. 
- start the frontend and try to login or use the API endpoints (see docs)


# Attributes

Attributes are fundamental to the function of the web application and ensure harmonized metadata. 




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





### Start App

To start the uvivorn server.

```
python3 src/app.py
```


```bash
src
    ├── app.py
    ├── config
    │   ├── __init__.py
    │   ├── __pycache__
    │   │   └── __init__.cpython-311.pyc
    │   ├── enums
    │   │   ├── input
    │   │   │   └── types.py
    │   │   └── users
    │   │       ├── __pycache__
    │   │       │   └── roles.cpython-311.pyc
    │   │       └── roles.py
    │   ├── exceptions
    │   │   ├── HTTPExceptions.py
    │   │   └── __pycache__
    │   │       └── HTTPExceptions.cpython-311.pyc
    │   ├── models
    │   │   ├── __init__.py
    │   │   ├── affilitation
    │   │   │   └── affilitations.py
    │   │   ├── annotations
    │   │   │   ├── __init__.py
    │   │   │   ├── __pycache__
    │   │   │   │   ├── __init__.cpython-311.pyc
    │   │   │   │   ├── proteome.cpython-311.pyc
    │   │   │   │   └── uniprot.cpython-311.pyc
    │   │   │   ├── proteome.py
    │   │   │   └── uniprot.py
    │   │   ├── attributes.py
    │   │   ├── database
    │   │   │   └── neo4j
    │   │   ├── dataset
    │   │   │   ├── __pycache__
    │   │   │   │   └── Data.cpython-311.pyc
    │   │   │   ├── data.py
    │   │   │   └── params.py
    │   │   ├── input
    │   │   │   ├── README.md
    │   │   │   └── types.py
    │   │   ├── lab
    │   │   │   ├── instrumentation
    │   │   │   │   ├── liquid_chromatography.py
    │   │   │   │   └── mass_spectrometer.py
    │   │   │   └── methods
    │   │   │       └── README.md
    │   │   ├── responses.py
    │   │   ├── submissions
    │   │   │   └── submissions.py
    │   │   ├── token

    │   │   │   └── token.py
    │   │   └── user.py
    │   ├── settings
    │   │   ├── README.md
    │   │   ├── __init__.py
    │   │   ├── attributes.py
    │   │   ├── db.py
    │   │   ├── email.py
    │   │   ├── encryption.py
    │   │   ├── general.py
    │   │   ├── proteomes
    │   │   │   ├── __init__.py
    │   │   │   └── annotationsettings.py
    │   │   └── token.py
    │   └── user_input
    │       ├── __init__.py
    │       ├── performance
    │       ├── registration
    │       ├── registration.py
    │       └── submissions
    ├── lib
    │   └── data
    │       ├── DataHandling.py
    │       ├── PandaFileHandling.py
    │       ├── PostgreSQLHandling.py
    │       ├── interfaces
    │       │   ├── neo4j
    │       │   ├── pandas
    │       │   └── sql
    │       └── user
    ├── resources
    │   └── data
    │       ├── dynamic
    │       │   ├── performance
    │       │   ├── submissions
    │       │   └── tokens
    │       └── static
    │           └── datasets
    ├── routers
    │   ├── __init__.py
    │   ├── attributes
    │   │   └── attributes.py
    │   ├── authentication
    │   │   ├── __init__.py
    │   │   ├── token.py
    │   │   └── user.py
    │   ├── dataset
    │   │   ├── __init__.py
    │   │   └── dataset.py
    │   ├── features
    │   ├── performance
    │   └── submission
    │       ├── __pycache__
    │       │   └── submission.cpython-311.pyc
    │       └── submission.py
    ├── services
    │   ├── __init__.py
    │   ├── annotations
    │   │   ├── __init__.py
    │   │   └── uniprot.py
    │   ├── date.py
    │   ├── encryption.py
    │   ├── enums.py
    │   ├── ftp.py
    │   ├── mail.py
    │   ├── paths
    │   │   ├── __init__.py
    │   │   ├── paths.py
    │   │   └── utils.py
    │   ├── random_generators.py
    │   ├── read_text.py
    │   ├── regex.py
    │   ├── statistics
    │   │   ├── TestABC.py
    │   │   └── pairwise.py
    │   └── users.py
    ├── setup_utils
    │   ├── README.md
    │   ├── annotationsettings.py
    │   └── paths.py
    └── templates
        └── email
            ├── email_confirmation.html
            ├── state_changed.html
            └── verification_code.html
```