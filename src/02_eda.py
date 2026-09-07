"""
SupplyPrescript - Day 2: Exploratory Data Analysis
------------------------------------------------------
Explores delay patterns across shipping mode, region, and category.
Applies the null/row-drop decisions made after Day 1's audit:
  - Drop 'Product Description' (100% null)
  - Drop 'Order Zipcode' (86% null)
  - Drop rows where Delivery Status == 'Shipping canceled'
    (never delivered, not a valid delay case)
  - Drop the handful of rows with null Customer Lname / Customer Zipcode
"""

import pandas as pd

DATA_PATH = "data/DataCoSupplyChainDataset.csv"


def load_and_clean(path: str = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="ISO-8859-1")

    # Drop columns decided on Day 1
    df = df.drop(columns=["Product Description", "Order Zipcode"])

    # Drop cancelled shipments -- never delivered, not a valid delay case
    df = df[df["Delivery Status"] != "Shipping canceled"]

    # Drop the handful of rows with trivial nulls
    df = df.dropna(subset=["Customer Lname", "Customer Zipcode"])

    return df


def shipping_mode_delay_rate(df: pd.DataFrame) -> pd.Series:
    return (
        df.groupby("Shipping Mode")["Late_delivery_risk"]
        .mean()
        .sort_values(ascending=False)
    )


def region_delay_rate(df: pd.DataFrame, top_n: int = 15) -> pd.Series:
    return (
        df.groupby("Order Region")["Late_delivery_risk"]
        .mean()
        .sort_values(ascending=False)
        .head(top_n)
    )


def category_delay_rate(df: pd.DataFrame, top_n: int = 15) -> pd.Series:
    return (
        df.groupby("Category Name")["Late_delivery_risk"]
        .mean()
        .sort_values(ascending=False)
        .head(top_n)
    )


def scheduled_vs_late(df: pd.DataFrame) -> pd.Series:
    # Does a longer scheduled shipping window correlate with less delay?
    return (
        df.groupby("Days for shipment (scheduled)")["Late_delivery_risk"]
        .mean()
    )


def main():
    df = load_and_clean()
    print(f"Cleaned shape: {df.shape}")
    print()

    print("=== Delay rate by Shipping Mode ===")
    print(shipping_mode_delay_rate(df))
    print()

    print("=== Delay rate by Order Region (top 15) ===")
    print(region_delay_rate(df))
    print()

    print("=== Delay rate by Category (top 15) ===")
    print(category_delay_rate(df))
    print()

    print("=== Delay rate by Scheduled Shipping Days ===")
    print(scheduled_vs_late(df))

    # Save cleaned dataset for Day 3 (feature engineering)
    df.to_csv("data/cleaned_day2.csv", index=False)
    print()
    print("Saved cleaned dataset to data/cleaned_day2.csv")


if __name__ == "__main__":
    main()
