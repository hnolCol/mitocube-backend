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
from routers.dataset import dataset, heatmap, volcano, correlation
from routers.submission import submission, comments, count, ca, metatext, quantifications, researchaim
from routers.submission.analysis import pca
from routers.submission import permissions as submissions_permissions
from routers.authentication import token, user
from routers.info import info
from routers.features import features
from routers.features.protein_groups import protein_groups
from routers.features.proteins import find as protein_find
from routers.features.proteins import receive as protein_receive
from routers.genotypes import permissions as genotype_permissions
from routers.genotypes import genotypes
from routers.attributes import attributes
from routers.instruments import instruments
from routers.network import network
from routers.filter import filter
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
from routers.maintenance import procedures
from routers.maintenance import spareparts
from routers.peptides import peptides
from routers.metatexts import metatexts
from routers.condition_applications import condition_applications
from routers.ai import openai

from routers.stats import submissions as submission_stats
# from routers import play  # route to test things during development ###########################################################

from services.json import read_json


#the order of these matters for the functioning of the routes
router_sources = [dataset,
                  protein_groups,
                  protein_find,
                  protein_receive,
                  submissions_permissions,
                  submission_stats,
                  quantifications,
                  researchaim,
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
                  attributes, 
                  instruments, 
                  network, 
                  filter, 
                  rc, 
                  proteomes, 
                  news_permissions,
                  news, 
                  performance, 
                  timelines,
                  correlation,
                  researchgroup,
                  phenotypes,
                  maintenance,
                  states,
                  symptoms,
                  procedures,
                  spareparts, 
                  peptides,
                  samples,
                  condition_applications,
                  metatext, # submission specific metatexts
                  metatexts, # metatexts in general
                  openai,
                  pca
]
    
# router_sources = [dataset, submission, attributes, token, user, features, info, annotations, play] ###########################################################

GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()
ROOT_PATH = get_absolute_path_to_dir(__file__)
CTRL_PROTEOME_SETTINGS = get_control_proteome_settings()

DB = Database.DB()

DB.attributes._utils_insert_from_file()
# print("DURATION",DB.submissions.get_durations_between_states(state_01 = SubmissionStatesEnums.SUBMITTED, state_02 = SubmissionStatesEnums.DONE))

DB.features.find(search_string = "Plxnb")
print("FOUND FEATURES", DB.features.find(search_string = "Plxnb", limit = 10))
DB.peptides.find(search_string="A", provide_protein_info=True, limit = 5)
print("FOUND PEPTIDES", DB.peptides.find(search_string="A", limit=10, provide_protein_info=False))
# print("USER TAGS", DB.submission_filter.filter_by_user(user_tags=["QCQ2qU5c"]))
#DB.submissions.insert_view(tag="lpFT2EPDd0", user_tag="QCQ2qU5c")
#DB.submissions.get_views(tag="lpFT2EPDd0")
import pandas as pd 
dataset_tag = "BkrjUoOjGN"#"LOGtC9tNC13b" # "BuXOSlIl6G" #"BuXOSlIl6G"#"0Ks1mc18NL" #"LOGtC9tNC13b"# "LOGtC9tNC13b" # "BuXOSlIl6G" #"LOGtC9tNC13b" #  #   #"MpHCYf9mShVR" # #
#m = read_json(f"/Users/hnolte/Documents/GitHub/mitocube-backend/resources/data/{dataset_tag}/params.json")
#print(m)
#meta = DatasetSubmissionModel(**m
#DB.openai.generate_cypher_query_for_prompt("Is there a protein that is only quantified in a specific tissue ?")
# 
# 
# pubmed_results = get_pubmed_ids_by_query("OMA1")
# print(pubmed_results)
# print(pubmed_results.keys())
# print(pubmed_results["esearchresult"]["idlist"])
# text = get_pubmed_publications(pubmed_results["esearchresult"]["idlist"])
# r = DB.openai.summarize_pubmed_publications(prompt=text)
# print(r)
# print(text)
print("ARTICLES!")
#print(DB.condition_applications.find(sort_by_frequency = True, limit = 1), "submission tag filter ca")
#DB.submissions.get_conditions_applications(tag = "lpFT2EPDd0")
#DB.submissions.get_conditions_applications(tag = "lpFT2EPDd0", group_by_attribute = True)
#print(DB.condition_applications.get(tag = "7ba3e7778b33e4bfe591cdd4b010246602e9e008f3b7fcb0c0659eb87ea344db"))
# , tag = m["label"])
#d = pd.read_csv(f"/Users/hnolte/Desktop/peptide_test.txt", sep="\t") #.sample(n=4000)
submission_tag = "blood"
#DB.peptides.get_abundance(tag = "SPQLLIYAATSLADGVPSR") 
#print("PEPTIDE DATA")
#DB.proteomes.insert_uniprot_proteome(proteome_tags=["UP000000589"])
#lf, tag : str, submission_tag : str, sample_name : str, sample_index : int):
#i = 0 
#d.loc[:,"tag"] = d["sequence"].values 
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



@app.get("/", include_in_schema=False)
def frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.mount("/assets", StaticFiles(directory=GENERAL_SETTINGS.frontend_build_assets, html=True), name="frontend assets")


if __name__ == "__main__":
    uvicorn.run(app, port = 5002, proxy_headers=True)
