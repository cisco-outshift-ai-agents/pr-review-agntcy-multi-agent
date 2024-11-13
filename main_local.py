from http import HTTPStatus
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
import handle_pr
from auth import fastapi_validate_github_signature
from utils.logging_config import logger as log

load_dotenv()
app = FastAPI()

@app.post('/api/webhook')
@fastapi_validate_github_signature
async def webhook(request: Request):
    x_github_event = request.headers.get("x-github-event")
    if not x_github_event:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "missing x-github-event header")
    
    payload = await request.json()
    return handle_pr.handle_github_event(payload, x_github_event, True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5500)
