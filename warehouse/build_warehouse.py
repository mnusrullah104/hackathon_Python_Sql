import sqlite3
from pathlib import Path
import pandas as pd

con = sqlite3.connect("db/hr.db")
con.executescript(Path("warehouse/ddl/01_create_warehouse.sql").read_text(encoding="utf-8"))
con.execute("PRAGMA foreign_keys = ON")


def plant_code(p):
    p = str(p).lower()
    if "head" in p or p.strip() == "ho":
        return "HO"
    if "korangi" in p or p.strip() == "kor":
        return "KOR"
    if "site" in p:
        return "SITE"
    if "faisal" in p or p.strip() == "fsd":
        return "FSD"
    return "UNK"


def load(df, table):
    df = df.where(df.notna(), None)
    df.to_sql(table, con, if_exists="append", index=False, chunksize=20000)
    con.commit()
    print(f"{table:26} rows={len(df)}")


dates = pd.date_range("2026-01-01", "2026-12-31")
dd = pd.DataFrame({
    "date_key": dates.strftime("%Y%m%d").astype(int),
    "full_date": dates.strftime("%Y-%m-%d"),
    "year": dates.year,
    "month": dates.month,
    "month_name": dates.strftime("%B"),
    "year_month": dates.strftime("%Y-%m"),
    "day": dates.day,
    "day_of_week": dates.day_of_week,
    "day_name": dates.strftime("%A"),
    "is_sunday": (dates.day_of_week == 6).astype(int),
    "week_start": (dates - pd.to_timedelta(dates.day_of_week, unit="D")).strftime("%Y-%m-%d"),
    "month_end": (dates + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d"),
})
load(dd, "dim_date")

dep = pd.read_sql("SELECT * FROM stg_departments", con)
dep["plant_code"] = dep["plant"].map(plant_code)
dep = dep[["dept_id", "dept_name", "plant", "plant_code", "cost_center",
           "previous_name", "renamed_on"]]
dep = dep.where(dep != "", None)
load(dep, "dim_department")

sh = pd.read_sql("SELECT * FROM stg_shifts", con).rename(columns={"name": "shift_name"})
load(sh[["shift_code", "shift_name", "start_time", "end_time",
         "crosses_midnight", "grace_minutes"]], "dim_shift")

emp = pd.read_sql("SELECT * FROM stg_employees", con)
h = pd.read_sql("SELECT * FROM stg_employment_history", con)
print("History rows jin ka emp_id employees mein nahi:", int((~h["emp_id"].isin(emp["emp_id"])).sum()))
print("Employees jin ki history nahi:", int((~emp["emp_id"].isin(h["emp_id"])).sum()))
print("History dept_id jo departments mein nahi:", int((~h["dept_id"].isin(dep["dept_id"])).sum()))

e2 = emp[["emp_id", "full_name", "gender", "hire_date", "separation_date", "plant",
          "employment_type", "status", "annual_leave_entitlement"]].rename(
    columns={"status": "emp_status"})
de = h.merge(e2, on="emp_id", how="inner")
de["is_current"] = de["valid_to"].isna().astype(int)
de["valid_to"] = de["valid_to"].fillna("9999-12-31")
de = de.sort_values(["emp_id", "valid_from"]).reset_index(drop=True)
de["employee_key"] = de.index + 1
de["annual_leave_entitlement"] = de["annual_leave_entitlement"].astype("Int64")
load(de[["employee_key", "emp_id", "full_name", "gender", "hire_date", "separation_date",
         "employment_type", "emp_status", "annual_leave_entitlement", "plant", "dept_id",
         "designation", "grade", "basic_salary", "change_reason", "valid_from",
         "valid_to", "is_current"]], "dim_employee")

ek = de[["employee_key", "emp_id", "valid_from"]].copy()
ek["valid_from"] = pd.to_datetime(ek["valid_from"])
ek = ek.sort_values("valid_from")


def attach(df, date_col):
    x = df.copy()
    x["_d"] = pd.to_datetime(x[date_col])
    x = x.sort_values("_d")
    x = pd.merge_asof(x, ek, left_on="_d", right_on="valid_from",
                      by="emp_id", direction="backward")
    missing = int(x["employee_key"].isna().sum())
    x = x[x["employee_key"].notna()].copy()
    x["employee_key"] = x["employee_key"].astype(int)
    x["date_key"] = x["_d"].dt.strftime("%Y%m%d").astype(int)
    return x, missing


att = pd.read_sql("SELECT * FROM stg_attendance_daily", con)
att, miss = attach(att, "work_date")
print("Attendance rows bina SCD2 match ke (drop):", miss)
load(att[["employee_key", "date_key", "dept_id", "shift_code", "status", "punch_count",
          "check_in", "check_out", "worked_hours", "late_minutes",
          "early_departure_minutes", "overtime_hours", "is_late",
          "is_early_departure", "is_sunday", "is_holiday"]], "fact_attendance_daily")

ld = pd.read_sql("SELECT * FROM stg_leave_days", con)
ld, miss = attach(ld, "leave_date")
print("Leave days bina SCD2 match ke (drop):", miss)
load(ld[["request_id", "employee_key", "date_key", "leave_type"]], "fact_leave_day")

ot = pd.read_sql("SELECT * FROM stg_overtime_requests", con)
ot, miss = attach(ot, "ot_date")
print("OT rows bina SCD2 match ke (drop):", miss)
load(ot[["request_id", "employee_key", "date_key", "requested_hours", "approved_hours",
         "status", "approver_id", "requested_at"]], "fact_overtime_approved")

pl = pd.read_sql("SELECT * FROM stg_payroll_lines", con)
month_end = pd.to_datetime(pl["payroll_month"] + "-01") + pd.offsets.MonthEnd(0)
sep = pd.to_datetime(pl["emp_id"].map(emp.set_index("emp_id")["separation_date"]), errors="coerce")
pl["month_end"] = month_end
pl["eff"] = month_end.where(sep.isna() | (sep >= month_end), sep)
pl, miss = attach(pl, "eff")
print("Payroll rows bina SCD2 match ke (drop):", miss)
pl["date_key"] = pl["month_end"].dt.strftime("%Y%m%d").astype(int)
load(pl[["line_id", "payroll_month", "employee_key", "date_key", "component",
         "component_type", "units", "amount"]], "fact_payroll_line")

con.execute("PRAGMA foreign_keys = ON")
bad = con.execute("PRAGMA foreign_key_check").fetchall()
print("Foreign key violations:", len(bad))
con.close()