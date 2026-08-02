from typing import Any, Dict, List

def generate_insights(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    for column, values in stats.get("summary", {}).items():
        if len(insights) >= 5: break
        if isinstance(values.get("mean"), (int, float)):
            insights.append({"claim": f"Average {column} is {values['mean']:.2f}.", "evidence_field": f"summary.{column}.mean", "evidence_value": values["mean"]})
    for column, values in stats.get("top_categories", {}).items():
        if len(insights) >= 5 or not values: continue
        category, count = next(iter(values.items()))
        insights.append({"claim": f"'{category}' is the leading {column} category with {count} records.", "evidence_field": f"top_categories.{column}.{category}", "evidence_value": count})
    if len(insights) < 3:
        insights.append({"claim": f"The dataset contains {stats['row_count']} usable records.", "evidence_field": "row_count", "evidence_value": stats["row_count"]})
    if len(insights) < 3:
        insights.append({"claim": f"The dataset contains {stats['column_count']} columns.", "evidence_field": "column_count", "evidence_value": stats["column_count"]})
    return insights[:5]
