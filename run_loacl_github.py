import os
from utils.logging_config import setup_console_logging, setup_file_logging
from fastapi import FastAPI, Request, Header
import handle_pr
from utils.logging_config import get_default_logger

logger = get_default_logger()


app = FastAPI()


@app.post('/api/webhook')
async def webhook(request: Request, x_github_event: str = Header(None)):
    payload = await request.json()
    logger.info(f"Header: {x_github_event}")
    return handle_pr.handle_github_event(payload, x_github_event, True)


if __name__ == "__main__":
    local_run = os.path.exists(".env")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5555)
