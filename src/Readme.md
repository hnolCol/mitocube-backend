
## Backend

## Installation

### Create virtual environment

Python 3.11

### Install requirements 

```
pip3 install -r requirments.txt 
```

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
    │   │   │   └── annotations.py
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
    │   ├── annotations.py
    │   └── paths.py
    └── templates
        └── email
            ├── email_confirmation.html
            ├── state_changed.html
            └── verification_code.html
```