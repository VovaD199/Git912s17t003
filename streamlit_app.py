from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from data_normalizer import NormalizationIssue, normalize_all_sources
from utils import (
    APP_LOGGER,
    build_category_summary,
    build_month_summary,
    build_quarter_summary,
    build_year_metrics,
)

st.set_page_config(
    page_title="Калькулятор особистого бюджету — рівень 3",
    page_icon="📈",
    layout="wide",
)


DEFAULT_YEAR = 2025
EXPECTED_JSON_COUNT = 3



def init_session_state() -> None:
    if "annual_df" not in st.session_state:
        st.session_state.annual_df = pd.DataFrame()
    if "issues" not in st.session_state:
        st.session_state.issues = []
    if "processing_done" not in st.session_state:
        st.session_state.processing_done = False



def render_home_page() -> None:
    st.title("💰 Калькулятор особистого бюджету — рівень 3")
    st.subheader("Річний звіт з нормалізацією даних")
    st.write(
        "Цей застосунок об'єднує дані з кількох джерел: 3 JSON-файлів "
        "попередніх кварталів та 1 CSV-файлу останнього кварталу. "
        "Перед побудовою звіту дані нормалізуються до єдиної структури."
    )

    st.markdown("### Що вміє застосунок")
    st.write("- завантажувати 3 JSON-файли та 1 CSV-файл;")
    st.write("- перевіряти структуру джерел;")
    st.write("- нормалізувати дані до єдиного формату;")
    st.write("- будувати річний, квартальний і місячний звіти;")
    st.write("- показувати проблеми обробки та зберігати лог-файл.")

    st.info(
        "Порада: спочатку відкрийте розділ 'Завантаження та обробка даних', "
        "завантажте всі 4 файли й лише після цього переходьте до аналітичних сторінок."
    )



def render_upload_page() -> None:
    st.title("📂 Завантаження та обробка даних")

    year = st.number_input(
        "Рік звіту",
        min_value=2000,
        max_value=2100,
        value=DEFAULT_YEAR,
        step=1,
    )

    json_files = st.file_uploader(
        "Завантажте 3 JSON-файли для Q1, Q2 та Q3",
        type=["json"],
        accept_multiple_files=True,
    )
    csv_file = st.file_uploader(
        "Завантажте CSV-файл для Q4 (експорт із попередньої задачі)",
        type=["csv"],
        accept_multiple_files=False,
    )

    if st.button("Обробити дані"):
        APP_LOGGER.info("Користувач запустив обробку даних")

        if len(json_files) != EXPECTED_JSON_COUNT:
            st.error("Потрібно завантажити рівно 3 JSON-файли.")
            APP_LOGGER.warning("Неправильна кількість JSON-файлів: %s", len(json_files))
            return

        if csv_file is None:
            st.error("Потрібно завантажити CSV-файл для останнього кварталу.")
            APP_LOGGER.warning("CSV-файл не завантажено")
            return

        try:
            annual_df, issues = normalize_all_sources(
                json_sources=[(uploaded_file, uploaded_file.name) for uploaded_file in json_files],
                csv_source=(csv_file, csv_file.name),
                year=int(year),
                csv_quarter=4,
            )
        except Exception as exc:  # noqa: BLE001
            APP_LOGGER.exception("Критична помилка під час обробки даних")
            st.error(f"Не вдалося обробити дані: {exc}")
            return

        st.session_state.annual_df = annual_df
        st.session_state.issues = issues
        st.session_state.processing_done = True

        if annual_df.empty:
            st.warning("Обробку завершено, але фінальний набір даних порожній.")
        else:
            st.success("Дані успішно оброблено.")
            st.dataframe(annual_df, width="stretch")

        render_issues_block(issues)

        log_path = Path("logs/app.log")
        if log_path.exists():
            with log_path.open("rb") as file_obj:
                st.download_button(
                    label="📥 Завантажити лог-файл",
                    data=file_obj.read(),
                    file_name="app.log",
                    mime="text/plain",
                )



def render_issues_block(issues: list[NormalizationIssue]) -> None:
    st.markdown("### Повідомлення про обробку")

    if not issues:
        st.success("Критичних проблем під час нормалізації не зафіксовано.")
        return

    for issue in issues:
        message = f"**{issue.source_file}**: {issue.message}"
        if issue.level.lower() == "error":
            st.error(message)
        else:
            st.warning(message)



def ensure_data_ready() -> bool:
    if st.session_state.annual_df.empty:
        st.warning("Спочатку завантажте та обробіть дані у відповідному розділі.")
        return False
    return True



