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

def wrap_prompt(*args):
    lines = []
    min_indent = 999999  # arbitrary large number

    for arg in args:
        for line in arg.split("\n"):
            if line.lstrip():
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
            lines.append(line)

    normalized_lines = []
    for line in lines:
        if line.lstrip():
            current_indent = len(line) - len(line.lstrip())
            relative_indent = current_indent - min_indent
            normalized_lines.append(" " * relative_indent + line.lstrip().rstrip())
        else:
            normalized_lines.append("")

    return "\n".join(normalized_lines)
