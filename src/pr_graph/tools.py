from langchain_core.tools import BaseTool
import re

class CalculateLineNumberTool(BaseTool):
    name = "calculate_line_number"
    description = "Calculate the line number for a given line in a modified file."
    
    def _run(self, file: str, line: str) -> int:
        """Calculate the line number for a given line in a file patch.
        
        Args:
            file: The file patch content as a string
            line: The specific line to find the line number for
            
        Returns:
            The calculated line number as an integer
        """
        if not line.startswith("+") and not line.startswith("-"):
            raise ValueError("unambigous line")
    
        if line.startswith("+"):
            skipSign = "-"
        else:
            skipSign = "+"
    
        line_number = 0
        for l in file.splitlines():
            if l.startswith(skipSign):
                continue
            line_number += 1
            if l.strip().lower() == line.strip().lower():
                return line_number

        raise ValueError("line not found")

    def _arun(self, file: str, line: str) -> None:
        """Async implementation - not supported"""
        raise NotImplementedError("CalculateLineNumberTool does not support async")

