from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional

_GROQ_MODEL = "llama-3.3-70b-versatile"


def _fallback_insights(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic backup used if no GROQ_API_KEY is set or the LLM call fails."""
    insights: List[Dict[str, Any]] = []
    for column, values in stats.get("summary", {}).items():
        if len(insights) >= 5:
            break
        if isinstance(values.get("mean"), (int, float)):
            insights.append({
                "claim": f"Average {column} is {values['mean']:.2f}.",
                "evidence_field": f"summary.{column}.mean",
                "evidence_value": values["mean"],
            })
    for column, values in stats.get("top_categories", {}).items():
        if len(insights) >= 5 or not values:
            continue
        category, count = next(iter(values.items()))
        insights.append({
            "claim": f"'{category}' is the leading {column} category with {count} records.",
            "evidence_field": f"top_categories.{column}.{category}",
            "evidence_value": count,
        })
    if len(insights) < 3:
        insights.append({"claim": f"The dataset contains {stats['row_count']} usable records.", "evidence_field": "row_count", "evidence_value": stats["row_count"]})
    if len(insights) < 3:
        insights.append({"claim": f"The dataset contains {stats['column_count']} columns.", "evidence_field": "column_count", "evidence_value": stats["column_count"]})
    return insights[:5]


def _flatten_evidence_paths(stats: Dict[str, Any], prefix: str = "") -> List[str]:
    """List every dot-path in stats whose value is a plain number, so the LLM only cites real fields."""
    paths: List[str] = []
    for key, value in stats.items():
        path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            paths.extend(_flatten_evidence_paths(value, path))
        elif isinstance(value, (int, float)):
            paths.append(path)
    return paths


def generate_insights(stats: Dict[str, Any], business_goal: Optional[str] = None) -> List[Dict[str, Any]]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return _fallback_insights(stats)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        available_paths = _flatten_evidence_paths({
            "summary": stats.get("summary", {}),
            "top_categories": stats.get("top_categories", {}),
            "correlations": stats.get("correlations", {}),
            "row_count": stats.get("row_count"),
            "column_count": stats.get("column_count"),
        })

        prompt = f"""You are a senior business analyst reviewing a dataset's computed statistics.
Business goal: {business_goal or "Find the most decision-useful patterns in this data."}

Computed statistics (JSON, this is ground truth — never invent numbers not in here):
{json.dumps(stats, default=str)[:6000]}

Valid evidence_field paths you may cite (must match exactly, dot-separated):
{json.dumps(available_paths)[:2000]}

Write 5 specific, non-obvious, decision-useful insights relevant to the business goal.
Avoid generic "the average of X is Y" statements unless that average is genuinely notable.
Prefer insights that compare categories, flag outliers, or connect two fields.

Respond with ONLY a JSON object: {{"insights": [{{"claim": "...", "evidence_field": "<exact path from the list above>", "evidence_value": <the exact numeric value at that path>}}]}}"""

        response = client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        parsed = json.loads(response.choices[0].message.content)
        insights = parsed.get("insights", [])
        if not insights:
            return _fallback_insights(stats)
        return insights[:5]
    except Exception:
        # Network issue, bad key, malformed LLM output, etc. Never let the pipeline crash the mission.
        return _fallback_insights(stats)
