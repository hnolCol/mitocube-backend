from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import uvicorn

### import settings
from config.settings.general import get_general_settings
from config.settings.db import get_db_settings

from config.settings.proteomes.control_proteomes import get_control_proteome_settings
from config.models.submissions.comments import SubmissionCommentModel
from config.models.submissions.submissions import DatasetSubmissionModel
# from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase, AnnotationDatabase
# from lib.database.ABCDatabase import MCAttributes
from lib.database.Database import Database
# from lib.data.genotype.ABCGenotypeDatabase import MCGenotypes
# from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
### import services
from services.paths.utils import get_absolute_path_to_dir

#from migration.load_data import MigrateScripts 

### import routers
from routers.dataset import dataset, heatmap, volcano, correlation
from routers.submission import submission, comments, count
from routers.authentication import token, user
from routers.info import info
from routers.annotations import annotations
from routers.features import features
from routers.genotypes import genotypes
from routers.attributes import attributes
from routers.instruments import instruments
from routers.network import network
from routers.filter import filter
from routers.rc import rc
from routers.proteomes import proteomes
from routers.news import news
from routers.performance import performance
from routers.unittypes import unittypes
from routers.timelines import timelines
from routers.researchgroups import researchgroup
from routers.phenotypes import phenotypes
from routers.states import states
from routers.maintenance import symptoms
from routers.maintenance import maintenance 
from routers.maintenance import procedures
from routers.maintenance import spareparts
from routers.peptides import peptides
# from routers import play  # route to test things during development ###########################################################

from services.json import read_json

router_sources = [dataset, 
                  submission, 
                  comments,
                  count,
                  token, user, 
                  features, 
                  info, 
                  annotations,
                  heatmap, 
                  volcano, 
                  genotypes, 
                  attributes, 
                  instruments, 
                  network, 
                  filter, 
                  rc, 
                  proteomes, 
                  news, 
                  performance, 
                  unittypes,
                  timelines,
                  correlation,
                  researchgroup,
                  phenotypes,
                  maintenance,
                  states,
                  symptoms,
                  procedures,
                  spareparts, 
                  peptides]

# router_sources = [dataset, submission, attributes, token, user, features, info, annotations, play] ###########################################################

GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()
ROOT_PATH = get_absolute_path_to_dir(__file__)
CTRL_PROTEOME_SETTINGS = get_control_proteome_settings()

DB = Database.DB()
print(DB)
print(DB.submissions.count(state=4))
print(DB.submissions.count(state=3))
import pandas as pd 
dataset_tag = "BkrjUoOjGN"#"LOGtC9tNC13b" # "BuXOSlIl6G" #"BuXOSlIl6G"#"0Ks1mc18NL" #"LOGtC9tNC13b"# "LOGtC9tNC13b" # "BuXOSlIl6G" #"LOGtC9tNC13b" #  #   #"MpHCYf9mShVR" # #
#m = read_json(f"/Users/hnolte/Documents/GitHub/mitocube-backend/resources/data/{dataset_tag}/params.json")
#print(m)
#meta = DatasetSubmissionModel(**m, tag = m["label"])
d = pd.read_csv(f"/Users/hnolte/Desktop/peptide_test.txt", sep="\t") #.sample(n=4000)
submission_tag = "blood"
#DB.peptides.get_abundance(tag = "SPQLLIYAATSLADGVPSR") 
#print("PEPTIDE DATA")
#DB.proteomes.insert_uniprot_proteome(proteome_tags=["UP000000589"])
#lf, tag : str, submission_tag : str, sample_name : str, sample_index : int):
i = 0 
d.loc[:,"tag"] = d["sequence"].values 
# #DB.peptides._insert_peptides(data = d[["sequence", "protein_tag", "start", "end", "tag"]])
# for colName in d.columns:
#     if colName not in ["protein_tag", "start", "end","tag","sequence"]:
#         print(colName)
#         print(d[["tag", colName]].rename(columns={colName:"value"}))
#         #sample_tag = DB.samples.insert(submission_tag=submission_tag, sample_name=colName, sample_index=i)
#         DB.peptides.insert_quantification_data_from_df(submission_tag=submission_tag, 
#                                                        sample_name=colName, 
#                                                        quantification_data=d[["tag", colName]].rename(columns={colName:"value"}))
#         i += 1

# r = DB.peptides.correlate_to(tag = "EYLSMLTDINGK", exclude_within_protein_correlation=True, limit = 10, min_size=50)
# print(r, "correlate to EYLSMLTDINGK")
# r = DB.peptides.correlate_peptides_of_proteins(protein_tags=["E9Q414"])
# print(r)

# DB.submissions.insert_condition_application(tag = "asda224", attribute_tag = "att_compound",
#                                           trait_tag = "att_compound:cccp") 

# DB.submissions.insert_condition_application(tag = "asda224",
#                                           trait_data = [
#                                               {"type" : "Attribute", "tag" : "att_compound", 
#                                                "children" : [
#                                                    {"type" : "Trait", "tag" : "att_compound:hydroxyurea",  
#                                                     "children" : [
#                                                         {"type" : "Attribute", "tag" : "att_concentration", 
#                                                          "children" : [{"type" : "Trait", "tag" : "att_concentration:M", "value" : 2}]}]}]}]) 
                                          
                                          
#check for users
DB.users.check()


if CTRL_PROTEOME_SETTINGS.add_control_proteome:
    control_proteome = pd.read_csv(CTRL_PROTEOME_SETTINGS.control_proteome_file, sep="\t",)
    DB.proteomes.add_proteome_details( proteome_tag = "ctrl", proteome_info = {"name" : "Ctrl proteome","description" : "Control / misc proteins  such as GFP, and lucZ."})
    DB.proteomes.insert_proteome_from_dataframe(control_proteome,proteome_tag="ctrl")
    

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

# db_features = PandaFeatureDatabase()
# db_features.update()  # load all configured Features (UniProt)

# db_annotations = AnnotationDatabase()
# db_annotations.update()  # load all configured Annotations

# db_attributes = MCAttributes.getAttributeDatabase()
# db_attributes.update()  # pre-loads the general attribution table (not the attributes from dataset)

# db_genotypes = MCGenotypes.getGenotypeDatabase()
# db_genotypes.update()


@app.get("/", include_in_schema=False)
def frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.mount("/assets", StaticFiles(directory=GENERAL_SETTINGS.frontend_build_assets, html=True), name="frontend assets")


if __name__ == "__main__":
    uvicorn.run(app, port = 5002, proxy_headers=True)
