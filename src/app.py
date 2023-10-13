import os 

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import uvicorn

### import settings
from config.settings.general import get_general_settings
from config.settings.db import get_db_settings
### import services 
from services.paths.paths import Paths 
from services.paths.utils import get_absolute_path_to_dir

### import routers
from routers.dataset import dataset
from routers.submission import submission
from routers.attributes import attributes
from routers.authentication import token, user
from routers.features import faetures
from routers.info import info


router_sources = [dataset, submission, attributes, token,  user, faetures, info]

GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()
ROOT_PATH = get_absolute_path_to_dir(__file__)

## check and create paths
paths = Paths(ROOT_PATH, DB_SETTINGS) #class should only be used to get paths 
print(paths.submissions)


origins = [
    "http://localhost:5000",
    "http://localhost:3000"
]

app = FastAPI(
    title=GENERAL_SETTINGS.app_name,
    version=GENERAL_SETTINGS.version,
    description=GENERAL_SETTINGS.description,
    redoc_url="/api/doc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
### add routers from packages 
for rs in router_sources:
    if hasattr(rs,"router"):
        app.include_router(getattr(rs,"router"))


if __name__ == "__main__":
    
    uvicorn.run(app, port = 5000)





