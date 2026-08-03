from __future__ import annotations
from typing import Any, Dict
import pandas as pd

def _value(value: Any) -> Any:
    if pd.isna(value): return None
    if isinstance(value, pd.Timestamp): return value.isoformat()
    return value.item() if hasattr(value, "item") else value

def _cv(df: pd.DataFrame, col: str) -> float:
    """Coefficient of variation - used to pick the numeric column with the most interesting spread."""
    series = df[col].dropna()
    mean = series.mean()
    return abs(series.std() / mean) if mean and not pd.isna(mean) else 0.0

def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    summary = {c: {k: _value(v) for k, v in values.items()} for c, values in df.describe(include="all").to_dict().items()} if not df.empty else {}

    # Skip ID-like columns (near-unique per row, e.g. CustomerID) - charting these is meaningless
    # since every value_count would be 1. Also skip if there's effectively one row per category.
    row_count = len(df)
    chartable_categorical = [
        c for c in categorical
        if row_count > 0 and df[c].nunique(dropna=False) <= max(20, row_count * 0.5) and df[c].nunique(dropna=False) < row_count
    ]
    categories = {c: {str(k): int(v) for k, v in df[c].value_counts(dropna=False).head(5).items()} for c in chartable_categorical}

    correlations = {a: {b: _value(v) for b, v in row.items()} for a, row in df[numeric].corr().to_dict().items()} if len(numeric) >= 2 else {}

    trend: Dict[str, Any] = {}
    dates = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    if dates and numeric:
        date_col, metric = dates[0], max(numeric, key=lambda c: _cv(df, c))
        working = df[[date_col, metric]].dropna()
        series = working.groupby(working[date_col].dt.to_period("M"))[metric].mean()
        trend = {"date_column": date_col, "metric": metric, "points": [{"period": str(k), "value": _value(v)} for k, v in series.items()]}

    # Fallback when there's no date column to chart a trend against: bucket the most
    # variable numeric column into a histogram so the "trend" slot is never just blank.
    distribution: Dict[str, Any] = {}
    if not trend and numeric:
        metric = max(numeric, key=lambda c: _cv(df, c))
        series = df[metric].dropna()
        if len(series) and series.nunique() > 1:
            bins = pd.cut(series, bins=min(8, series.nunique()))
            counts = bins.value_counts().sort_index()
            distribution = {"metric": metric, "buckets": [{"range": str(k), "count": int(v)} for k, v in counts.items()]}

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "summary": summary,
        "top_categories": categories,
        "correlations": correlations,
        "trend": trend,
        "distribution": distribution,
    }
