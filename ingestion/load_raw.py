import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
import pandas as pd

DATA = Path("data_raw")
DB = Path("db/hr.db")

CSV_FILES = {
    "employees.csv": "raw_employees",
    "employment_history.csv": "raw_employment_history",
    "departments.csv": "raw_departments",
    "shift_roster.csv": "raw_shift_roster",
    "device_mapping.csv": "raw_device_mapping",
    "biometric_punches.csv": "raw_punches",
    "holidays.csv": "raw_holidays",
    "overtime_requests.csv": "raw_overtime_requests",
    "payroll_lines.csv": "raw_payroll_lines",
    "applications.csv": "raw_applications",
}
JSON_FILES = {
    "shifts.json": "raw_shifts",
    "leave_requests.json": "raw_leave_requests",
}


def row_hash(source, n, values):
    text = source + "|" + str(n) + "|" + "|".join(values)
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def load_table(con, df, table, source):
    df = df.astype(str)
    hashes = [
        row_hash(source, i, list(r))
        for i, r in enumerate(df.itertuples(index=False))
    ]
    df["_source_file"] = source
    df["_loaded_at"] = datetime.now().isoformat(timespec="seconds")
    df["_row_hash"] = hashes

    cols = ", ".join(f'"{c}" TEXT' for c in df.columns)
    con.execute(f'CREATE TABLE IF NOT EXISTS {table} ({cols}, UNIQUE(_row_hash))')

    names = ", ".join(f'"{c}"' for c in df.columns)
    marks = ", ".join("?" for _ in df.columns)
    con.executemany(
        f"INSERT OR IGNORE INTO {table} ({names}) VALUES ({marks})",
        df.itertuples(index=False, name=None),
    )
    con.commit()

    in_table = con.execute(
        f"SELECT COUNT(*) FROM {table} WHERE _source_file = ?", (source,)
    ).fetchone()[0]
    status = "OK" if in_table == len(df) else "MISMATCH"
    con.execute(
        "INSERT INTO raw_load_log VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), source, table,
         len(df), in_table, status),
    )
    con.commit()
    print(f"{source:28} file={len(df):>7}  table={in_table:>7}  {status}")


def main():
    DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute(
        "CREATE TABLE IF NOT EXISTS raw_load_log "
        "(run_at TEXT, source_file TEXT, table_name TEXT, "
        "file_rows INTEGER, table_rows INTEGER, status TEXT)"
    )

    for fname, table in CSV_FILES.items():
        df = pd.read_csv(DATA / fname, dtype=str, keep_default_na=False)
        load_table(con, df, table, fname)

    for fname, table in JSON_FILES.items():
        with open(DATA / fname, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = next(v for v in data.values() if isinstance(v, list))
        df = pd.DataFrame({"payload": [json.dumps(r, ensure_ascii=False) for r in data]})
        load_table(con, df, table, fname)

    con.close()


if __name__ == "__main__":
    main()