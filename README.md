# mitocube-backend
 Backend for MitoCube Web Application


## Quick Start

- Edit configuration in folder ```config``` which are based on the ```pydantic``` BaseSettings. 
The config folder contains pydantic BaseSettings for the Database (db.py), the email settings and the files.
You will have to change the followings:

- attributes_file The file that contain all the attributes you would like to configure. 
```python
class DB(BaseSettings):
    """Base Settings"""

    attribute_file : FilePath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/attributes/attributes.json"
```
The file must exist otherwise the app wont start. 

## General Settings
The general settings allow you to specify the folliwng parameters. 

```python
class General(BaseSettings):
    """Class model for general settings"""
    app_name : str = "MitoCube"
    version : str = "0.1"
    lead_contact : EmailStr = "h.nolte@age.mpg.de"
    description : str = "MitoCube offers protein-centric searches to explore the expression of a protein in all acquired proteomic datasets."
    allowed_email_domains : List[str] = ["@age.mpg.de"]
```

Here you can specify if you would like to restrict the user registration to a certain domain of emails preventing users to use private emails using the ```allowed_email_domains``` parameter. 
If the you leave this empty, in prinicple everyone can register and have access to the data. Hence, for security reasons, this should not be an empty list. 