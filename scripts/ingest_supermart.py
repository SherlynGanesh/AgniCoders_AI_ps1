import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))
from backend.data_ingestion.load_supermart import load_supermart_sales


def ingest_supermart():
    print("==================================================")
    print("Ingesting Supermart Grocery Sales Patterns")
    print("==================================================")
    df = load_supermart_sales()
    if df is not None:
        print(f"Supermart records detected: {len(df)} sales records analyzed.")
    else:
        print("Dataset optional step finished.")


if __name__ == "__main__":
    ingest_supermart()
