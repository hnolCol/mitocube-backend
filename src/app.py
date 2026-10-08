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
from config.models.submissions.comments import SubmissionCommentModel
from config.models.submissions.submissions import DatasetSubmissionModel


# 
### import services
from services.paths.utils import get_absolute_path_to_dir

from services.external.pubmed import get_pubmed_ids_by_query, get_pubmed_publications
### import routers

from routers.dataset import correlation as submission_correlation # volcano
from routers.submission import submission, comments, count, ca, metatext, quantifications, researchaim, ranking
from routers.submission.analysis import pca, volcano, annotations as submission_annotations, heatmap, compare
from routers.submission import permissions as submissions_permissions
from routers.submission import export as submission_export 
from routers.authentication import token, user
from routers.info import info
from routers.features import features
from routers.features.protein_groups import protein_groups
from routers.features.proteins import find as protein_find
from routers.features.proteins import receive as protein_receive
from routers.features.proteins import favorite as protein_favorite
from routers.features.precursors import precursors as feature_precursors
from routers.features.ptms import ptms as feature_ptms
from routers.features.precursors import count as precursor_count
from routers.features.precursors import insert as precursor_insert
from routers.features import correlations as feature_correlation
from routers.genotypes import permissions as genotype_permissions
from routers.genotypes import genotypes
from routers.attributes import permissions as attribute_permissions
from routers.attributes import attributes
from routers.instruments import instruments
#from routers.network import network
#from routers.filter import filter
from routers.annotations import permissions as annotation_permissions
from routers.annotations import annotations
from routers.rc import rc
from routers.proteomes import proteomes
from routers.news import news 
from routers.news import permissions as news_permissions
from routers.performance import performance
from routers.performance import standards as performance_standards
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
from routers.diseases import diseases
from routers.variants import Variants
from routers.diseases import ClinVar
from routers.phenotypes import PhenotypeAssociation as PhenotypeAssociation
from routers.crosslink import external_resource as crosslink_external_resource
from routers.crosslink import crosslink
from routers.protocols import protocols
from routers.mfa import mfa
from routers.policy import policy
from lib.lifespan import lifespan
import sys 



#the order of these matters for the functioning of the routes
router_sources = [policy,
                  protein_groups,
                  protein_favorite,
                  protein_find,
                  protein_receive,
                  precursor_count,
                  precursor_insert,
                  feature_precursors,
                  feature_ptms,
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
                  heatmap, 
                  volcano,
                  compare,
                  genotype_permissions, 
                  genotypes, 
                  attribute_permissions,
                  attributes, 
                  instruments,
                  annotation_permissions,
                  annotations, 
                  rc, 
                  proteomes, 
                  news_permissions,
                  news, 
                  performance, 
                  performance_standards, 
                  timelines,
                  submission_correlation,
                  feature_correlation,
                  researchgroup,
                  phenotypes,
                  maintenance,
                  mfa,
                  states,
                  maintenancepermissions,
                  symptoms,
                  procedures,
                  spareparts,
                  externalservice,
                  peptides,
                  samples,
                  condition_applications,
                  metatext,
                  metatexts,
                  openai,
                  pca,
                  submission_annotations,
                  heatmap,
                  diseases,
                  ClinVar,
                  Variants,
                  PhenotypeAssociation,
                  crosslink,
                  crosslink_external_resource,
                  protocols,
                  submission_export
]
    

GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()
ROOT_PATH = get_absolute_path_to_dir(__file__)





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
    lifespan=lifespan,
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
    if hasattr(rs,"public_router"):
        app.include_router(getattr(rs,"public_router"))

## host the static html of the frontend 
templates = Jinja2Templates(directory=GENERAL_SETTINGS.frontend_build)


@app.get("/", include_in_schema=False)
def frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.mount("/assets", StaticFiles(directory=GENERAL_SETTINGS.frontend_build_assets, html=True), name="frontend assets")

if __name__ == "__main__":
    # Setup/migration flags are handled by the dedicated CLI; see docs/SETUP.md.
    # Run the setup steps (if any flags given) and then start the server.
    from setup_utils.cli import run as run_setup

    has_setup_flags = any(a.startswith("--") and a not in ("--help",) for a in sys.argv[1:])
    if has_setup_flags:
        run_setup()
    uvicorn.run(app, port=5002, proxy_headers=True)
