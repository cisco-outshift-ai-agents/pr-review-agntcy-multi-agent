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

import os

from utils.constants import ENVIRONMENT_ENV, LANGCHAIN_API_KEY_ENV
from utils.secret_manager import secret_manager


def set_environment_variables():
    if os.getenv(ENVIRONMENT_ENV) == "local" or secret_manager.langchain_api_key is None:
        return

    os.environ[LANGCHAIN_API_KEY_ENV] = secret_manager.langchain_api_key
