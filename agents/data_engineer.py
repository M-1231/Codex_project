from __future__ import annotations

from typing import List, Tuple
import pandas as pd


def clean_dataframe(dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Remove exact duplicates, treat missing values, and infer simple types."""
    df = dataframe.copy()
    log: List[str] = []
    before = len(df)
    df = df.drop_duplicates()
    log.append(f"Dropped {before - len(df)} exact duplicate row(s).")
    for column in df.columns:
        missing = int(df[column].isna().sum())
        if not missing:
            continue
        if pd.api.types.is_numeric_dtype(df[column]) and pd.notna(df[column].median()):
            df[column] = df[column].fillna(df[column].median())
            log.append(f"Filled {missing} missing value(s) in '{column}' with its median.")
        elif pd.api.types.is_numeric_dtype(df[column]):
            log.append(f"Flagged {missing} missing value(s) in '{column}' (no numeric median available).")
        else:
            df[column] = df[column].fillna("Unknown")
            log.append(f"Filled {missing} missing value(s) in '{column}' with 'Unknown'.")
    for column in df.columns:
        if not pd.api.types.is_object_dtype(df[column]):
            continue
        values = df[column].dropna().astype(str).str.strip()
        if values.empty:
            continue
        numeric = pd.to_numeric(values.str.replace(",", "", regex=False), errors="coerce")
        if numeric.notna().mean() >= 0.85:
            df[column] = pd.to_numeric(df[column].astype(str).str.replace(",", "", regex=False), errors="coerce")
            log.append(f"Coerced '{column}' to numeric values.")
        elif any(token in column.lower() for token in ("date", "time", "month", "year", "day")):
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().mean() >= 0.70:
                df[column] = parsed
                log.append(f"Coerced '{column}' to dates.")
    return df, log
