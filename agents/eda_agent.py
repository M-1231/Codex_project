from __future__ import annotations
from typing import Any, Dict
import pandas as pd

def _value(value: Any) -> Any:
    if pd.isna(value): return None
    if isinstance(value, pd.Timestamp): return value.isoformat()
    return value.item() if hasattr(value, "item") else value

def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    summary = {c: {k: _value(v) for k, v in values.items()} for c, values in df.describe(include="all").to_dict().items()} if not df.empty else {}
    categories = {c: {str(k): int(v) for k, v in df[c].value_counts(dropna=False).head(5).items()} for c in categorical}
    correlations = {a: {b: _value(v) for b, v in row.items()} for a, row in df[numeric].corr().to_dict().items()} if len(numeric) >= 2 else {}
    trend: Dict[str, Any] = {}
    dates = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    if dates and numeric:
        # Pick the numeric column with the highest coefficient of variation instead of
        # whichever happened to come first in the dataframe - usually the more interesting trend to chart.
        def _cv(col: str) -> float:
            series = df[col].dropna()
            mean = series.mean()
            return abs(series.std() / mean) if mean and not pd.isna(mean) else 0.0
        date_col, metric = dates[0], max(numeric, key=_cv)
        working = df[[date_col, metric]].dropna()
        series = working.groupby(working[date_col].dt.to_period("M"))[metric].mean()
        trend = {"date_column": date_col, "metric": metric, "points": [{"period": str(k), "value": _value(v)} for k, v in series.items()]}
    return {"row_count": int(len(df)), "column_count": int(len(df.columns)), "summary": summary, "top_categories": categories, "correlations": correlations, "trend": trend}
