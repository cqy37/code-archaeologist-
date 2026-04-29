import json
from typing import Dict, Any
from core.knowledge_base import KnowledgeBase
from utils.llm_client import LLMClient


class RefactorAgent:
    SYSTEM_PROMPT = """You are an expert refactoring consultant. Your job is to propose safe, incremental modernization plans for legacy code.

Constraints:
- Prioritize behavioral preservation (the refactored code must do exactly the same thing)
- Favor small, reviewable changes over massive rewrites
- Include rollback checkpoints
- Add tests where coverage is missing

Respond in valid JSON with these keys:
- strategy: string (high-level approach, e.g., "Extract Strategy Pattern", "Introduce Repository Layer")
- steps: list of strings (ordered, actionable steps)
- code_changes: list of objects with keys: file, action (create|modify|delete), description, estimated_lines_changed
- tests_needed: list of strings (test scenarios to add)
- estimated_risk: string (low|medium|high)
- rollback_plan: string (how to revert if issues arise)
- prerequisites: list of strings (what must be true before starting)
- expected_benefits: list of strings (e.g., "50% reduction in cyclomatic complexity")

Be concrete. Reference specific function names and line numbers where possible."""

    def __init__(self, llm: LLMClient, config: Dict[str, Any] = None):
        self.llm = llm
        self.config = config or {}
        self.safety_level = self.config.get("safety_level", "high")

    def plan(self, target: str, kb: KnowledgeBase) -> Dict[str, Any]:
        # Gather context: file contents + reasoner findings + explorer hotspots
        files = kb.get_all_files()
        target_files = [f for f in files if target in f["path"]]

        if not target_files:
            return {"error": f"No files matching target '{target}' found in knowledge base"}

        reasoner_findings = kb.get_findings(agent="reasoner")
        module_findings = [f for f in reasoner_findings if target in f["file_path"]]

        prompt = self._build_prompt(target, target_files, module_findings)

        response = self.llm.complete(
            system_prompt=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        plan = self._parse_response(response["content"])
        plan["target"] = target
        plan["model"] = response.get("model", "unknown")

        # Store plan
        plan_id = kb.store_plan(target_files[0]["path"] if target_files else target, plan)
        plan["plan_id"] = plan_id

        return plan

    def _build_prompt(self, target: str, files: list, findings: list) -> str:
        file_summaries = []
        for f in files:
            file_summaries.append(
                f"File: {f['path']}\n"
                f"Language: {f['language']}\n"
                f"LOC: {f['lines_of_code']}\n"
                f"Functions: {[fn['name'] for fn in f.get('functions', [])]}\n"
                f"Classes: {[cls['name'] for cls in f.get('classes', [])]}\n"
                f"Preview:\n{f.get('content_preview', '')[:800]}\n"
            )

        finding_summaries = []
        for fi in findings:
            try:
                data = json.loads(fi["finding"])
                finding_summaries.append(
                    f"- Domain: {data.get('business_domain', 'unknown')}\n"
                    f"  Purpose: {data.get('purpose', 'unknown')}\n"
                    f"  Risks: {data.get('risks', [])}\n"
                )
            except Exception:
                finding_summaries.append(f"- Raw finding: {fi['finding'][:200]}")

        safety_note = f"\nSafety level required: {self.safety_level.upper()}. "
        if self.safety_level == "high":
            safety_note += "Prefer the smallest possible changes. Do not change public APIs."
        elif self.safety_level == "medium":
            safety_note += "Internal refactoring is acceptable. Maintain backward compatibility."
        else:
            safety_note += "Structural changes are allowed if justified."

        return f"""Generate a modernization plan for the legacy module: {target}

## File Context
{chr(10).join(file_summaries)}

## Business Context (from Reasoner Agent)
{chr(10).join(finding_summaries)}

## Constraints
{safety_note}

Provide your plan in the requested JSON format."""

    def _parse_response(self, content: str) -> Dict[str, Any]:
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            return json.loads(json_str)
        except Exception:
            return {
                "raw_plan": content,
                "strategy": "manual_review_required",
                "steps": ["Parse LLM output manually"],
                "estimated_risk": "unknown",
                "parse_error": True,
            }
