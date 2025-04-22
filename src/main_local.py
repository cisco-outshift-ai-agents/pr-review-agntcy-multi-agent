# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

from dotenv import load_dotenv

load_dotenv()

from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request

import handle_pr
from auth import fastapi_validate_github_signature
from utils.constants import GITHUB_EVENT_HEADER

app = FastAPI()


@app.post("/api/webhook")
@fastapi_validate_github_signature
async def webhook(request: Request):
    x_github_event = request.headers.get(GITHUB_EVENT_HEADER)
    if not x_github_event:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "missing x-github-event header")

    payload = await request.json()
    result = await handle_pr.handle_github_event(payload, x_github_event)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main_local:app", host="0.0.0.0", port=5500, reload=False, log_level="debug")
