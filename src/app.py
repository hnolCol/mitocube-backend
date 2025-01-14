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

from config.models.submissions.submissions import DatasetSubmissionModel
# from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase, AnnotationDatabase
# from lib.data.database.ABCDatabase import MCAttributes
from lib.data.database.Database import Database
# from lib.data.genotype.ABCGenotypeDatabase import MCGenotypes
# from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
### import services
from services.paths.utils import get_absolute_path_to_dir

from migration.load_data import MigrateScripts 

### import routers
from routers.dataset import dataset, heatmap, volcano, correlation
from routers.submission import submission
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
# from routers import play  # route to test things during development ###########################################################

from services.json import read_json

router_sources = [dataset, 
                  submission, 
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
                  phenotypes]

# router_sources = [dataset, submission, attributes, token, user, features, info, annotations, play] ###########################################################

GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()
ROOT_PATH = get_absolute_path_to_dir(__file__)
CTRL_PROTEOME_SETTINGS = get_control_proteome_settings()

DB = Database.DB()
print(DB)

import pandas as pd 
dataset_tag = "LOGtC9tNC13b" # "BuXOSlIl6G" #"BuXOSlIl6G"#"0Ks1mc18NL" #"LOGtC9tNC13b"# "LOGtC9tNC13b" # "BuXOSlIl6G" #"LOGtC9tNC13b" #  #   #"MpHCYf9mShVR" # #
m = read_json(f"/Users/hnolte/Documents/GitHub/mitocube-backend/resources/data/{dataset_tag}/params.json")
print(m)
meta = DatasetSubmissionModel(**m, tag = m["label"])
d = pd.read_csv(f"/Users/hnolte/Documents/GitHub/mitocube-backend/resources/data/{dataset_tag}/data.txt", sep="\t").set_index("Key") #.sample(n=4000)

phenotype_json = read_json("/Users/hnolte/Documents/GitHub/mitocube-backend/resources/phenotypes/phenotypes.json")


# ms = MigrateScripts(submissions=DB.submissions, datasets=DB.datasets, users=DB.users)
# ms.add_users()
# ms.run()

#DB.proteomes.correlate_features(tag = "UP000005640")
from lib.user.UserHandling import UserDB
from config.models.genotype import GenotypeModel
from config.models.performance import QCRunModel, QCPeptidesModel, QCPeptideModel
from config.models.timeline import TimelineInputModel
from config.models.phenotype import PhenotypeGenotypeInput, PhenotypeInputModel
from config.models.news.news import NewsModel
DB.submissions.get_correlated_features(tags=["BuXOSlIl6G"],feature_tag = "Q9Y5T4", direction = "both", filter_tag = "mc", limit=30)
DB.submissions.get_correlated_features(tags=["BuXOSlIl6G"],feature_tag = "Q9Y5T4", direction = "positive", filter_tag = "mc", limit=30)

# for p in phenotype_json:
#     DB.phenotypes.insert(PhenotypeInputModel(**p))
print("feautre")
DB.features.get_abundance_distribution(tag = "Q9Y5T4", attribute_tag = "att_acquisition")
print("==")
#DB.proteomes.get_feature_abundance_dist(tag = "UP000005640")
#print("Proteome abundance")
#users_from_db = UserDB.get_users()
#DB.users.add_users(users_from_db)
DB.insert_meta(meta)
#DB.insert_dataset(d,dataset_tag)
# DB.attributes.get_mandatory_attributes()
# print("NO STATE")
# DB.attributes.get_mandatory_attributes(state=3)
# print("MANDATRY")
# print(DB.instruments.get())
# print(DB.instruments.get_samples_by_instrument(tags=["att_ms:expl480"]))
# print("===!====")

# DB.instruments.get_counts_by_instrument_and_attribute( attribute_tags = ["att_proteome","att_gene_expression_alteration"], tags = ["att_ms:expl480"])


#print(DB.timeline.get())
#DB.timeline.insert(timeline=TimelineInputModel(content="The submission state goes crazy", submission_state=5, submission_tag="QWoxfB7omh", user_tag="lxMGhZSn"))
#print("=!§")