def render_year_report() -> None:
    st.title("📊 Річний звіт")
    if not ensure_data_ready():
        return

    annual_df = st.session_state.annual_df
    metrics = build_year_metrics(annual_df)
    category_summary = build_category_summary(annual_df)
    month_summary = build_month_summary(annual_df)
    quarter_summary = build_quarter_summary(annual_df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Загальний дохід за рік", f"{metrics['total_income']:.2f} грн")
    col2.metric("Загальні витрати", f"{metrics['total_expenses']:.2f} грн")
    col3.metric("Залишок", f"{metrics['balance']:.2f} грн")

    st.markdown("### Розподіл витрат по категоріях")
    st.dataframe(category_summary, width="stretch")
    if not category_summary.empty:
        st.bar_chart(category_summary.set_index("category"), width="stretch")

    st.markdown("### Порівняння кварталів")
    st.dataframe(quarter_summary, width="stretch")
    if not quarter_summary.empty:
        chart_df = quarter_summary.set_index("quarter")[["income", "expenses", "balance"]]
        st.bar_chart(chart_df, width="stretch")

    st.markdown("### Зведення по місяцях")
    st.dataframe(month_summary, width="stretch")

    with st.expander("Показати повний нормалізований набір"):
        st.dataframe(annual_df, width="stretch")

    render_issues_block(st.session_state.issues)



def render_quarter_report() -> None:
    st.title("🗓️ Звіт по кварталах")
    if not ensure_data_ready():
        return

    annual_df = st.session_state.annual_df
    quarter_summary = build_quarter_summary(annual_df)

    st.dataframe(quarter_summary, width="stretch")

    if quarter_summary.empty:
        st.info("Немає даних для квартального аналізу.")
        return

    selected_quarter = st.selectbox(
        "Оберіть квартал",
        options=quarter_summary["quarter"].tolist(),
    )

    filtered_df = annual_df[annual_df["quarter"] == selected_quarter].copy()
    expense_df = filtered_df[filtered_df["record_type"] == "expense"]

    st.markdown(f"### Деталізація для {selected_quarter}")
    quarter_category_summary = build_category_summary(filtered_df)
    st.dataframe(quarter_category_summary, width="stretch")

    if not quarter_category_summary.empty:
        st.bar_chart(quarter_category_summary.set_index("category"), width="stretch")

    st.markdown("### Детальні записи кварталу")
    st.dataframe(filtered_df, width="stretch")

    if expense_df.empty:
        st.warning("Для обраного кварталу немає витратних записів.")



def render_month_report() -> None:
    st.title("📅 Звіт за окремий місяць")
    if not ensure_data_ready():
        return

    annual_df = st.session_state.annual_df
    month_options = (
        annual_df[["month_number", "month_name"]]
        .drop_duplicates()
        .sort_values("month_number")
    )

    labels = [
        f"{row.month_number:02d} — {row.month_name}"
        for row in month_options.itertuples(index=False)
    ]
    selected_label = st.selectbox("Оберіть місяць", options=labels)
    selected_month_number = int(selected_label.split(" — ")[0])

    month_df = annual_df[annual_df["month_number"] == selected_month_number].copy()
    income_total = float(month_df.loc[month_df["record_type"] == "income", "amount"].sum())
    expenses_total = float(month_df.loc[month_df["record_type"] == "expense", "amount"].sum())
    balance = income_total - expenses_total

    col1, col2, col3 = st.columns(3)
    col1.metric("Дохід", f"{income_total:.2f} грн")
    col2.metric("Витрати", f"{expenses_total:.2f} грн")
    col3.metric("Баланс", f"{balance:.2f} грн")

    expense_df = month_df[month_df["record_type"] == "expense"]
    if expense_df.empty:
        st.warning("Для обраного місяця немає витратних записів.")
        return

    category_summary = (
        expense_df.groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .reset_index(drop=True)
    )

    st.markdown("### Витрати по категоріях")
    st.dataframe(category_summary, width="stretch")
    st.bar_chart(category_summary.set_index("category"), width="stretch")

    st.markdown("### Детальні записи місяця")
    st.dataframe(month_df, width="stretch")



def main() -> None:
    init_session_state()
    APP_LOGGER.info("Запуск Streamlit-застосунку рівня 3")

    page = st.sidebar.radio(
        "Навігація",
        [
            "Головна",
            "Завантаження та обробка даних",
            "Річний звіт",
            "Звіт по кварталах",
            "Звіт за окремий місяць",
        ],
    )

    st.sidebar.markdown("---")
    if st.session_state.processing_done:
        st.sidebar.success("Дані оброблено")
        st.sidebar.write(f"Рядків у наборі: {len(st.session_state.annual_df)}")
        st.sidebar.write(f"Проблем зафіксовано: {len(st.session_state.issues)}")
    else:
        st.sidebar.info("Дані ще не оброблялись")

    if page == "Головна":
        render_home_page()
    elif page == "Завантаження та обробка даних":
        render_upload_page()
    elif page == "Річний звіт":
        render_year_report()
    elif page == "Звіт по кварталах":
        render_quarter_report()
    elif page == "Звіт за окремий місяць":
        render_month_report()


if __name__ == "__main__":
    main()
