import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List
from core.knowledge_base import KnowledgeBase
from utils.llm_client import LLMClient


class ValidatorAgent:
    SYSTEM_PROMPT = """You are a QA engineer and test architect. Evaluate a refactoring plan for safety and correctness.

Respond in valid JSON with these keys:
- behavioral_consistency: string (preserved|likely_preserved|at_risk|broken)
- test_coverage_assessment: string (adequate|needs_improvement|critical_gaps)
- test_plan: list of strings (specific test cases to implement)
- edge_cases: list of strings (boundary conditions that could break)
- performance_impact: string (improved|neutral|regression_risk|unknown)
- observability: list of strings (logging/metrics that should be added)
- approval: boolean (true if safe to proceed, false if more work needed)
- warnings: list of strings (concerns that don't block but should be noted)
- required_validations: list of strings (steps that MUST be performed before merge)

Be conservative. If you are not confident the refactoring preserves behavior, set approval to false."""

    def __init__(self, llm: LLMClient, config: Dict[str, Any] = None):
        self.llm = llm
        self.config = config or {}
        self.timeout = self.config.get("timeout_seconds", 60)
        self.run_tests = self.config.get("run_tests", True)

    def validate(self, plan: Dict[str, Any], kb: KnowledgeBase) -> Dict[str, Any]:
        target = plan.get("target", "unknown")
        files = kb.get_all_files()
        target_files = [f for f in files if target in f["path"]]

        # Gather original test results if tests exist
        test_results = self._run_existing_tests(target)

        # Build prompt with plan + original code context
        prompt = self._build_prompt(plan, target_files, test_results)

        response = self.llm.complete(
            system_prompt=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        validation = self._parse_response(response["content"])
        validation["target"] = target
        validation["original_test_results"] = test_results
        validation["model"] = response.get("model", "unknown")

        # Store validation finding
        kb.store_finding(
            target, "validator", "validation_report",
            json.dumps(validation, ensure_ascii=False),
            confidence=0.9 if validation.get("approval") else 0.7
        )

        return validation

    def _run_existing_tests(self, target: str) -> Dict[str, Any]:
        """Attempt to discover and run existing tests."""
        results = {"found": False, "passed": 0, "failed": 0, "output": ""}

        if not self.run_tests:
            return results

        # Look for common test directories
        test_dirs = ["tests", "test", "__tests__", "spec"]
        test_commands = [
            ["python", "-m", "pytest", "-v", "--tb=short"],
            ["python", "-m", "unittest", "discover", "-v"],
            ["npm", "test"],
            ["mvn", "test"],
        ]

        for td in test_dirs:
            if os.path.isdir(td):
                results["found"] = True
                for cmd in test_commands:
                    try:
                        proc = subprocess.run(
                            cmd, cwd=td, capture_output=True, text=True, timeout=self.timeout
                        )
                        results["output"] = proc.stdout + proc.stderr
                        results["returncode"] = proc.returncode
                        # Attempt naive parsing
                        if "passed" in results["output"]:
                            import re
                            m = re.search(r'(\d+) passed', results["output"])
                            if m:
                                results["passed"] = int(m.group(1))
                            m = re.search(r'(\d+) failed', results["output"])
                            if m:
                                results["failed"] = int(m.group(1))
                        break
                    except Exception:
                        continue
                break

        return results

    def _build_prompt(self, plan: Dict[str, Any], files: list, test_results: Dict[str, Any]) -> str:
        file_summaries = []
        for f in files:
            file_summaries.append(
                f"File: {f['path']}\n"
                f"LOC: {f['lines_of_code']}\n"
                f"Preview:\n{f.get('content_preview', '')[:600]}\n"
            )

        plan_json = json.dumps(plan, ensure_ascii=False, indent=2)
        test_json = json.dumps(test_results, ensure_ascii=False, indent=2)

        return f"""Evaluate the following refactoring plan for safety.

## Refactoring Plan
{plan_json}

## Original Code Context
{chr(10).join(file_summaries)}

## Existing Test Results
{test_json}

## Task
Determine whether this refactoring is safe to execute. Consider:
1. Does the plan change any public APIs or observable behavior?
2. Are there sufficient tests to catch regressions?
3. What edge cases might break during the refactoring?
4. Is the rollback plan adequate?

Provide your evaluation in the requested JSON format."""

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
                "raw_evaluation": content,
                "behavioral_consistency": "unknown",
                "approval": False,
                "parse_error": True,
                "warnings": ["Could not parse structured validator output; manual review required"],
            }
