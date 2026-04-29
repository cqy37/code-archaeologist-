import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


class CodeParser:
    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".java": "java",
        ".sql": "sql",
        ".ts": "typescript",
        ".go": "go",
        ".rb": "ruby",
    }

    def __init__(self):
        self.import_patterns = {
            "python": [
                r"^\s*import\s+([\w.]+)",
                r"^\s*from\s+([\w.]+)\s+import",
            ],
            "javascript": [
                r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
                r"^\s*const\s+.*?=\s+require\(['\"]([^'\"]+)['\"]\)",
                r"^\s*import\s+['\"]([^'\"]+)['\"]",
            ],
            "java": [
                r"^\s*import\s+([\w.]+);",
            ],
        }

    def detect_language(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        return self.LANGUAGE_MAP.get(ext, "unknown")

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        language = self.detect_language(file_path)
        content = self._read_file(file_path)
        if content is None:
            return {"error": "Could not read file"}

        imports = self.extract_imports(content, language)
        functions = self.extract_functions(content, language)
        classes = self.extract_classes(content, language)
        comments = self.extract_comments(content, language)

        return {
            "file_path": file_path,
            "language": language,
            "lines_of_code": len(content.splitlines()),
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "comments": comments,
            "content_preview": content[:2000],
        }

    def _read_file(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return None

    def extract_imports(self, content: str, language: str) -> List[str]:
        patterns = self.import_patterns.get(language, [])
        imports = []
        for pattern in patterns:
            imports.extend(re.findall(pattern, content, re.MULTILINE))
        return list(set(imports))

    def extract_functions(self, content: str, language: str) -> List[Dict[str, Any]]:
        functions = []
        if language == "python":
            pattern = r"^\s*def\s+(\w+)\s*\(([^)]*)\)"
            for match in re.finditer(pattern, content, re.MULTILINE):
                name = match.group(1)
                args = match.group(2)
                line_num = content[:match.start()].count("\n") + 1
                functions.append({"name": name, "args": args, "line": line_num})
        elif language == "javascript":
            patterns = [
                r"^\s*(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
                r"^\s*const\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",
                r"^\s*(\w+)\s*:\s*(?:async\s*)?\(([^)]*)\)\s*=>",
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    name = match.group(1)
                    args = match.group(2)
                    line_num = content[:match.start()].count("\n") + 1
                    functions.append({"name": name, "args": args, "line": line_num})
        elif language == "java":
            pattern = r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\(([^)]*)\)\s*\{"
            for match in re.finditer(pattern, content, re.MULTILINE):
                name = match.group(1)
                args = match.group(2)
                line_num = content[:match.start()].count("\n") + 1
                functions.append({"name": name, "args": args, "line": line_num})
        return functions

    def extract_classes(self, content: str, language: str) -> List[Dict[str, Any]]:
        classes = []
        if language == "python":
            pattern = r"^\s*class\s+(\w+)(?:\(([^)]*)\))?"
            for match in re.finditer(pattern, content, re.MULTILINE):
                name = match.group(1)
                bases = match.group(2) or ""
                line_num = content[:match.start()].count("\n") + 1
                classes.append({"name": name, "bases": bases, "line": line_num})
        elif language in ("javascript", "java"):
            pattern = r"^\s*class\s+(\w+)(?:\s+extends\s+(\w+))?"
            for match in re.finditer(pattern, content, re.MULTILINE):
                name = match.group(1)
                bases = match.group(2) or ""
                line_num = content[:match.start()].count("\n") + 1
                classes.append({"name": name, "bases": bases, "line": line_num})
        return classes

    def extract_comments(self, content: str, language: str) -> List[str]:
        comments = []
        if language in ("python", "ruby"):
            # Single-line comments
            comments.extend(re.findall(r"#\s*(.*)", content))
            # Docstrings
            docstrings = re.findall(r'"""(.*?)"""', content, re.DOTALL)
            comments.extend([d.strip() for d in docstrings])
        elif language in ("javascript", "java", "typescript", "go"):
            comments.extend(re.findall(r"//\s*(.*)", content))
            block_comments = re.findall(r"/\*(.*?)\*/", content, re.DOTALL)
            comments.extend([c.strip() for c in block_comments])
        elif language == "sql":
            comments.extend(re.findall(r"--\s*(.*)", content))
        return [c.strip() for c in comments if c.strip()]
