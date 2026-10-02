import os
import glob
import pandas as pd
from typing import List, Dict, Any, Optional
from backend.data_ingestion.cleaning import inspect_schema


def load_supermart_sales(data_dir: str = "data/raw/supermart") -> Optional[pd.DataFrame]:
    """
    Ingests public Supermart Grocery Sales dataset to learn order patterns.
    If not present, warns user with exact placement instructions without halting system.
    """
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not csv_files:
        print(f"[Supermart Ingestion] No CSV found in '{data_dir}'.")
        print("To load Supermart historical grocery sales:")
        print(f"1. Download 'Supermart Grocery Sales - Retail Analytics Dataset' from Kaggle.")
        print(f"2. Place the CSV file into: {os.path.abspath(data_dir)}/")
        print("Proceeding without Supermart historical dataset (synthetic order generation will be used).")
        return None

    file_path = csv_files[0]
    df = pd.read_csv(file_path)
    inspect_schema(df, "Supermart Grocery Sales Pattern")
    return df
