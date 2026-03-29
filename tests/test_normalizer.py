from __future__ import annotations

import io
import json

import pandas as pd
import pytest

from data_normalizer import (
    InvalidBudgetDataError,
    detect_json_format,
    normalize_all_sources,
    normalize_json_payload,
    normalize_quarter_csv,
    quarter_to_month_number,
)


def make_bytes_io(payload: str) -> io.BytesIO:
    return io.BytesIO(payload.encode("utf-8"))



def test_detect_json_format_v1() -> None:
    payload = {
        "quarter": "Q1",
        "months": [],
    }
    assert detect_json_format(payload) == "v1"



def test_detect_json_format_v2() -> None:
    payload = {
        "period": "Q2",
        "data": [],
    }
    assert detect_json_format(payload) == "v2"



def test_detect_json_format_v3() -> None:
    payload = {
        "quarter_id": 3,
        "budget": {},
    }
    assert detect_json_format(payload) == "v3"



def test_quarter_to_month_number() -> None:
    assert quarter_to_month_number(1, 1) == 1
    assert quarter_to_month_number(2, 3) == 6
    assert quarter_to_month_number(4, 2) == 11



def test_normalize_csv_skips_total_rows() -> None:
    df = pd.DataFrame(
        [
            {"Місяць": "Місяць 1", "Категорія": "Їжа", "Сума": 1000},
            {"Місяць": "ВСЬОГО", "Категорія": "ДОХІД", "Сума": 5000},
        ]
    )

    normalized = normalize_quarter_csv(
        df,
        quarter=4,
        year=2025,
        source_file="quarterly_budget.csv",
    )

    assert len(normalized) == 1
    assert normalized.iloc[0]["record_type"] == "expense"
    assert normalized.iloc[0]["category"] == "Їжа"



def test_normalize_json_v1_includes_income_and_expenses() -> None:
    payload = {
        "quarter": "Q1",
        "months": [
            {
                "month": "Місяць 1",
                "income": 10000,
                "expenses": {
                    "Їжа": 3000,
                    "Транспорт": 500,
                },
            }
        ],
    }

    normalized = normalize_json_payload(
        payload,
        year=2025,
        source_file="sample_q1.json",
    )

    assert len(normalized) == 3
    assert set(normalized["record_type"].tolist()) == {"income", "expense"}



def test_september_error_is_reported_in_issues() -> None:
    bad_payload = {
        "quarter_id": 3,
        "budget": {
            "month_1": {
                "income_total": 10000,
                "expense_items": {"food": 1000, "transport": 100},
            },
            "month_2": {
                "income_total": 11000,
                "expense_items": {"food": 1200, "transport": 200},
            },
            "month_3": {
                "income_total": 12000,
                "expense_items": {"food": 1300, "transport": "unknown"},
            },
        },
    }

    json_file = make_bytes_io(json.dumps(bad_payload, ensure_ascii=False))
    csv_df = pd.DataFrame(
        [{"Місяць": "Місяць 1", "Категорія": "Їжа", "Сума": 1000}]
    )
    csv_file = make_bytes_io(csv_df.to_csv(index=False))

    annual_df, issues = normalize_all_sources(
        json_sources=[(json_file, "bad_q3.json")],
        csv_source=(csv_file, "quarterly_budget.csv"),
        year=2025,
    )

    assert not annual_df.empty
    assert issues
    assert any("вереснев" in issue.message.lower() for issue in issues)



def test_unknown_category_raises_error() -> None:
    payload = {
        "quarter": "Q1",
        "months": [
            {
                "month": "Місяць 1",
                "income": 10000,
                "expenses": {
                    "Подорожі": 3000,
                },
            }
        ],
    }

    with pytest.raises(InvalidBudgetDataError):
        normalize_json_payload(payload, year=2025, source_file="bad_categories.json")
