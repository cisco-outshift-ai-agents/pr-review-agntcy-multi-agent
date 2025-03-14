from dotenv import load_dotenv

load_dotenv()

from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request

import handle_pr
from auth import fastapi_validate_github_signature
from utils.constants import GITHUB_EVENT_HEADER
from utils.logging_config import logger as log
app = FastAPI()


@app.post("/api/webhook")
@fastapi_validate_github_signature
async def webhook(request: Request):
    x_github_event = request.headers.get(GITHUB_EVENT_HEADER)
    if not x_github_event:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "missing x-github-event header")

    log.info(f"Received event: {x_github_event}")
    payload = await request.json()
    return handle_pr.handle_github_event(payload, x_github_event)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main_local:app", host="0.0.0.0", port=5500, reload=False, log_level="debug")
