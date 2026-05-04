from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os 
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
import argparse 



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

#check for users, essentially, create admin user if no users exists with the defined admin email.




origins = [
    "https://mitocube.age.mpg.de",
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
    #parase arguments only when running this file directly, otherwise the arguments will be parsed when importing this file, which is not desired.
    args = argparse.ArgumentParser(description="Migrate data from old json files to the database. ")

    args.add_argument("--setup_database", action="store_true", help="Whether to run the migration scripts. This should only be set to true if you want to run the migration, otherwise it should be false, as the migration scripts are not idempotent. ")
    args.add_argument("--genotypes",  help="Path pointing to a genotype json file that can be used to populate the genotypes in the database. The file should be a json file")
    args.add_argument("--migrate_submissions",  help="Path pointing to a submission folder that can be used to populate the submissions in the database. The folder should contain one folder per submission containg the files params.json and data.txt.", default=None)
    args.add_argument("--proteomes", help = "List of uniprot proteomes to be addded to the database, separated by comma. Example: UP000005640,UP000002311", default=None)
    args.add_argument("--add_control_proteome", action="store_true", help="Whether to add the control proteome to the database. The control proteome is a collection of proteins that are used for testing and development purposes. It contains common proteins such as GFP and luciferase. This should only be set to true if you want to add the control proteome, otherwise it should be false, as the control proteome is not intended for production use. ")
    args.add_argument("--resources_path", help="Path pointing to the resources folder that contains the json files for the migration. This should be a folder containing the files genotypes.json, users.json, and a folder data containing the submission folders. ", default="/home/cloud/resources/")


    args = args.parse_args()
    setup_db_default = args.setup_database
    migrate_submission_folder = args.migrate_submissions 
    proteomes_to_add = args.proteomes 
    lead_user = DB.users.get_lead_user() 
    add_control_proteome = args.add_control_proteome
    genotype_file = args.genotypes
    if setup_db_default:
        DB.users.check(lead_tag = "fOtsqZCP")
        #adding attributes, will set is_updating to true for all attributes, but this is necessary to update the attributes with the correct trait associations. Required for a proteome addition.
        DB.attributes._utils_insert_from_file(file_path =os.path.join(args.resources_path, "attributes/attributes.json"))
        #adding users, will set is_updating to true for all users, but this is necessary to update the users with the correct information. 
        DB.users._utils_migrate(path_to_user_data=os.path.join(args.resources_path, "users/users.json")) 
        DB.annotations._utils_insert_from_file(
            file_path=os.path.join(args.resources_path, "annotations/MitoCarta/annotations.json"),
            folder_path=os.path.join(args.resources_path, "annotations"),
            user_tag=lead_user,
        )
    if CTRL_PROTEOME_SETTINGS.add_control_proteome or add_control_proteome:
        control_proteome = pd.read_csv(CTRL_PROTEOME_SETTINGS.control_proteome_file, sep="\t",)
        #adding proteme details, will set is_updating to true
        DB.proteomes.add_proteome_details( proteome_tag = "ctrl", proteome_info = {"name" : "Ctrl proteome","description" : "Control / misc proteins  such as GFP, and lucZ."})
        DB.proteomes.insert_proteome_from_dataframe(control_proteome, proteome_tag="ctrl", user_tag = lead_user)
        DB.proteomes.set_updating(tag="ctrl", updating=False) #reset updating.
            
    if proteomes_to_add is not None:
        print("Adding proteomes: " + proteomes_to_add + " from Uniprot. This may take a while... If they exist already, they will be updated. ")
        proteome_list = proteomes_to_add.split(",")
        DB.proteomes.insert_uniprot_proteome(proteome_tags=proteome_list, reviewed=False, user_tag = lead_user)
    if genotype_file is not None:
        from migrate_genotypes import MigrateGenotypes 
        genotype_mapper_file_path = MigrateGenotypes(path_to_genotypes=genotype_file, fallback_user_tag=lead_user).migrate()
        
    if migrate_submission_folder is not None:
        if genotype_file is None:
            print("No genotype file provided, gentoypes are likely to be missed..")
        from MigrateDatabase import MigrateData 
        MigrateData (path_to_submission_folder = migrate_submission_folder, genotype_labels_path=genotype_mapper_file_path, fallback_user_tag = lead_user).run()
        
    if setup_db_default:
        
        DB.instrument_states._utils_insert_from_file(file_path=os.path.join(args.resources_path, "maintenance/instrumentstates.txt"), sep="\t")
        DB.maintenance_events._utils_insert_maintenance_state_from_file(file_path=os.path.join(args.resources_path, "maintenance/maintenancestates.txt"), sep="\t") 
        DB.maintenance_procedures._utils_insert_from_file(file_path=os.path.join(args.resources_path, "maintenance/procedures.txt"), sep="\t")
        DB.symptoms._utils_insert_from_file(file_path=os.path.join(args.resources_path, "symptoms/symptoms.txt"), sep="\t")

        #python3 src/app.py --setup_database --genotypes /Users/hnolte/Documents/GitHub/mitocube-backend/resources/genotypes/genotypes.json --migrate_submissions /Users/hnolte/Documents/GitHub/mitocube-backend/resources/data --proteomes UP000005640,UP000000589 --resources_path /Users/hnolte/Documents/GitHub/mitocube-backend/resources/

            
    uvicorn.run(app, port = 5002, proxy_headers=True)
