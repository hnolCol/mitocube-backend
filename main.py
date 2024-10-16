from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from config import SystemSettings

import lib.rest.routes.application as routes_app
import lib.rest.routes.attributes.attributes as routes_attributes
import lib.rest.routes.auth.auth as routes_auth
import lib.rest.routes.genotypes.genotypes as routes_genotypes
import lib.rest.routes.submissions.submissions as routes_submissions
import lib.rest.routes.users.users as routes_users

import uvicorn

system_settings = SystemSettings.get_system_settings()

app = FastAPI(title = system_settings.app_name,
              version = system_settings.app_version,
              description = system_settings.app_description,
              redoc_url = "/api/doc",
              default_response_class = ORJSONResponse)

app.add_middleware(CORSMiddleware,  # FixMe: Wrong type?
                   allow_origins = [system_settings.allowed_middleware_url],
                   allow_credentials = True,
                   allow_methods = ["*"],
                   allow_headers = ["*"])

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
for item in [routes_auth, routes_app, routes_attributes, routes_genotypes, routes_submissions, routes_users]:
    if hasattr(item, "router"):
        app.include_router(getattr(item, "router"))

app.mount("/assets", StaticFiles(directory = system_settings.dir_assets,
                                 html = True),
          name = "frontend assets")

if __name__ == "__main__":
    uvicorn.run(app, port = 5000, proxy_headers = True)  # Question Port from configuration? different from
