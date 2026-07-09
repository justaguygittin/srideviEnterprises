"""
=========================================================
Project : Sridevi Enterprises
File    : categorize_catalog.py
Purpose : Auto assign departments.

Author  : Srikar
=========================================================
"""

import pandas as pd

from department_keywords import DEPARTMENT_KEYWORDS

from pathlib import Path

BASE_DIR = Path(__file__).parent

INPUT_FILE = BASE_DIR / "Catalog.csv"
OUTPUT_FILE = BASE_DIR / "Catalog_with_departments.csv"


def classify(category_name: str):

    text = str(category_name).lower()

    for department, keywords in DEPARTMENT_KEYWORDS.items():

        for keyword in keywords:

            if keyword in text:
                return department

    return "Miscellaneous"


def main():

    df = pd.read_csv(INPUT_FILE)

    df["Department"] = df["category"].apply(classify)

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("Done!")
    print(f"Output saved as {OUTPUT_FILE}")
    print("\nDepartment Summary")
    print("=" * 35)
    print(df["Department"].value_counts())
    print("\nFinished.")

    misc = df[df["Department"] == "Miscellaneous"]
    if not misc.empty:
        print("\nNeeds Manual Review")
        print("=" * 35)

        for category in sorted(misc["category"].unique()):
            print(category)


if __name__ == "__main__":
    main()
