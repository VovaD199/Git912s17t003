# Personal Budget Calculator - Level 3: Annual Report with Data Normalization

## Practical work

In this task, you continue the development of a series of learning projects:

- **level 1** — monthly budget;
- **level 2** — quarterly report with CSV export;
- **level 3** — annual analytical application with processing of heterogeneous data sources.

This task is close to a real working situation: data comes from different versions of the system, in different formats, with potential errors, and needs to be brought into a single structure before building a report.

---

## Purpose of work

Learn:

- work with multiple data sources simultaneously;
- check the structure of input files;
- normalize data from different JSON formats to a single model;
- read and process CSV from a previous version of the application;
- implement `exception handling` when processing files;
- use `logging` to record processing stages and problematic data;
- build a Streamlit application with multiple navigation sections;
- generate an annual analytical report based on summarized data.

---

## Problem plot

The personal budget app has changed several times over the year. As a result, data has been stored in different formats:

1. **The last quarter of the year** saved in **CSV** is the result of the previous task.
2. **The first 9 months of the year** come as **three separate JSON files**.
3. Each JSON has a **different structure** because the format was changed at the customer's request.
4. One of the JSON files contains a **training error in the September data**. It needs to be detected, processed, and logged.

Your task is to create an application that downloads these files, checks them, normalizes them, combines them into a single annual set, and builds a convenient annual report.

---

## What needs to be implemented

### 1. Data loading

The application should allow you to download:

- `3` JSON files of quarters;
- `1` CSV file of the last quarter.

### 2. Data structure check

Before normalization, you need to check:

- is the file readable at all;
- whether the format matches the expected one (`.json` or `.csv`);
- are the required fields present?
- whether the values have the correct type;
- is it possible to determine the quarter and month;
- whether the amounts are numerical;
- are there any obvious structural errors?

### 3. Data Normalization

It is necessary to bring all 4 sources into a **single structure**.

Importantly:

- normalization logic should be placed in a **separate Python file**;
- `Month 1` should be interpreted as **the first month of the corresponding quarter**, and not as a universal month name for the entire year;
- The CSV from the previous task must be processed correctly, taking into account service lines such as `TOTAL`, `REVENUE`, `EXPENSES`, `BALANCE`.

### 4. Formation of an annual data set

After normalization, all records need to be combined into a single dataset to construct:

- annual report;
- quarterly comparison;
- viewing a single month.

### 5. Building an annual report

The application must show:

- total income for the year;
- total expenses for the year;
- balance of funds;
- distribution of expenses by category;
- comparison of quarters;
- breakdown by month;
- tables and graphs.

### 6. Error messages

The user should see clear messages if:

- the file is damaged;
- the structure does not meet expectations;
- some records have incorrect values;
- an error was detected in the September data.

### 7. Logging

The application should create a log file and record key events and problems in it.

---

## Streamlit interface requirements

The application should have a **left navigation bar** with sections:

### Home page
Must contain:

- application name;
- a short welcome message;
- description of the purpose of the application;
- a short user manual.

### Annual report
Should display:

- metrics for the year;
- a table or tables with summarized data;
- expense schedule by category;
- comparison of quarters.

### Quarterly report
Should display:

- indicators of each quarter;
- comparison of quarters with each other;
- a table or graph by quarter.

### Report for a specific month
Should allow:

- choose a month;
- see income, expenses, balance;
- view expenses by category;
- see the corresponding schedule.

### Loading data
Must contain:

- file uploaders;
- processing start button;
- success or error messages.

> **Important:**
> don't use `use_container_width`.
> For relevant interface elements, use only `width="stretch"`.

---

## Normalization requirements

Create a separate module, for example:

```text
data_normalizer.py
```

It should have functions for:

- reading CSV;
- reading JSON;
- structure checks;
- normalization of various JSON formats;
- normalize CSV from the previous problem;
- data validation;
- combining results into a single DataFrame.

### Example of target structure after normalization

```python
{
"year": 2025,
"quarter": "Q1",
"month_index_in_quarter": 1,
"month_number": 1,
"month_name": "January",
"category": "Food",
"amount": 3500.0,
"record_type": "expense",
"source_file": "q1_budget.json",
"source_format": "json"
}
```

### Minimum fields of a single structure

- `year`
- `quarter`
- `month_index_in_quarter`
- `month_number`
- `month_name`
- `category`
- `amount`
- `record_type`
- `source_file`
- `source_format`

---

## Examples of differences between JSON files

Your solution should take into account that JSON can have different structures.

### Example 1

```json
{
"quarter": "Q1",
"months": [
{
"month": "Month 1",
"income": 12000,
"expenses": {
"Food": 3500,
"Transport": 500,
"Entertainment": 900
}
}
]
}
```

### Example 2

```json
{
"period": "Q2",
"data": [
{
"name": "Month 1",
"salary": 14000,
"costs": [
{"category": "Food", "value": 3200},
{"category": "Transport", "value": 700}
]
}
]
}
```

### Example 3

```json
{
"quarter_id": 3,
"budget": {
"month_1": {
"income_total": 15000,
"expense_items": {
"food": 4100,
"transport": 600,
"other": 900
}
}
}
}
```

You need to be able to convert all of these options to a single format.

---

## Requirements for exception handling

Exception handling is **required** in this task.

It is necessary to provide for the handling of at least the following situations:

