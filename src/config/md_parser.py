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

from .parser_mixin import ParserMixin, ParseContentError
import re


class MarkdownParser(ParserMixin):
    def parse_content(self, content: str) -> dict[str, str]:
        try:
            # Validate the structure of the markdown content
            if not self.__validate_md_structure(content):
                raise ParseContentError("Invalid markdown structure.", content)
            # Example parsing logic for markdown-style content
            sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
            sections = sections[1:] if len(sections) > 1 else sections
            structured_content: dict[str, str] = {}

            for section in sections:
                lines = section.strip().split("\n")
                main_title = lines[0].strip()
                content = "\n".join(lines[1:]).strip()
                # Split content by subtitles (-)
                subsections = re.split(r"^-\s+\*\*(.*?):?\*\*", content, flags=re.MULTILINE)
                if len(subsections) > 1:
                    structured_content[main_title] = ""  # Initialize as an empty string
                    for i in range(1, len(subsections), 2):
                        subtitle = subsections[i].strip()
                        subcontent = subsections[i + 1].strip() if i + 1 < len(subsections) else ""
                        if i == 1:
                            structured_content[main_title] = f"{subtitle}: {subcontent}"
                        else:
                            structured_content[main_title] += f"\n{subtitle}: {subcontent}"
                else:
                    structured_content[main_title] = content
            return structured_content
        except Exception as e:
            raise ParseContentError(f"Error parsing markdown content. {e}", content) from e

    # Validate the structure of the markdown content.
    # TODO: Implement the validation logic into the config.Config class instead of the parser.
    def __validate_md_structure(self, content: str) -> bool:
        expected_structure = [
            r"^# Alfred Configuration File\s*$",
            r"^## Overview\s*$",
            r"^## PR Title and Description\s*$",
            r"^## Code Review\s*$",
            r"^- \*\*Terraform Syntax and Style Checks:\*\*\s*$",
            r"^## Security & Compliance Policies\s*$",
            r"^- \*\*Security Requirements:\*\*\s*$",
            r"^- \*\*Compliance Requirements:\*\*\s*$",
        ]

        lines = content.split("\n")
        index = 0

        for pattern in expected_structure:
            while index < len(lines) and not re.match(pattern, lines[index].strip()):
                index += 1

            if index >= len(lines):
                return False

            index += 1

        return True
