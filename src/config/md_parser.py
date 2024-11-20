from config.parser_mixin import ParserMixin, ParseContentError
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
            structured_content = {}

            for section in sections:
                lines = section.strip().split("\n")
                main_title = lines[0].strip()
                content = "\n".join(lines[1:]).strip()
                # Split content by subtitles (-)
                subsections = re.split(r"^-\s+\*\*(.*?):?\*\*", content, flags=re.MULTILINE)
                if len(subsections) > 1:
                    structured_content[main_title] = {}
                    for i in range(1, len(subsections), 2):
                        subtitle = subsections[i].strip()
                        subcontent = subsections[i + 1].strip() if i + 1 < len(subsections) else ""
                        if i == 1:
                            structured_content[main_title] = f"{subtitle}: {subcontent}"
                        else:
                            structured_content[main_title] = structured_content[main_title] + f"\n{subtitle}: {subcontent}"
                else:
                    structured_content[main_title] = content
            return structured_content
        except Exception as e:
            raise ParseContentError(f"Error parsing markdown content. {e}", content)

    def __validate_md_structure(self, content: str) -> bool:
        expected_structure = [
            r"^# PRCoach Configuration File\s*$",
            r"^## Overview\s*$",
            r"^## PR Title and Description\s*$",
            r"^## PR Summary of Changes\s*$",
            r"^## Code Review\s*$",
            r"^- \*\*Terraform Syntax and Style Checks:\*\*\s*$",
            r"^## Documentation and Explanation\s*$",
            r"^- \*\*Auto-Documentation:\*\*\s*$",
            r"^- \*\*Code Comments:\*\*\s*$",
            r"^## File Structure Review\s*$",
            r"^- \*\*Consistency Checks:\*\*\s*$",
            r"^- \*\*Best Practices Comparison:\*\*\s*$",
            r"^## Cloud Environment \(as discovered by the system from your repo\)\s*$",
            r"^- \*\*Primary Cloud Provider:\*\*",
            r"^- \*\*Secondary Cloud Providers:\*\*",
            r"^## Security & Compliance Policies\s*$",
            r"^- \*\*Security Requirements:\*\*\s*$",
            r"^- \*\*Compliance Requirements:\*\*\s*$",
            r"^## Change Impact Analysis\s*$",
            r"^- \*\*Dependency Analysis:\*\*\s*$",
            r"^- \*\*Risk Assessment:\*\*\s*$",
            r"^## Continuous review\s*$",
            r"^- \*\*Linting Review:\*\*\s*$",
            r"^- \*\*Scanning Review:\*\*\s*$",
            r"^## Learning and Improvement\s*$",
            r"^- \*\*Knowledge Base:\*\*\s*$",
            r"^- \*\*KPI Tracking:\*\*\s*$",
            r"^## Expert Reviewers\s*$",
            r"^- \*\*Designated Expert Reviewers:\*\*\s*$",
            r"^## Continuous Improvement\s*$",
            r"^- \*\*Feedback Loop:\*\*\s*$",
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
