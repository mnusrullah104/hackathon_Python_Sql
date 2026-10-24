# Indus Weave HR Pipeline

Python + SQLite pipeline: raw HCM exports se trusted warehouse tak, 10 business questions aur data quality checks.

## Setup
1. Python 3 install karein, phir `python -m venv venv` aur `venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. `indus_weave_hcm_data.zip` unzip karke files us folder mein rakhein jo `ingestion/load_raw.py` ke top par likha hai

## Run
- `python run_pipeline.py --fresh`: database zero se banata hai (raw load se DQ checks tak)
- `python run_pipeline.py`: raw rakh kar staging se aage dobara banata hai

Order: ingestion, stage2a/2b/2c, stage3 attendance, warehouse, analytics queries, DQ checks.
Natije: `analytics/results/*.csv`, DQ results: table `dq_results` in `db/hr.db`.

## Design decisions
- Raw layer sab text, load idempotent, `_source_file`, `_loaded_at`, `_row_hash` ke saath
- Employees dedupe: latest `updated_at` rakha, merge log `stg_employee_merge_log`
- History: `effective_to` ko ignore kiya, record agle record se ek din pehle tak valid
- Punches: 2 minute ke andar duplicate hataye, unmapped punches `stg_rejected_punches` mein
- Night shift punches shift ki start date par assign
- Star schema, SCD2 `dim_employee`, foreign keys enforced

## Faulty device clock
`DEV-SITE-01` ki clock 2026-07-01 se +1 ghanta aage thi. Saboot: SITE ka median check-in KOR/FSD se
June tak 0 minute aur 1 July se lagbhag 60 minute zyada (`transform/diagnose_drift.py`).
Fix sirf 1 July ke baad ke punches par (-1 ghanta).
Lesson learned: pehli blanket fix ne poore period par -1 ghanta lagaya tha, jis se 21,360 nakli early
departures bani. Sahi fix ke baad 3,167 rah gayi.

## Team
(apne naam yahan likhein)