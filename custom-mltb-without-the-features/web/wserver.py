from uvloop import install

install()
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, WARNING
from asyncio import sleep
from aiohttp.client_exceptions import ClientError

from web.nodes import extract_file_ids, make_tree

getLogger("httpx").setLevel(WARNING)
getLogger("aiohttp").setLevel(WARNING)


app = FastAPI()


templates = Jinja2Templates(directory="web/templates/")

basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)

LOGGER = getLogger(__name__)


@app.get("/app/files", response_class=HTMLResponse)
async def files(request: Request):
    return templates.TemplateResponse("page.html", {"request": request})


@app.api_route(
    "/app/files/torrent", methods=["GET", "POST"], response_class=HTMLResponse
)
async def handle_torrent(request: Request):
    params = request.query_params

    if not (gid := params.get("gid")):
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "GID is missing",
                "message": "GID not specified",
            }
        )

    if not (pin := params.get("pin")):
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "Pin is missing",
                "message": "PIN not specified",
            }
        )

    code = "".join([nbr for nbr in gid if nbr.isdigit()][:4])
    if code != pin:
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "Invalid pin",
                "message": "The PIN you entered is incorrect",
            }
        )

    if request.method == "POST":
        content = {
            "files": [],
            "engine": "",
            "error": "No download client available",
            "message": "No download client available",
        }
    else:
        content = {
            "files": [],
            "engine": "",
            "error": "No download client available",
            "message": "No download client available",
        }
    return JSONResponse(content)


@app.get("/", response_class=HTMLResponse)
async def homepage():
    return (
        "<h1>See mirror-leech-telegram-bot "
        "<a href='https://www.github.com/anasty17/mirror-leech-telegram-bot'>@GitHub</a> "
        "By <a href='https://github.com/anasty17'>Anas</a></h1>"
    )


@app.exception_handler(Exception)
async def page_not_found(_, exc):
    return HTMLResponse(
        f"<h1>404: Task not found! Mostly wrong input. <br><br>Error: {exc}</h1>",
        status_code=404,
    )