# DB.peptides.set_qc_peptides(peptides = QCPeptidesModel(user_tag="DsuV8w4t",peptides = [QCPeptideModel(sequence="DIPGLTDTTVPR",protein_tag="P62753"),QCPeptideModel(sequence="FDDAVVQSDFK", protein_tag="P11142")]), join = False)
# print(DB.peptides.get_qc_peptides())
# DB.qc.insert(QCRunModel(tag = "asd23a23", 
#                         instrument_name_tag="expl480", 
#                         user_tag = "DsuV8w4t", 
#                         quant_proteins=5000, 
#                         quant_peptides=12000,
#                         group_attr={'att_ms':['exploris480'],'att_lc_system':['e1200']},
#                         rt_peptides={'ASTNDFR':12.2,"TNPOTRSK" : 28.2})
            #  )
# print("========")
# abundacen = DB.features.get_avg_abundance(tags = ["Q9NZI8"])
# print(abundacen)
# f = DB.features.get_f_value(tags = ["Q9NZI8"])
# data = DB.features.get_data(tags=["Q9NZI8","Q9Y3P9"])
# print("PIVOT")

# print("HIERY",DB.attributes.get_attribute_hierarchy(tags=["att_collision_energy","att_ms_interface"]))
# #DB.attributes.get_unittype(tags = ["att_compound","att_digestion_time"])
    
# print(f)
# DB.submission_summary.get(tag=dataset_tag)
# print("========")

genotypes_from_file = [GenotypeModel(**x, proteome_tag=x["proteome_id"]) for x  in read_json("/Users/hnolte/Documents/GitHub/mitocube-backend/resources/genotypes/genotypes.json")]

# DB.proteomes.find_features(query="Fbxo",proteome_tags="asda")
# DB.proteomes.find_features(query="Fbxo",proteome_tags="UP000005640")
r = DB.features.get_quantification_count(tags=['P41587','A0JNW5',"ABS","Q8NHH1"])

#DB.unittypes.get_units(tags=["concentration","time"])
DB.samples.get_sample(tag = "20240308_LOGtC9tNC13b_05_dmso")

#check for users
DB.users.check()

if CTRL_PROTEOME_SETTINGS.add_control_proteome:
    control_proteome = pd.read_csv(CTRL_PROTEOME_SETTINGS.control_proteome_file, sep="\t",)
    DB.proteomes.add_proteome_details( proteome_tag = "ctrl", proteome_info = {"name" : "Ctrl proteome","description" : "Control / misc proteins  such as GFP, and lucZ."})
    DB.proteomes.insert_proteome_from_dataframe(control_proteome,proteome_tag="ctrl")
    

# print(da)
# print("WUHU")
# df = DB.features.get_data(tags=['A0JNW5','P41587'])
# print(df["tag"].unique())
# #print(DB.features.get_quantification_stats(tag = ))
# print(DB.features.get_quantification_stats(tags = ['P41587','A0JNW5',"ABS","Q8NHH1"]))
# overview = DB.features.get_regulation_summary(tags=['P41587','A0JNW5',"ABS","Q8NHH1"])
# print(DB.filters.get_feature_quant(tag="mitocarta_3.0", ascending = True, limit = None))
# print(DB.filters.get_abundance_distribution(tag="mitocarta_3.0"))
# print(DB.filters.get_overlap_with_dataset_quant(tags=["mitocarta_3.0","hendriks_list_of_substrates"], submission_tags = ['BuXOSlIl6G',"LOGtC9tNC13b"]))
# print("abundance dist, above")
# print(overview)D
#DB.news.insert(NewsModel(user_tag="lxMGhZSn", content="New dataset published.", submission_tags=["LOGtC9tNC13b"], feature_tags=["A4GXA9","A0A0C5B5G6"]))
#print(DB.news.get())
#DB.genotypes.add_genotypes(genotypes_from_file)

r = DB.attributes.get_attributes_by_search_string(search_string = "comp")
print("SEARCH", r)
#DB.proteomes.insert_uniprot_proteome()
#r = DB.datasets.get_datatable(tag = dataset_tag)

#DB.filters.isin(tag="mitocarta_3.0", feature_tags=["Q15070"])

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
