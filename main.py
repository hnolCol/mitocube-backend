from lib.util import DummyText

import uvicorn

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from lib.data.mem import MemEmailTokens, MemLoginTokens, MemUserTokens
import lib.data.sql.postgresql as psql

import lib.rest.routes.auth.auth as routes_auth  # Critical for user authentication

# import lib.rest.routes.application as routes_app
# import lib.rest.routes.attributes.attributes as routes_attributes

# import lib.rest.routes.genotypes.genotypes as routes_genotypes
# import lib.rest.routes.dataset.dataset as routes_dataset  # ToDo: add to routes
# import lib.rest.routes.datasets.datasets as routes_datasets  # ToDo: add to routes
# import lib.rest.routes.datasets.deprecated_datasets as routes_deprecated_datasets
# import lib.rest.routes.features.features as routes_features
# import lib.rest.routes.features.deprecated_features as routes_deprecated_features
# import lib.rest.routes.instruments.deprecated_instruments as routes_deprecated_instruments
# import lib.rest.routes.submissions.deprecated_submission as routes_deprecated_submission
# import lib.rest.routes.submissions.deprecated_submissions as routes_deprecated_submissions
# import lib.rest.routes.user.user as routes_user  # ToDo: add to routes
# import lib.rest.routes.users.users as routes_users
# import lib.rest.routes.users.deprecated_users as routes_deprecated_users

from config import SystemSettings

system_settings = SystemSettings.get_system_settings()

# Initialise token memory
MemEmailTokens()  # Fixme: is currently persistent but in a very simple way, fix MemTokens class
MemLoginTokens()
MemUserTokens()  # Fixme: is currently persistent but in a very simple way, fix MemTokens class

db_features = psql.PostgreSQLFeatureDatabase()  # todo: create 'init'/first loading method
db_features.read()


app = FastAPI(title = system_settings.app_name,
              version = system_settings.app_version,
              description = system_settings.app_api_description,
              # terms_of_service="http://example.com/terms/",  # Link to terms?
              # contact={ "name":"Deadpoolio the Amazing", "url": "http://x-force.example.com/contact/", "email": "dp@x-force.example.com"},
              # license_info={"name": "Apache 2.0", "identifier": "MIT", "URL": "http://x-force.example.com/contact/"},
              summary = DummyText.get_joke(),  # ToDo: replace with system_settings.app_description,
              openapi_url = "/openapi.json",
              docs_url = "/docs",  # Fixme: Set to 'docs_url' None to disable in live system. ToDo: make config variable to set system to live.
              redoc_url = "/redocs",  # Fixme: Set to 'redoc_url' None to disable in live system. ToDo: make config variable to set system to live.
              default_response_class = ORJSONResponse)

# Question, is it possible to use multiple Middle wares?
app.add_middleware(CORSMiddleware,
                   allow_credentials = True,
                   allow_methods = ["*"],
                   allow_headers = ["*"],
                   allow_origins = ["http://0.0.0.0:3000", "http://0.0.0.0:3001", "http://0.0.0.0:5000",
                                    "http://120.0.0.1:3000", "http://120.0.0.1:3001", "http://120.0.0.1:5000",
                                    "http://localhost:3000", "http://localhost:3001", "http://localhost:5000"])

# Basic Error Handling
# ToDo: idea would be to redirect to the main page or a url that helps to go to the right page
# Ideally, separate response within the api sub-path, how to?
# Without it just sends: "{"detail":"Not Found"}"
#@app.exception_handler(StarletteHTTPException)
#async def http_exception_handler(request, exc):
    # exc.status_code # e.g. 404
#    return FileResponse("/home/andreaslindner/Downloads/giphy.webp")  # sends 200 no 404 but the correct file
    # return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

# add routers from packages
# for item in [routes_auth, routes_app, routes_attributes, routes_features, routes_genotypes, routes_users,
#              routes_deprecated_instruments, routes_deprecated_submission, routes_deprecated_submissions,
#              routes_deprecated_users, routes_deprecated_datasets, routes_deprecated_features]:
for item in [routes_auth]:
    if hasattr(item, "router"):
        app.include_router(getattr(item, "router"))

app.mount("/assets", StaticFiles(directory = system_settings.dir_assets,
                                 html = True),
          name = "frontend assets")

if __name__ == "__main__":
    uvicorn.run(app, port = 5000, proxy_headers = True)  # Question Port from configuration? different from
