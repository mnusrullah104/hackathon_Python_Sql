
# Indus Weave HR Pipeline

A Python and SQLite data engineering project that transforms raw Human Capital Management (HCM) data into a clean, reliable, and analytics-ready data warehouse.

The pipeline includes data ingestion, data cleaning,employee history tracking, attendance processing, business analytics,and data quality checks.

## Project Overview

HR data often contains duplicate records, missing employee mappings, incorrect attendance times, and inconsistent information.

This project solves these problems by building a complete data pipeline that processes raw HR data and prepares it for business reporting and analysis.

## Key Features

- **Data Ingestion:** Loads raw HR data from source files into SQLite.
- **Data Cleaning:** Cleans and prepares data for further processing.
- **Duplicate Handling:** Removes duplicate employee records and attendance punches.
- **Employee History:** Tracks employee changes using SCD Type 2.
- **Attendance Processing:** Handles attendance punches, including night shifts.
- **Data Warehouse:** Organizes processed data using a star schema.
- **Business Analytics:** Runs 10 business queries and saves results as CSV files.
- **Data Quality Checks:** Identifies data issues and stores the results in the database.
- **Error Investigation:** Detects and corrects attendance device clock problems.

## Technologies Used

- Python
- SQLite
- SQL
- Pandas
- SQLAlchemy
- CSV
- Data Cleaning and Transformation
- Data Warehousing
- ETL Pipeline
- Data Quality Checks

## Pipeline Architecture

The pipeline follows these steps:

1. **Ingestion:** Load raw HCM data.
2. **Staging:** Clean, validate, and prepare the data.
3. **Attendance Processing:** Process attendance punches and handle duplicates.
4. **Data Warehouse:** Build structured tables for analysis.
5. **Analytics:** Run business queries and export results.
6. **Data Quality:** Check the processed data and store quality results.

**Pipeline Flow:**

`Raw Data → Staging → Attendance Processing → Data Warehouse → Analytics → Data Quality Checks`

## Project Setup

### 1. Install Python

Install Python 3 on your computer.

### 2. Create a Virtual Environment

Run the following commands in your terminal:

```bash
python -m venv venv
```

Activate the environment on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

### 4. Prepare the Data

Extract `indus_weave_hcm_data.zip` and place the data files in the folder specified at the top of `ingestion/load_raw.py`.

## Run the Pipeline

### Run from Scratch

```bash
python run_pipeline.py --fresh
```

This command creates the database from scratch and runs the complete pipeline, from raw data ingestion to data quality checks.

**Note:** Use this option carefully because it rebuilds the database.

### Run Again

```bash
python run_pipeline.py
```

This command keeps the raw data and rebuilds the later processing stages.

## Project Outputs

### Analytics Results

Business query results are saved as CSV files in:

`analytics/results/`

### Data Quality Results

Data quality results are stored in the `dq_results` table inside:

`db/hr.db`

These outputs can be used to review business insights and identify data quality issues.

## Important Data Engineering Decisions

### 1. Raw Data Layer

- Stored raw data as text.
- Added `_source_file` to track the source file.
- Added `_loaded_at` to record the load time.
- Added `_row_hash` to help identify duplicate records.
- Designed the loading process to support repeated runs.

### 2. Employee Deduplication

When multiple records existed for the same employee, the latest record based on `updated_at` was kept.

The merge details were recorded in `stg_employee_merge_log`.

### 3. Employee History

Used SCD Type 2 to maintain employee history in `dim_employee`.

Historical records were managed using effective dates. The next record determined when the previous record ended.

### 4. Attendance Processing

- Removed duplicate punches within two minutes.
- Stored unmatched punches in `stg_rejected_punches`.
- Assigned night-shift punches to the shift's start date.

### 5. Data Warehouse Design

Used a star schema to organize data for business reporting and analytics.

Foreign key relationships were enforced to maintain data integrity.

## Case Study: Faulty Attendance Device Clock

### Problem

The attendance device `DEV-SITE-01` had a clock that was one hour ahead starting July 1, 2026.

This caused incorrect attendance times and affected early-departure calculations.

### Investigation

The issue was identified by comparing median check-in times across sites.

The investigation was performed using:

`transform/diagnose_drift.py`

### Solution

Only attendance punches from July 1, 2026, onward were corrected by subtracting one hour.

### Results

- **Before the correct fix:** 21,360 false early departures.
- **After the correct fix:** 3,167 early departures remained.

The remaining records were not automatically assumed to be errors and required further investigation.

### Key Lesson

Always investigate the root cause of a data quality issue before applying a correction. A correction applied to the wrong time period can create more problems than it solves.

## Skills Demonstrated

Through this project, I demonstrated practical work with:

- Python programming
- SQL and SQLite
- ETL pipeline development
- Data ingestion and transformation
- Data cleaning and deduplication
- Employee history tracking with SCD Type 2
- Star schema data warehouse design
- Attendance data processing
- Business analytics
- Data quality validation
- Debugging and root cause analysis

## Project Structure

```text
indus-weave-hr-pipeline/
│
├── ingestion/
│   └── load_raw.py
│
├── transform/
│   └── diagnose_drift.py
│
├── analytics/
│   └── results/
│
├── db/
│   └── hr.db
│
├── requirements.txt
├── run_pipeline.py
├── warehouse.png
└── README.md
```

*Note: This is a simplified overview. Other project folders and files may also be present.*

## Individual Project

**Name:** Muhammad Nasrullah

**Project:** Indus Weave HR Pipeline

**Role:** Data Engineer

This is an individual data engineering project focused on building a reliable pipeline from raw HR data to a structured data warehouse and business analytics.

---

**Author:** Muhammad Nasrulla