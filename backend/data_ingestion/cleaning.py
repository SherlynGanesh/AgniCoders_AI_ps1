import pandas as pd
from typing import Dict, Any


def clean_dataframe(df: pd.DataFrame, column_mappings: Dict[str, str]) -> pd.DataFrame:
    """
    Renames columns to canonical names, strips whitespace, drops invalid rows.
    """
    # Select available columns
    available_cols = {orig: target for orig, target in column_mappings.items() if orig in df.columns}
    sub_df = df[list(available_cols.keys())].rename(columns=available_cols).copy()

    # Strip whitespace from string columns
    for col in sub_df.select_dtypes(include=['object']):
        sub_df[col] = sub_df[col].astype(str).str.strip()
        sub_df[col] = sub_df[col].replace({'nan': None, 'None': None, '': None})

    return sub_df


def inspect_schema(df: pd.DataFrame, source_name: str):
    """Prints a schema preview of the ingested file."""
    print(f"\n================ SCHEMA PREVIEW: {source_name} ================")
    print(f"Total Rows: {len(df)}")
    print(f"Columns Detected ({len(df.columns)}): {list(df.columns)}")
    print("Sample Records:")
    print(df.head(2).to_dict(orient='records'))
    print("================================================================\n")
