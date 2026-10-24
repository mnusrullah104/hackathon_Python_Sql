import sqlite3
from datetime import datetime

con = sqlite3.connect("db/hr.db")
results = []
now = datetime.now().isoformat(timespec="seconds")

def q(sql):
    return con.execute(sql).fetchone()[0]

def add(kind, table, check, ok, detail):
    results.append((now, kind, table, check, "PASS" if ok else "FAIL", detail))

# 1. Primary key: unique aur not null
PKS = {
    "dim_date": ["date_key"], "dim_department": ["dept_id"],
    "dim_employee": ["employee_key"], "dim_shift": ["shift_code"],
    "fact_attendance_daily": ["attendance_id"], "fact_leave_day": ["leave_day_id"],
    "fact_overtime_approved": ["request_id"], "fact_payroll_line": ["line_id"],
    "stg_employees": ["emp_id"], "stg_punches": ["punch_id"],
    "stg_attendance_daily": ["emp_id", "work_date"],
    "stg_leave_requests": ["request_id"], "stg_overtime_requests": ["request_id"],
    "stg_payroll_lines": ["line_id"],
}
for t, cols in PKS.items():
    cl = ", ".join(cols)
    total = q(f"SELECT COUNT(*) FROM {t}")
    dist = q(f"SELECT COUNT(*) FROM (SELECT DISTINCT {cl} FROM {t})")
    nulls = q(f"SELECT COUNT(*) FROM {t} WHERE " + " OR ".join(f"{c} IS NULL" for c in cols))
    add("primary_key", t, f"unique({cl})", total == dist, f"rows={total}, distinct={dist}")
    add("primary_key", t, f"not_null({cl})", nulls == 0, f"null_rows={nulls}")

# 2. Referential integrity: har fact row ka dimension row
FKS = [
    ("fact_attendance_daily", "employee_key", "dim_employee", "employee_key"),
    ("fact_attendance_daily", "date_key", "dim_date", "date_key"),
    ("fact_attendance_daily", "dept_id", "dim_department", "dept_id"),
    ("fact_attendance_daily", "shift_code", "dim_shift", "shift_code"),
    ("fact_leave_day", "employee_key", "dim_employee", "employee_key"),
    ("fact_leave_day", "date_key", "dim_date", "date_key"),
    ("fact_overtime_approved", "employee_key", "dim_employee", "employee_key"),
    ("fact_overtime_approved", "date_key", "dim_date", "date_key"),
    ("fact_payroll_line", "employee_key", "dim_employee", "employee_key"),
    ("fact_payroll_line", "date_key", "dim_date", "date_key"),
    ("dim_employee", "dept_id", "dim_department", "dept_id"),
]
for f, fc, d, dc in FKS:
    n = q(f"SELECT COUNT(*) FROM {f} x LEFT JOIN {d} y ON x.{fc} = y.{dc} "
          f"WHERE x.{fc} IS NOT NULL AND y.{dc} IS NULL")
    add("referential", f, f"{fc} -> {d}.{dc}", n == 0, f"orphan_rows={n}")

# 3. Reconciliation: raw = staging + rejected/merged/dropped
RECON = [
    ("raw_departments", ["stg_departments"]),
    ("raw_employees", ["stg_employees", "stg_employee_merge_log"]),
    ("raw_employment_history", ["stg_employment_history", "stg_history_fix_log"]),
    ("raw_shift_roster", ["stg_shift_roster"]),
    ("raw_holidays", ["stg_holidays"]),
    ("raw_device_mapping", ["stg_device_mapping"]),
    ("raw_shifts", ["stg_shifts"]),
    ("raw_leave_requests", ["stg_leave_requests"]),
    ("raw_overtime_requests", ["stg_overtime_requests"]),
    ("raw_payroll_lines", ["stg_payroll_lines"]),
    ("raw_punches", ["stg_punches", "stg_rejected_punches"]),
]
for raw, parts in RECON:
    r = q(f"SELECT COUNT(*) FROM {raw}")
    s = sum(q(f"SELECT COUNT(*) FROM {p}") for p in parts)
    add("reconciliation", raw, "raw = " + " + ".join(parts), r == s, f"raw={r}, accounted={s}")

# 4. Accepted values
ACC = [
    ("fact_attendance_daily", "status",
     ["Present", "Absent", "On Leave", "Holiday", "Weekly Off", "Missing Punch"]),
    ("fact_leave_day", "leave_type", ["Annual", "Casual", "Sick"]),
    ("fact_overtime_approved", "status", ["Approved", "Rejected", "Pending"]),
    ("fact_payroll_line", "component",
     ["BASIC", "HOUSE_RENT", "MEDICAL", "CONVEYANCE", "EOBI", "INCOME_TAX",
      "OVERTIME", "ABSENCE_DEDUCTION", "LOAN_INSTALLMENT"]),
    ("fact_payroll_line", "component_type", ["EARNING", "DEDUCTION"]),
]
for t, c, vals in ACC:
    lst = ",".join("'" + v + "'" for v in vals)
    n = q(f"SELECT COUNT(*) FROM {t} WHERE {c} IS NULL OR {c} NOT IN ({lst})")
    add("accepted_values", t, f"{c} in allowed list", n == 0, f"bad_rows={n}")

# 5. Business sanity
n = q("SELECT COUNT(*) FROM fact_attendance_daily WHERE worked_hours < 0")
add("business", "fact_attendance_daily", "no negative worked_hours", n == 0, f"bad_rows={n}")
n = q("SELECT COUNT(*) FROM fact_attendance_daily WHERE worked_hours > 16")
add("business", "fact_attendance_daily", "no shift longer than 16h", n == 0, f"bad_rows={n}")
n = q("""SELECT COUNT(*) FROM dim_employee a JOIN dim_employee b
         ON a.emp_id = b.emp_id AND a.employee_key < b.employee_key
         AND a.valid_from <= COALESCE(b.valid_to, '9999-12-31')
         AND b.valid_from <= COALESCE(a.valid_to, '9999-12-31')""")
add("business", "dim_employee", "no overlapping SCD2 ranges", n == 0, f"overlaps={n}")

# Natije dq_results table mein
con.execute("DROP TABLE IF EXISTS dq_results")
con.execute("""CREATE TABLE dq_results (run_at TEXT, check_type TEXT, table_name TEXT,
               check_name TEXT, status TEXT, detail TEXT)""")
con.executemany("INSERT INTO dq_results VALUES (?,?,?,?,?,?)", results)
con.commit()

fails = [r for r in results if r[4] == "FAIL"]
print(f"DQ checks: {len(results)} | PASS: {len(results) - len(fails)} | FAIL: {len(fails)}")
for r in fails:
    print("FAIL:", r[2], "|", r[3], "|", r[5])
con.close()