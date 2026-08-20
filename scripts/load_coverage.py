"""Clean coverage CSVs and load them into a SQLite database."""

from pathlib import Path
import sqlite3

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATABASE_PATH = ROOT / "coverage.db"


def _clean_text_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        frame[column] = frame[column].astype("string").str.strip()
    return frame


def _require_non_null(frame: pd.DataFrame, table_name: str) -> None:
    null_counts = frame.isna().sum()
    invalid = null_counts[null_counts > 0]
    if not invalid.empty:
        details = ", ".join(f"{column}={count}" for column, count in invalid.items())
        raise ValueError(f"{table_name} contains null values: {details}")


def clean_plans(path: Path = DATA_DIR / "plans.csv") -> pd.DataFrame:
    plans = pd.read_csv(path, dtype={"plan_id": "string"})
    plans = _clean_text_columns(
        plans,
        ["plan_id", "plan_name", "coverage_type", "network_tier"],
    )
    for column in ["monthly_premium", "annual_deductible", "copay_pct"]:
        plans[column] = pd.to_numeric(plans[column], errors="raise")
    plans = plans.drop_duplicates().reset_index(drop=True)
    _require_non_null(plans, "plans")
    if plans["plan_id"].duplicated().any():
        raise ValueError("plans.plan_id must be unique")
    return plans


def clean_claims(path: Path = DATA_DIR / "claims.csv") -> pd.DataFrame:
    claims = pd.read_csv(
        path,
        dtype={"claim_id": "string", "member_id": "string", "plan_id": "string"},
    )
    claims = _clean_text_columns(
        claims,
        ["claim_id", "member_id", "plan_id", "procedure", "status"],
    )
    claims["claim_amount"] = pd.to_numeric(claims["claim_amount"], errors="raise")
    claims["date_filed"] = pd.to_datetime(
        claims["date_filed"], errors="raise", format="%Y-%m-%d"
    ).dt.strftime("%Y-%m-%d")
    claims = claims.drop_duplicates().reset_index(drop=True)
    _require_non_null(claims, "claims")
    if claims["claim_id"].duplicated().any():
        raise ValueError("claims.claim_id must be unique")
    return claims


def load_database(
    plans: pd.DataFrame,
    claims: pd.DataFrame,
    database_path: Path = DATABASE_PATH,
) -> None:
    unknown_plan_ids = sorted(set(claims["plan_id"]) - set(plans["plan_id"]))
    if unknown_plan_ids:
        raise ValueError(f"claims reference unknown plan IDs: {unknown_plan_ids}")

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        plans.to_sql("plans", connection, if_exists="replace", index=False)
        claims.to_sql("claims", connection, if_exists="replace", index=False)
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_plans_plan_id ON plans(plan_id)"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_claims_claim_id ON claims(claim_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_claims_member_id ON claims(member_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_claims_plan_id ON claims(plan_id)"
        )


def main() -> None:
    plans = clean_plans()
    claims = clean_claims()
    load_database(plans, claims)
    print(f"Loaded {len(plans)} plans and {len(claims)} claims into {DATABASE_PATH}")


if __name__ == "__main__":
    main()