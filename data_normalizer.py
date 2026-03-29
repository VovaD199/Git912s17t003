from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd
from pandas.errors import ParserError


# ------------------------------------------------------------
# Налаштування констант
# ------------------------------------------------------------

TARGET_CATEGORIES = {
    "food": "Їжа",
    "їжа": "Їжа",
    "transport": "Транспорт",
    "транспорт": "Транспорт",
    "entertainment": "Розваги",
    "розваги": "Розваги",
    "housing": "Житло / Комунальні",
    "housing / utilities": "Житло / Комунальні",
    "житло / комунальні": "Житло / Комунальні",
    "other": "Інше",
    "інше": "Інше",
}

MONTH_NAME_BY_NUMBER = {
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

MONTH_INDEX_FROM_LABEL = {
    "Місяць 1": 1,
    "Місяць 2": 2,
    "Місяць 3": 3,
}


# ------------------------------------------------------------
# Власні винятки
# ------------------------------------------------------------


class NormalizationError(Exception):
    """Базова помилка нормалізації."""


class InvalidBudgetDataError(NormalizationError):
    """Помилка структури або значень бюджету."""


# ------------------------------------------------------------
# Допоміжні структури
# ------------------------------------------------------------


@dataclass
class NormalizationIssue:
    level: str
    source_file: str
    message: str
    record_hint: str | None = None


# ------------------------------------------------------------
# Логування
# ------------------------------------------------------------


def setup_logger(log_path: str | Path = "logs/app.log") -> logging.Logger:
    """Створює та повертає логер для обробки даних."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("budget_normalizer")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


LOGGER = setup_logger()


# ------------------------------------------------------------
# Базові утиліти
# ------------------------------------------------------------


def normalize_category(category: str) -> str:
    """Повертає уніфіковану назву категорії."""
    key = category.strip().lower()
    if key not in TARGET_CATEGORIES:
        raise InvalidBudgetDataError(f"Невідома категорія: {category}")
    return TARGET_CATEGORIES[key]



def quarter_to_month_number(quarter: int, month_index_in_quarter: int) -> int:
    """Обчислює номер місяця в році за кварталом і позицією в кварталі."""
    if quarter not in {1, 2, 3, 4}:
        raise InvalidBudgetDataError(f"Неприпустимий номер кварталу: {quarter}")
    if month_index_in_quarter not in {1, 2, 3}:
        raise InvalidBudgetDataError(
            f"Неприпустимий номер місяця в кварталі: {month_index_in_quarter}"
        )
    return (quarter - 1) * 3 + month_index_in_quarter



def build_record(
    *,
    year: int,
    quarter: int,
    month_index_in_quarter: int,
    category: str,
    amount: float,
    record_type: str,
    source_file: str,
    source_format: str,
) -> dict[str, Any]:
    """Формує запис у єдиному цільовому форматі."""
    month_number = quarter_to_month_number(quarter, month_index_in_quarter)
    month_name = MONTH_NAME_BY_NUMBER[month_number]

    return {
        "year": year,
        "quarter": f"Q{quarter}",
        "month_index_in_quarter": month_index_in_quarter,
        "month_number": month_number,
        "month_name": month_name,
        "category": category,
        "amount": float(amount),
        "record_type": record_type,
        "source_file": source_file,
        "source_format": source_format,
    }



def validate_amount(amount: Any, *, source_file: str, record_hint: str = "") -> float:
    """Перевіряє, що сума є числом та не є від'ємною."""
    try:
        value = float(amount)
    except (TypeError, ValueError) as exc:
        LOGGER.error(
            "Некоректне значення суми у %s | %s | value=%r",
            source_file,
            record_hint,
            amount,
        )
        raise InvalidBudgetDataError(f"Некоректне значення суми: {amount!r}") from exc

    if value < 0:
        LOGGER.error(
            "Від'ємне значення суми у %s | %s | value=%r",
            source_file,
            record_hint,
            amount,
        )
        raise InvalidBudgetDataError(f"Сума не може бути від'ємною: {value}")

    return value



def validate_september_record(month_number: int, payload: Any, *, source_file: str) -> None:
    """Навчальна перевірка: вересневі дані мають бути перевірені окремо.

    TODO для студентів:
    - розширити правила перевірки;
    - або зупиняти обробку,
    - або пропускати лише проблемний запис з логуванням.
    """
    if month_number != 9:
        return

    serialized = json.dumps(payload, ensure_ascii=False)
    if "unknown" in serialized.lower() or '"вересень": null' in serialized.lower():
        LOGGER.warning(
            "Виявлено підозрілий запис у вересневих даних: %s | payload=%s",
            source_file,
            serialized,
        )
        raise InvalidBudgetDataError(
            "У вересневих даних знайдено спеціально закладену помилку"
        )


# ------------------------------------------------------------
# Читання файлів
# ------------------------------------------------------------


def read_uploaded_json(file_obj: BinaryIO | BytesIO, source_name: str) -> dict[str, Any]:
    """Зчитує JSON із завантаженого файлу Streamlit."""
    LOGGER.info("Завантаження JSON-файлу: %s", source_name)
    try:
        raw_bytes = file_obj.read()
        text = raw_bytes.decode("utf-8")
        return json.loads(text)
    except UnicodeDecodeError:
        LOGGER.exception("Помилка кодування під час читання JSON: %s", source_name)
        raise
    except json.JSONDecodeError:
        LOGGER.exception("Пошкоджений JSON-файл: %s", source_name)
        raise



def read_uploaded_csv(file_obj: BinaryIO | BytesIO, source_name: str) -> pd.DataFrame:
    """Зчитує CSV із завантаженого файлу Streamlit."""
    LOGGER.info("Завантаження CSV-файлу: %s", source_name)
    try:
        raw_bytes = file_obj.read()
        text = raw_bytes.decode("utf-8-sig")
        return pd.read_csv(StringIO(text))
    except UnicodeDecodeError:
        LOGGER.exception("Помилка кодування під час читання CSV: %s", source_name)
        raise
    except ParserError:
        LOGGER.exception("CSV не вдалося розпарсити: %s", source_name)
        raise


# ------------------------------------------------------------
# Нормалізація CSV з попередньої задачі
# ------------------------------------------------------------


def normalize_quarter_csv(
    df: pd.DataFrame,
    *,
    quarter: int,
    year: int,
    source_file: str,
) -> pd.DataFrame:
    """Нормалізує CSV четвертого кварталу з попередньої задачі.

    Очікувано, CSV має колонки:
    - Місяць
    - Категорія
    - Сума

    У файлі також можуть бути службові рядки типу:
    - ВСЬОГО / ДОХІД
    - ВСЬОГО / ВИТРАТИ
    - ВСЬОГО / БАЛАНС
    """
    LOGGER.info("Початок нормалізації CSV: %s", source_file)

    required_columns = {"Місяць", "Категорія", "Сума"}
    if not required_columns.issubset(df.columns):
        raise InvalidBudgetDataError(
            f"CSV не містить обов'язкових колонок: {required_columns}"
        )

    records: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        month_label = str(row["Місяць"]).strip()
        category = str(row["Категорія"]).strip()
        amount = row["Сума"]

        if month_label == "ВСЬОГО":
            # TODO для студентів:
            # за бажанням можна зберегти ці підсумкові рядки окремо
            LOGGER.info("Пропущено службовий рядок CSV: %s | %s", month_label, category)
            continue

        if month_label not in MONTH_INDEX_FROM_LABEL:
            LOGGER.warning(
                "Невідома назва місяця у CSV: %s | file=%s",
                month_label,
                source_file,
            )
            continue

        month_index = MONTH_INDEX_FROM_LABEL[month_label]
        validated_amount = validate_amount(
            amount,
            source_file=source_file,
            record_hint=f"{month_label} / {category}",
        )

        normalized_category = normalize_category(category)
        records.append(
            build_record(
                year=year,
                quarter=quarter,
                month_index_in_quarter=month_index,
                category=normalized_category,
                amount=validated_amount,
                record_type="expense",
                source_file=source_file,
                source_format="csv",
            )
        )

    normalized_df = pd.DataFrame(records)
    LOGGER.info(
        "CSV нормалізовано успішно: %s | records=%s",
        source_file,
        len(normalized_df),
    )
    return normalized_df


# ------------------------------------------------------------
# Нормалізація JSON: формат 1
# ------------------------------------------------------------


def normalize_json_format_v1(
    data: dict[str, Any],
    *,
    year: int,
    source_file: str,
) -> pd.DataFrame:
    """Підтримує формат:

    {
      "quarter": "Q1",
      "months": [
        {
          "month": "Місяць 1",
          "income": 12000,
          "expenses": {"Їжа": 3000, ...}
        }
      ]
    }
    """
    LOGGER.info("Початок нормалізації JSON V1: %s", source_file)

    if "quarter" not in data or "months" not in data:
        raise InvalidBudgetDataError("JSON V1 не містить ключів 'quarter' або 'months'")

    quarter = int(str(data["quarter"]).replace("Q", ""))
    records: list[dict[str, Any]] = []

    for month_payload in data["months"]:
        month_label = month_payload["month"]
        month_index = MONTH_INDEX_FROM_LABEL[month_label]

        income = validate_amount(
            month_payload["income"],
            source_file=source_file,
            record_hint=f"{month_label} / income",
        )
        records.append(
            build_record(
                year=year,
                quarter=quarter,
                month_index_in_quarter=month_index,
                category="Дохід",
                amount=income,
                record_type="income",
                source_file=source_file,
                source_format="json",
            )
        )

        expenses = month_payload["expenses"]
        for category, amount in expenses.items():
            validated_amount = validate_amount(
                amount,
                source_file=source_file,
                record_hint=f"{month_label} / {category}",
            )
            records.append(
                build_record(
                    year=year,
                    quarter=quarter,
                    month_index_in_quarter=month_index,
                    category=normalize_category(category),
                    amount=validated_amount,
                    record_type="expense",
                    source_file=source_file,
                    source_format="json",
                )
            )

    return pd.DataFrame(records)


# ------------------------------------------------------------
# Нормалізація JSON: формат 2
# ------------------------------------------------------------


def normalize_json_format_v2(
    data: dict[str, Any],
    *,
    year: int,
    source_file: str,
) -> pd.DataFrame:
    """Підтримує формат:

    {
      "period": "Q2",
      "data": [
        {
          "name": "Місяць 1",
          "salary": 14000,
          "costs": [
            {"category": "Їжа", "value": 3200}
          ]
        }
      ]
    }
    """
    LOGGER.info("Початок нормалізації JSON V2: %s", source_file)

    if "period" not in data or "data" not in data:
        raise InvalidBudgetDataError("JSON V2 не містить ключів 'period' або 'data'")

    quarter = int(str(data["period"]).replace("Q", ""))
    records: list[dict[str, Any]] = []

    for month_payload in data["data"]:
        month_label = month_payload["name"]
        month_index = MONTH_INDEX_FROM_LABEL[month_label]

        income = validate_amount(
            month_payload["salary"],
            source_file=source_file,
            record_hint=f"{month_label} / salary",
        )
        records.append(
            build_record(
                year=year,
                quarter=quarter,
                month_index_in_quarter=month_index,
                category="Дохід",
                amount=income,
                record_type="income",
                source_file=source_file,
                source_format="json",
            )
        )

        for item in month_payload["costs"]:
            category = item["category"]
            amount = item["value"]
            validated_amount = validate_amount(
                amount,
                source_file=source_file,
                record_hint=f"{month_label} / {category}",
            )
            records.append(
                build_record(
                    year=year,
                    quarter=quarter,
                    month_index_in_quarter=month_index,
                    category=normalize_category(category),
                    amount=validated_amount,
                    record_type="expense",
                    source_file=source_file,
                    source_format="json",
                )
            )

    return pd.DataFrame(records)


# ------------------------------------------------------------
# Нормалізація JSON: формат 3
# ------------------------------------------------------------


def normalize_json_format_v3(
    data: dict[str, Any],
    *,
    year: int,
    source_file: str,
) -> pd.DataFrame:
    """Підтримує формат:

    {
      "quarter_id": 3,
      "budget": {
        "month_1": {
          "income_total": 15000,
          "expense_items": {"food": 4100, ...}
        }
      }
    }

    У цьому форматі в одному з прикладів навмисно є помилка у вересневих даних.
    """
    LOGGER.info("Початок нормалізації JSON V3: %s", source_file)

    if "quarter_id" not in data or "budget" not in data:
        raise InvalidBudgetDataError("JSON V3 не містить ключів 'quarter_id' або 'budget'")

    quarter = int(data["quarter_id"])
    records: list[dict[str, Any]] = []

    for month_key, month_payload in data["budget"].items():
        try:
            month_index = int(str(month_key).split("_")[-1])
        except (TypeError, ValueError) as exc:
            raise InvalidBudgetDataError(
                f"Неможливо визначити номер місяця з ключа: {month_key}"
            ) from exc

        month_number = quarter_to_month_number(quarter, month_index)
        validate_september_record(month_number, month_payload, source_file=source_file)

        income = validate_amount(
            month_payload["income_total"],
            source_file=source_file,
            record_hint=f"{month_key} / income_total",
        )
        records.append(
            build_record(
                year=year,
                quarter=quarter,
                month_index_in_quarter=month_index,
                category="Дохід",
                amount=income,
                record_type="income",
                source_file=source_file,
                source_format="json",
            )
        )

        for category, amount in month_payload["expense_items"].items():
            validated_amount = validate_amount(
                amount,
                source_file=source_file,
                record_hint=f"{month_key} / {category}",
            )
            records.append(
                build_record(
                    year=year,
                    quarter=quarter,
                    month_index_in_quarter=month_index,
                    category=normalize_category(category),
                    amount=validated_amount,
                    record_type="expense",
                    source_file=source_file,
                    source_format="json",
                )
            )

    return pd.DataFrame(records)


# ------------------------------------------------------------
# Автовизначення JSON-формату
# ------------------------------------------------------------


def detect_json_format(data: dict[str, Any]) -> str:
    """Визначає формат JSON за ключами верхнього рівня."""
    if {"quarter", "months"}.issubset(data.keys()):
        return "v1"
    if {"period", "data"}.issubset(data.keys()):
        return "v2"
    if {"quarter_id", "budget"}.issubset(data.keys()):
        return "v3"
    raise InvalidBudgetDataError("Не вдалося визначити формат JSON")



def normalize_json_payload(
    data: dict[str, Any],
    *,
    year: int,
    source_file: str,
) -> pd.DataFrame:
    """Нормалізує JSON після автовизначення формату."""
    detected_format = detect_json_format(data)
    LOGGER.info("Визначено формат JSON: %s | file=%s", detected_format, source_file)

    if detected_format == "v1":
        return normalize_json_format_v1(data, year=year, source_file=source_file)
    if detected_format == "v2":
        return normalize_json_format_v2(data, year=year, source_file=source_file)
    if detected_format == "v3":
        return normalize_json_format_v3(data, year=year, source_file=source_file)

    raise InvalidBudgetDataError(f"Непідтримуваний формат JSON: {detected_format}")


# ------------------------------------------------------------
# Об'єднання даних
# ------------------------------------------------------------


def combine_normalized_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Об'єднує всі нормалізовані DataFrame в один річний набір."""
    non_empty_frames = [frame for frame in frames if not frame.empty]
    if not non_empty_frames:
        return pd.DataFrame(
            columns=[
                "year",
                "quarter",
                "month_index_in_quarter",
                "month_number",
                "month_name",
                "category",
                "amount",
                "record_type",
                "source_file",
                "source_format",
            ]
        )

    annual_df = pd.concat(non_empty_frames, ignore_index=True)
    annual_df = annual_df.sort_values(
        by=["month_number", "record_type", "category"]
    ).reset_index(drop=True)

    LOGGER.info("Фінальний річний DataFrame сформовано | rows=%s", len(annual_df))
    return annual_df


# ------------------------------------------------------------
# Узагальнена точка входу для Streamlit
# ------------------------------------------------------------


def normalize_all_sources(
    *,
    json_sources: list[tuple[BinaryIO | BytesIO, str]],
    csv_source: tuple[BinaryIO | BytesIO, str] | None,
    year: int,
    csv_quarter: int = 4,
) -> tuple[pd.DataFrame, list[NormalizationIssue]]:
    """Нормалізує всі джерела та повертає фінальний DataFrame і список проблем.

    Параметри:
    - json_sources: список пар (file_obj, source_name)
    - csv_source: пара (file_obj, source_name) або None
    - year: рік звіту
    - csv_quarter: номер кварталу для CSV із попередньої задачі

    TODO для студентів:
    - розширити збір issues,
    - додати точніші правила валідації,
    - інтегрувати з Streamlit-повідомленнями.
    """
    frames: list[pd.DataFrame] = []
    issues: list[NormalizationIssue] = []

    for file_obj, source_name in json_sources:
        try:
            payload = read_uploaded_json(file_obj, source_name)
            normalized = normalize_json_payload(
                payload,
                year=year,
                source_file=source_name,
            )
            frames.append(normalized)
        except Exception as exc:  # noqa: BLE001 - навмисно для навчального прикладу
            LOGGER.exception("Не вдалося обробити JSON: %s", source_name)
            issues.append(
                NormalizationIssue(
                    level="error",
                    source_file=source_name,
                    message=str(exc),
                )
            )

    if csv_source is not None:
        file_obj, source_name = csv_source
        try:
            csv_df = read_uploaded_csv(file_obj, source_name)
            normalized_csv = normalize_quarter_csv(
                csv_df,
                quarter=csv_quarter,
                year=year,
                source_file=source_name,
            )
            frames.append(normalized_csv)
        except Exception as exc:  # noqa: BLE001 - навмисно для навчального прикладу
            LOGGER.exception("Не вдалося обробити CSV: %s", source_name)
            issues.append(
                NormalizationIssue(
                    level="error",
                    source_file=source_name,
                    message=str(exc),
                )
            )

    annual_df = combine_normalized_frames(frames)
    return annual_df, issues


if __name__ == "__main__":
    print(
        "Це каркас модуля data_normalizer.py. "
        "Імпортуйте його у streamlit_app.py та доповнюйте логіку під вимоги задачі."
    )
