from fastapi import FastAPI, Request, Header
import handle_pr
import os


app = FastAPI()


@app.post('/api/webhook')
async def webhook(request: Request, x_github_event: str = Header(None)):
    payload = await request.json()
    return handle_pr.handle_github_event(payload, x_github_event, True)


if __name__ == "__main__":
    local_run = os.path.exists(".env")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
