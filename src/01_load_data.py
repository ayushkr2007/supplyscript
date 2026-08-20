"""
SupplyPrescript - Day 1: Data Loading & Schema Audit
------------------------------------------------------
Loads the DataCo Smart Supply Chain dataset, checks schema, nulls,
and target distribution. This is the foundation for the delay
prediction model (Week 1 of SupplyPrescript).
"""

import pandas as pd

DATA_PATH = "data/DataCoSupplyChainDataset.csv"

def load_raw_data(path: str = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="ISO-8859-1")
    return df


def audit_nulls(df: pd.DataFrame) -> pd.Series:
    nulls = df.isnull().sum()
    return nulls[nulls > 0].sort_values(ascending=False)


def audit_target(df: pd.DataFrame) -> None:
    print("Late_delivery_risk distribution:")
    print(df["Late_delivery_risk"].value_counts(normalize=True))
    print()
    print("Delivery Status breakdown:")
    print(df["Delivery Status"].value_counts())


def main():
    df = load_raw_data()

    print(f"Shape: {df.shape}")
    print()

    print("=== Null audit ===")
    print(audit_nulls(df))
    print()

    print("=== Target audit ===")
    audit_target(df)
    print()

    print("=== Dtype summary ===")
    print(df.dtypes.value_counts())


if __name__ == "__main__":
    main()
