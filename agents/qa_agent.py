from math import isclose
from typing import Any, Dict, List

def verify_insights(stats: Dict[str, Any], insights: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    approved, rejected = [], []
    for insight in insights:
        value: Any = stats; found = True
        for part in insight.get("evidence_field", "").split("."):
            if not isinstance(value, dict) or part not in value:
                found = False; break
            value = value[part]
        expected = insight.get("evidence_value")
        matches = found and (isclose(value, expected, rel_tol=1e-6, abs_tol=1e-9) if isinstance(value, (int, float)) and isinstance(expected, (int, float)) else value == expected)
        if matches: approved.append(insight)
        else: rejected.append({"insight": insight, "reason": "Evidence field was not found in analysis stats." if not found else "Evidence value does not match analysis stats."})
    return {"approved": approved, "rejected": rejected}