- file not downloaded;
- the file is empty;
- JSON is not readable;
- CSV is not readable;
- required fields are missing;
- the values are of the wrong type;
- the sum is not a number;
- it is impossible to determine the month or quarter;
- the data for September contains an error.

### Minimally expected exceptions

- `FileNotFoundError`
- `json.JSONDecodeError`
- `UnicodeDecodeError`
- `pandas.errors.ParserError`
- `KeyError`
- `ValueError`
- `TypeError`

You can optionally create your own exceptions if it improves the structure of the solution.

---

## Logging requirements

Use the `logging` module.

Logging should:

- write to a file;
- contain the date and time;
- contain the message level;
- record key processing stages;
- record problem entries and errors.

### Recommended path to the log file

```text
logs/app.log
```

### What exactly should be logged

Be sure to log:

- start of the application;
- download each file;
- start normalization of a specific file;
- successful completion of normalization;
- number of successfully processed records;
- number of rejected entries;
- missing fields;
- incorrect types;
- suspicious or problematic values;
- an error in the September data;
- construction of the final annual set;
- formation of a final report.

### Example of log format

```text
2026-03-29 10:15:21 | INFO | File loaded: q1_budget.json
2026-03-29 10:15:21 | INFO | Start normalization for q1_budget.json
2026-03-29 10:15:21 | WARNING | Missing category 'Other' in month_2
2026-03-29 10:15:22 | ERROR | Invalid September value: 'unknown'
```

---

## Special condition: error in September data

One of the JSON files intentionally contains an error in the data for September.

### Important

This error **cannot be ignored**.

The student must:

- detect an erroneous entry;
- log the problem;
- or correctly skip the entry with an explanation;
- or partially process the file and show a warning;
- or stop processing with an explanation of the reason.

But you can't pretend that the mistake didn't exist.

---

## Expected Python modules

The minimum expected use is:

- `streamlit`
- `pandas`
- `json`
- `logging`
- `pathlib`
- `io`
- `typing`
- `datetime`

It is also appropriate to use:

- `pytest` — for tests
- `os` — as needed

---

## Expense categories

After normalization, the categories should be reduced to a single set, for example:

- `Food`
- `Transport`
- `Entertainment`
- `Housing / Utilities`
- `Other`

If the source JSON uses alternative names (`food`, `transport`, `housing`, `other`), they need to be mapped to these names.

---

## Limitations

In this job you cannot:

- hardcode the finished annual result manually;
- ignore differences between JSON formats;
- keep all logic only in `streamlit_app.py`;
- hide errors without logging;
- to miss the September error without explanation;
- use `use_container_width`.

---

## Recommended repository structure

```text
budget-year-report/
│
├── streamlit_app.py
├── data_normalizer.py
├── utils.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│ ├── sample_q1.json
│ ├── sample_q2.json
│ ├── sample_q3_with_error.json
│ └── quarterly_budget.csv
│
├── logs/
│ └── app.log
│
└── tests/
├── test_normalizer.py
├── test_validation.py
└── test_streamlit_app.py
```

---

## File requirements

### `streamlit_app.py`
Must contain:

- Streamlit interface;
- side navigation;
- file upload;
- call normalization functions;
- construction of tables, metrics and graphs;
- user notifications about errors and warnings.

### `data_normalizer.py`
Must contain:

- file reading functions;
- structure checking functions;
- CSV normalization;
- normalization of various JSON structures;
- value validation;
- formation of a single data set.

### `utils.py`
May contain:

- auxiliary functions;
- mapping of months;
- category mapping;
- logging settings.

### `requirements.txt`
It should contain all the necessary dependencies to run the project.

### `tests/`
There should be tests for at least the critical parts of the logic.

---

## How to launch a project

### 1. Clone the repository

```bash
git clone <repo-url>
cd budget-year-report
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

For Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Launch the application

```bash
streamlit run streamlit_app.py
```

---

## Minimum result

A solution is considered to be basically workable if:

- you can upload 3 JSON and 1 CSV;
- files are read and checked;
- normalization is performed;
- a common annual data set is being formed;
- an annual report is being prepared;
- a log file is created;
- the error is revealed in September and does not disappear without a trace.

---

## What will be assessed

The following will be taken into account during the inspection:

- correctness of reading and processing files;
- the presence of normalization in a separate module;
- quality of error handling;
- availability and content of logging;
- correctness of the Streamlit interface;
- ease of navigation;
- quality of code structure;
- clarity of messages for the user;
- correct reaction to problematic September data.

---

## Typical student mistakes

Pay attention to these common problems:

- all logic is written in one file;
- the solution is designed for only one specific JSON format;
- no check for missing keys;
- no logging or logs contain only `print`;
- the problematic September entry simply disappears;
- CSV with summary rows is processed incorrectly;
- `Month 1` is processed without taking into account the quarter;
- the user does not see an explanation of errors in the application.

---

## Tip

Don't try to build the entire application at once. It's better to move in stages:

1. implement file reading;
2. check the structure;
3. implement normalization;
4. merge the data;
5. add logging;
6. Only after that build the interface and visualizations.

---

## Remember

This task is not about "drawing a graph at any cost", but about **quality data processing in a realistic scenario**.

Your solution should show that you can:

- work with incomplete and heterogeneous data;
- do not hide mistakes;
- build understandable and maintainable code;
- create an analytical application that can be explained and tested.

