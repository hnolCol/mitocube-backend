# Settings

Settings are handle using pydantics `BaseSettings` which are devided into several submodules. 

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

