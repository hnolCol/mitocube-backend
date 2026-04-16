from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import uvicorn

### import settings
from config.settings.general import get_general_settings
from config.settings.db import get_db_settings

from config.enums.states import SubmissionStatesEnums
from config.settings.proteomes.control_proteomes import get_control_proteome_settings
from config.models.submissions.comments import SubmissionCommentModel
from config.models.submissions.submissions import DatasetSubmissionModel
# f, AnnotationDatabase
# from lib.database.ABCDatabase import MCAttributes
from lib.database.Database import Database
# 

# 
### import services
from services.paths.utils import get_absolute_path_to_dir

from services.external.pubmed import get_pubmed_ids_by_query, get_pubmed_publications
#from migration.load_data import MigrateScripts 

### import routers
from routers.dataset import dataset
from routers.dataset import correlation as submission_correlation # volcano
from routers.submission import submission, comments, count, ca, metatext, quantifications, researchaim, ranking
from routers.submission.analysis import pca, volcano, annotations as submission_annotations, heatmap
from routers.submission import permissions as submissions_permissions
from routers.authentication import token, user
from routers.info import info
from routers.features import features
from routers.features.protein_groups import protein_groups
from routers.features.proteins import find as protein_find
from routers.features.proteins import receive as protein_receive
from routers.features import correlations as feature_correlation
from routers.genotypes import permissions as genotype_permissions
from routers.genotypes import genotypes
from routers.attributes import permissions as attribute_permissions
from routers.attributes import attributes
from routers.instruments import instruments
from routers.network import network
from routers.filter import filter
from routers.annotations import permissions as annotation_permissions
from routers.annotations import annotations
from routers.rc import rc
from routers.proteomes import proteomes
from routers.news import news 
from routers.news import permissions as news_permissions
from routers.performance import performance
from routers.users import views as user_views
from routers.timelines import timelines
from routers.researchgroups import researchgroup
from routers.phenotypes import phenotypes
from routers.states import states
from routers.samples import samples
from routers.maintenance import symptoms
from routers.maintenance import maintenance 
from routers.maintenance import maintenancepermissions
from routers.maintenance import procedures
from routers.maintenance import spareparts
from routers.maintenance import externalservice
from routers.peptides import peptides
from routers.metatexts import metatexts
from routers.condition_applications import condition_applications
from routers.ai import openai
from routers.stats import submissions as submission_stats
# from routers import play  # route to test things during development ###########################################################

from services.json import read_json
import pandas as pd


migrate = False

#the order of these matters for the functioning of the routes
router_sources = [dataset,
                  protein_groups,
                  protein_find,
                  protein_receive,
                  submissions_permissions, 
                  submission_stats, 
                  quantifications,
                  researchaim,
                  ranking,
                  submission, 
                  comments,
                  count,
                  ca,
                  user_views,
                  token, 
                  user, 
                  features, 
                  info, 
                  #annotations,
                  heatmap, 
                  volcano,
                  genotype_permissions, 
                  genotypes, 
                  attribute_permissions,
                  attributes, 
                  instruments, 
                  network, 
                  filter,
                  annotation_permissions,
                  annotations, 
                  rc, 
                  proteomes, 
                  news_permissions,
                  news, 
                  performance, 
                  timelines,
                  submission_correlation,
                  feature_correlation,
                  researchgroup,
                  phenotypes,
                  maintenance,
                  states,
                  maintenancepermissions,
                  symptoms,
                  procedures,
                  spareparts,
                  externalservice,
                  peptides,
                  samples,
                  condition_applications,
                  metatext, # submission specific metatexts
                  metatexts, # metatexts in general
                  openai,
                  pca,
                  submission_annotations,
                  heatmap
]
    
# router_sources = [dataset, submission, attributes, token, user, features, info, annotations, play] ###########################################################

GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()
ROOT_PATH = get_absolute_path_to_dir(__file__)
CTRL_PROTEOME_SETTINGS = get_control_proteome_settings()

DB = Database.DB()
#DB.instrument_states.get_fractional_state_durations()
# DB.attributes._utils_insert_from_file()
#DB.instrument_states._utils_insert_from_file(file_path="/Users/PParsa/Documents/GitHub/mitocube-backend/resources/maintenance/instrumentstates.txt", sep="\t")
#DB.maintenance_events._utils_insert_maintenance_state_from_file(file_path="/Users/PParsa/Documents/GitHub/mitocube-backend/resources/maintenance/maintenancestates.txt", sep="\t")        
                                     
#check for users, essentially, create admin user if no users exists with the defined admin email.
DB.users.check()
#DB.attributes._utils_insert_from_file(path_to_file ="/Users/HNolte/Documents/GitHub/mitocube-backend/resources/attributes/attributes.json")

if migrate:
    DB.users._utils_migrate(path_to_user_data="/home/cloud/resources/users/users.json")
    DB.attributes._utils_insert_from_file(path_to_file ="/home/cloud/mitocube-backend/resources/attributes/attributes.json")
    DB.instrument_states._utils_insert_from_file(file_path="/home/cloud/mitocube-backend/resources/maintenance/instrumentstates.txt", sep="\t")
    DB.maintenance_events._utils_insert_maintenance_state_from_file(file_path="/home/cloud/mitocube-backend/resources/maintenance/maintenancestates.txt", sep="\t") 
    DB.maintenance_procedures._utils_insert_from_file(path_to_file="/home/cloud/mitocube-backend/resources/maintenance/procedures.txt", sep="\t")

    if CTRL_PROTEOME_SETTINGS.add_control_proteome:
        control_proteome = pd.read_csv(CTRL_PROTEOME_SETTINGS.control_proteome_file, sep="\t",)
        #adding proteme details, will set is_updating to true
        DB.proteomes.add_proteome_details( proteome_tag = "ctrl", proteome_info = {"name" : "Ctrl proteome","description" : "Control / misc proteins  such as GFP, and lucZ."})
        DB.proteomes.insert_proteome_from_dataframe(control_proteome, proteome_tag="ctrl")
        DB.proteomes.set_updating(tag="ctrl", updating=False) #reset updating.

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


@app.get("/", include_in_schema=False)
def frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.mount("/assets", StaticFiles(directory=GENERAL_SETTINGS.frontend_build_assets, html=True), name="frontend assets")


if __name__ == "__main__":
    uvicorn.run(app, port = 5002, proxy_headers=True)
