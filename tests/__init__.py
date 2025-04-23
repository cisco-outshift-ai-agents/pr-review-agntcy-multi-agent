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
import sys
from dotenv import load_dotenv

load_dotenv()

os.environ["TESTENV"] = "true"

# Since the source code is encapsulated in a separate subfolder (src), we need to tell this to python otherwise the imports won't work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
