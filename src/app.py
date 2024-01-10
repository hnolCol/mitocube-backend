from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import uvicorn

### import settings
from config.settings.general import get_general_settings
from config.settings.db import get_db_settings
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase, AnnotationDatabase
from lib.data.database.ABCDatabase import MCAttributes
### import services
from services.paths.utils import get_absolute_path_to_dir

### import routers
from routers.dataset import dataset
from routers.submission import submission
from routers.authentication import token, user
from routers.info import info
from routers.annotations import annotations, attributes
from routers.features import features
# from routers import play  # route to test things during development ###########################################################

router_sources = [dataset, submission, attributes, token, user, features, info, annotations]
# router_sources = [dataset, submission, attributes, token, user, features, info, annotations, play] ###########################################################

GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()
ROOT_PATH = get_absolute_path_to_dir(__file__)


origins = [
    "http://localhost:5000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5000"
]

app = FastAPI(
    title=GENERAL_SETTINGS.app_name,
    version=GENERAL_SETTINGS.version,
    description=GENERAL_SETTINGS.description,
    redoc_url="/api/doc",
    default_response_class=ORJSONResponse)

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

## host the static html of the frontend 
templates = Jinja2Templates(directory=GENERAL_SETTINGS.frontend_build)

db_features = PandaFeatureDatabase()
db_features.update()  # load all configured Features (UniProt)

db_annotations = AnnotationDatabase()
db_annotations.update()  # load all configured Annotations

db_attributes = MCAttributes.getAttributeDatabase()
db_attributes.update()  # pre-loads the general attribution table (not the attributes from dataset)

@app.get("/", include_in_schema=False)
def frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.mount("/assets", StaticFiles(directory=GENERAL_SETTINGS.frontend_build_assets, html=True), name="frontend assets")


if __name__ == "__main__":
    uvicorn.run(app, port = 5000)
