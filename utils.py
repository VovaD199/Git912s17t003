from __future__ import annotations

from pathlib import Path
from typing import Iterable

import logging
import pandas as pd

MONTHS_UA = {
    1: "Січень",
    2: "Лютий",
    3: "Березень",
    4: "Квітень",
    5: "Травень",
    6: "Червень",
    7: "Липень",
    8: "Серпень",
    9: "Вересень",
    10: "Жовтень",
    11: "Листопад",
    12: "Грудень",
}

DISPLAY_CATEGORIES = [
    "Їжа",
    "Транспорт",
    "Розваги",
    "Житло / Комунальні",
    "Інше",
]


def setup_app_logger(log_path: str | Path = "logs/app.log") -> logging.Logger:
    """Налаштовує логер для Streamlit-застосунку.

    Не додає дублікати handler-ів при повторних rerun у Streamlit.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("budget_app")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


APP_LOGGER = setup_app_logger()


def safe_sum(series: Iterable[float] | pd.Series) -> float:
    """Безпечно підсумовує значення та повертає float."""
    if isinstance(series, pd.Series):
        if series.empty:
            return 0.0
        return float(series.sum())
    return float(sum(series))



def get_month_label(month_number: int) -> str:
    """Повертає назву місяця за номером."""
    return MONTHS_UA.get(month_number, f"Місяць {month_number}")



def build_year_metrics(annual_df: pd.DataFrame) -> dict[str, float]:
    """Обчислює головні річні метрики."""
    if annual_df.empty:
        return {
            "total_income": 0.0,
            "total_expenses": 0.0,
            "balance": 0.0,
        }

    income_df = annual_df[annual_df["record_type"] == "income"]
    expense_df = annual_df[annual_df["record_type"] == "expense"]

    total_income = safe_sum(income_df["amount"])
    total_expenses = safe_sum(expense_df["amount"])

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": total_income - total_expenses,
    }



def build_quarter_summary(annual_df: pd.DataFrame) -> pd.DataFrame:
    """Формує зведення по кварталах."""
    if annual_df.empty:
        return pd.DataFrame(columns=["quarter", "income", "expenses", "balance"])

    income_df = (
        annual_df[annual_df["record_type"] == "income"]
        .groupby("quarter", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "income"})
    )
    expense_df = (
        annual_df[annual_df["record_type"] == "expense"]
        .groupby("quarter", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "expenses"})
    )

    summary = income_df.merge(expense_df, on="quarter", how="outer").fillna(0.0)
    summary["balance"] = summary["income"] - summary["expenses"]

    quarter_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    summary["_sort"] = summary["quarter"].map(quarter_order)
    summary = summary.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    return summary



def build_category_summary(annual_df: pd.DataFrame) -> pd.DataFrame:
    """Формує зведення витрат по категоріях."""
    if annual_df.empty:
        return pd.DataFrame(columns=["category", "amount"])

    expense_df = annual_df[annual_df["record_type"] == "expense"]
    if expense_df.empty:
        return pd.DataFrame(columns=["category", "amount"])

    return (
        expense_df.groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .reset_index(drop=True)
    )



def build_month_summary(annual_df: pd.DataFrame) -> pd.DataFrame:
    """Формує зведення по місяцях."""
    if annual_df.empty:
        return pd.DataFrame(columns=["month_number", "month_name", "income", "expenses", "balance"])

    income_df = (
        annual_df[annual_df["record_type"] == "income"]
        .groupby(["month_number", "month_name"], as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "income"})
    )
    expense_df = (
        annual_df[annual_df["record_type"] == "expense"]
        .groupby(["month_number", "month_name"], as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "expenses"})
    )

    summary = income_df.merge(
        expense_df,
        on=["month_number", "month_name"],
        how="outer",
    ).fillna(0.0)
    summary["balance"] = summary["income"] - summary["expenses"]
    return summary.sort_values("month_number").reset_index(drop=True)
