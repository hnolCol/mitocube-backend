from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse  # PlainTextResponse

import api.routes.info as routes_info

import uvicorn

app = FastAPI(title = "GENERAL_SETTINGS.app_name",
              version = "GENERAL_SETTINGS.version",
              description = "GENERAL_SETTINGS.description",
              redoc_url = "/api/doc",
              default_response_class = ORJSONResponse)

app.add_middleware(CORSMiddleware,  # FixMe: Wrong type?
                   allow_origins = ["http://127.0.0.1:5000"],
                   allow_credentials = True,
                   allow_methods = ["*"],
                   allow_headers = ["*"])

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return FileResponse("/home/andreaslindner/Downloads/giphy.webp")
    # return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

### add routers from packages
for item in [routes_info]:
    if hasattr(item, "router"):
        app.include_router(getattr(item, "router"))

## host the static html of the frontend
# ToDo: Look that up
frontend_client = Jinja2Templates(directory = "/home/andreaslindner/Projects/MitoCube/GitHub/mitocube-frontend/dist")

@app.get("/", include_in_schema=False)
def frontend(request: Request):
    return frontend_client.TemplateResponse("index.html", {"request": request})

app.mount("/assets", StaticFiles(directory = "/home/andreaslindner/Projects/MitoCube/GitHub/mitocube-frontend/dist/assets",
                                 html = True),
          name = "frontend assets")

if __name__ == "__main__":
    uvicorn.run(app, port = 5000, proxy_headers = True)
