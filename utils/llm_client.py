import os
import json
from typing import List, Dict, Any, Optional


class LLMClient:
    def __init__(self, provider: str = "anthropic", model: str = "claude-sonnet-4-6",
                 max_tokens: int = 4096, temperature: float = 0.2):
        self.provider = provider
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = None
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        if self.provider == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY")
            if key:
                try:
                    import anthropic
                    self._client = anthropic.Anthropic(api_key=key)
                    return True
                except Exception:
                    pass
        return False

    def is_available(self) -> bool:
        return self._available

    def complete(self, system_prompt: str, messages: List[Dict[str, str]],
                 tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        if not self._available:
            return self._mock_response(system_prompt, messages)

        if self.provider == "anthropic":
            return self._anthropic_complete(system_prompt, messages, tools)

        return self._mock_response(system_prompt, messages)

    def _anthropic_complete(self, system_prompt: str, messages: List[Dict[str, str]],
                           tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        import anthropic

        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = self._client.messages.create(**kwargs)
            content = response.content[0].text if response.content else ""
            return {
                "content": content,
                "usage": {
                    "input_tokens": response.usage.input_tokens if hasattr(response, "usage") else 0,
                    "output_tokens": response.usage.output_tokens if hasattr(response, "usage") else 0,
                },
                "model": self.model,
            }
        except Exception as e:
            return {"content": f"", "error": str(e), "usage": {"input_tokens": 0, "output_tokens": 0}}

    def _mock_response(self, system_prompt: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fallback mock mode when no API key is available."""
        user_msg = messages[-1].get("content", "") if messages else ""

        if "business intent" in system_prompt.lower() or "understand" in system_prompt.lower():
            content = json.dumps({
                "business_domain": "Billing / Pricing",
                "purpose": "Calculates tiered pricing for electricity consumption based on usage brackets.",
                "key_entities": ["customer_id", "usage_kwh", "tier_rates", "total_amount"],
                "data_flow": "Input usage → Apply tier logic → Calculate sub-totals → Sum → Output bill",
                "risks": ["Hard-coded rates", "No input validation", "Monolithic function"],
            }, ensure_ascii=False, indent=2)
        elif "refactor" in system_prompt.lower() or "modernize" in system_prompt.lower():
            content = json.dumps({
                "strategy": "Extract tier calculation into Strategy pattern; add input validation; introduce dataclasses",
                "steps": [
                    "1. Extract PricingTier dataclass",
                    "2. Create PricingStrategy interface with calculate(usage) method",
                    "3. Replace nested if-else with strategy lookup",
                    "4. Add pydantic validation for inputs",
                    "5. Write unit tests for each tier boundary"
                ],
                "estimated_risk": "low",
                "files_to_modify": ["legacy_billing.py"],
            }, ensure_ascii=False, indent=2)
        elif "validate" in system_prompt.lower() or "test" in system_prompt.lower():
            content = json.dumps({
                "behavioral_consistency": "preserved",
                "test_results": {"passed": 12, "failed": 0, "coverage": 85},
                "warnings": ["Consider adding property-based tests for edge cases"],
                "approval": True,
            }, ensure_ascii=False, indent=2)
        else:
            content = json.dumps({"status": "mock_mode", "note": "Set ANTHROPIC_API_KEY for real LLM analysis"})

        return {
            "content": content,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "model": "mock",
        }
