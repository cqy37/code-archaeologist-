import json
from typing import Dict, Any
from core.knowledge_base import KnowledgeBase
from utils.llm_client import LLMClient


class ReasonerAgent:
    SYSTEM_PROMPT = """You are a senior software architect and business analyst specializing in legacy systems.
Your task is to analyze source code and reconstruct the business intent, data flow, and hidden constraints.

Respond in valid JSON with these keys:
- business_domain: string (e.g., "Billing", "Inventory", "User Management")
- purpose: string (one-sentence description of what this code does)
- key_entities: list of strings (important variables, tables, domain objects)
- data_flow: string (step-by-step description of how data transforms)
- assumptions: list of strings (implicit business rules or constraints)
- risks: list of strings (technical debt, maintainability issues, bugs waiting to happen)
- documentation_gaps: list of strings (what should be documented but isn't)
- confidence: float (0.0 to 1.0)

Be precise. If you cannot infer something, state "unknown" rather than guessing."""

    def __init__(self, llm: LLMClient, config: Dict[str, Any] = None):
        self.llm = llm
        self.config = config or {}
        self.chunk_size = self.config.get("chunk_size", 200)

    def analyze(self, file_path: str, kb: KnowledgeBase) -> Dict[str, Any]:
        file_info = kb.get_file(file_path)
        if not file_info:
            return {"error": f"File not found in knowledge base: {file_path}"}

        content = file_info.get("content_preview", "")
        language = file_info.get("language", "unknown")
        functions = file_info.get("functions", [])
        imports = file_info.get("imports", [])

        prompt = self._build_prompt(file_path, language, content, functions, imports)

        response = self.llm.complete(
            system_prompt=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        result = self._parse_response(response["content"])
        result["file_path"] = file_path
        result["model"] = response.get("model", "unknown")

        # Store findings
        kb.store_finding(
            file_path, "reasoner", "business_intent",
            json.dumps(result, ensure_ascii=False),
            confidence=result.get("confidence", 0.8)
        )

        return result

    def analyze_module(self, target: str, kb: KnowledgeBase) -> Dict[str, Any]:
        """Analyze a logical module by aggregating findings across related files."""
        all_files = kb.get_all_files()
        module_files = [f for f in all_files if target in f["path"]]

        if not module_files:
            return {"error": f"No files matching target '{target}' found"}

        aggregated = {
            "target": target,
            "files_analyzed": [f["path"] for f in module_files],
            "findings": [],
            "summary": {},
        }

        for f in module_files:
            finding = self.analyze(f["path"], kb)
            aggregated["findings"].append(finding)

        # Generate module-level summary
        summary = self._summarize_module(aggregated["findings"])
        aggregated["summary"] = summary

        kb.store_finding(
            target, "reasoner", "module_summary",
            json.dumps(summary, ensure_ascii=False),
            confidence=0.85
        )

        return aggregated

    def _build_prompt(self, file_path: str, language: str, content: str,
                      functions: list, imports: list) -> str:
        func_summary = "\n".join([f"  - {f['name']}({f['args']}) at line {f['line']}" for f in functions[:20]])
        import_summary = "\n".join([f"  - {i}" for i in imports[:20]])

        return f"""Analyze the following legacy code file and reconstruct its business intent.

File: {file_path}
Language: {language}
Functions:
{func_summary}

Imports/Dependencies:
{import_summary}

Source Code (first ~2000 chars):
```
{content}
```

Provide your analysis in the requested JSON format."""

    def _parse_response(self, content: str) -> Dict[str, Any]:
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            return json.loads(json_str)
        except Exception:
            return {
                "raw_analysis": content,
                "business_domain": "unknown",
                "purpose": "unknown",
                "confidence": 0.0,
                "parse_error": True,
            }

    def _summarize_module(self, findings: list) -> Dict[str, Any]:
        domains = set()
        purposes = []
        all_risks = []
        all_entities = set()

        for f in findings:
            domains.add(f.get("business_domain", "unknown"))
            purposes.append(f.get("purpose", ""))
            all_risks.extend(f.get("risks", []))
            all_entities.update(f.get("key_entities", []))

        return {
            "primary_domain": list(domains)[0] if len(domains) == 1 else list(domains),
            "purpose_overview": " ".join(purposes[:3]),
            "key_entities": sorted(list(all_entities))[:20],
            "consolidated_risks": list(set(all_risks))[:10],
            "files_count": len(findings),
        }
