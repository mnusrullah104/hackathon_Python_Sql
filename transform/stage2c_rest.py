import json
import sqlite3
import pandas as pd

con = sqlite3.connect("db/hr.db")


def txt(s):
    return s.fillna("").astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def iso(s):
    s = txt(s)
    out = pd.to_datetime(pd.Series([None] * len(s), index=s.index))
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"):
        out = out.fillna(pd.to_datetime(s, format=fmt, errors="coerce"))
    return out.dt.strftime("%Y-%m-%d")


def add_log(name, raw_n, stg_n, rej_n=0):
    row = pd.DataFrame([(name, raw_n, stg_n, rej_n, raw_n - stg_n - rej_n)],
                       columns=["raw_table", "raw_rows", "staging_rows",
                                "rejected_rows", "merged_or_dropped"])
    row.to_sql("stg_load_log", con, if_exists="append", index=False)


# ---------- 1. History fix ----------
hist = pd.read_sql("SELECT * FROM stg_employment_history", con)
emp = pd.read_sql("SELECT emp_id, hire_date FROM stg_employees", con)
hist = hist.merge(emp, on="emp_id", how="left")
hist["is_hire"] = hist["change_reason"].str.lower() == "hire"
tie = hist.duplicated(["emp_id", "valid_from"], keep=False)
fix_rows, drop_idx = [], []
for idx, r in hist[tie & hist["is_hire"]].iterrows():
    if isinstance(r["hire_date"], str) and r["hire_date"] < r["valid_from"]:
        hist.loc[idx, "valid_from"] = r["hire_date"]
        fix_rows.append((r["emp_id"], "Hire valid_from set to hire_date " + r["hire_date"]))
    else:
        drop_idx.append(idx)
        fix_rows.append((r["emp_id"], "Hire row dropped, same-day record wins"))
hist = hist.drop(index=drop_idx)
hist = hist.sort_values(["emp_id", "valid_from", "is_hire"], ascending=[True, True, False])
nxt = pd.to_datetime(hist.groupby("emp_id")["valid_from"].shift(-1))
hist["valid_to"] = (nxt - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
cols = ["emp_id", "valid_from", "valid_to", "orig_effective_to", "dept_id",
        "designation", "grade", "basic_salary", "change_reason"]
hist[cols].to_sql("stg_employment_history", con, if_exists="replace", index=False)
pd.DataFrame(fix_rows, columns=["emp_id", "fix"]).to_sql(
    "stg_history_fix_log", con, if_exists="replace", index=False)
print("History fixes:", fix_rows)
print("Bad ranges ab:", int((hist["valid_to"].notna() & (hist["valid_to"] < hist["valid_from"])).sum()))
first = hist.groupby("emp_id")["valid_from"].min().reset_index().merge(emp, on="emp_id")
print("Employees jin ki pehli history date != hire_date:", int((first["valid_from"] != first["hire_date"]).sum()))

# ---------- 2. Shifts ----------
rows = [json.loads(p) for (p,) in con.execute("SELECT payload FROM raw_shifts")]
sh = pd.DataFrame(rows)
sh["crosses_midnight"] = sh["crosses_midnight"].astype(int)
sh["grace_minutes"] = sh["grace_minutes"].astype(int)
sh[["shift_code", "name", "start_time", "end_time", "crosses_midnight", "grace_minutes"]].to_sql(
    "stg_shifts", con, if_exists="replace", index=False)
add_log("raw_shifts", len(rows), len(sh))

# ---------- 3. Leave ----------
recs = [json.loads(p) for (p,) in con.execute("SELECT payload FROM raw_leave_requests")]
req_rows, step_rows = [], []
for r in recs:
    emp_d = r.get("employee") or {}
    lv = r.get("leave") or {}
    req_rows.append({
        "request_id": r.get("request_id"),
        "emp_id": emp_d.get("emp_id"),
        "leave_type": lv.get("type"),
        "from_date": lv.get("from"),
        "to_date": lv.get("to"),
        "days_requested": lv.get("days_requested"),
        "submitted_at": r.get("submitted_at"),
        "cancelled_at": r.get("cancelled_at"),
    })
    for a in (r.get("approvals") or []):
        step_rows.append({
            "request_id": r.get("request_id"),
            "step": a.get("step"),
            "approver_role": a.get("approver_role"),
            "approver_id": a.get("approver_id"),
            "action": a.get("action"),
            "acted_at": a.get("acted_at"),
        })
lr = pd.DataFrame(req_rows)
ls = pd.DataFrame(step_rows)
for c in lr.columns:
    lr[c] = txt(lr[c])
for c in ls.columns:
    ls[c] = txt(ls[c])
lr["from_date"] = iso(lr["from_date"])
lr["to_date"] = iso(lr["to_date"])
lr["leave_type"] = lr["leave_type"].str.title()
print("Duplicate request_id:", int(lr["request_id"].duplicated().sum()))
print("Leave types:", lr["leave_type"].value_counts().to_dict())
print("Approver roles:", ls["approver_role"].value_counts().to_dict())
print("Approval actions:", ls["action"].value_counts().to_dict())

ls["role_l"] = ls["approver_role"].str.lower()
ls["ok"] = ls["action"].str.lower() == "approved"
mgr = ls[ls["role_l"] == "manager"].groupby("request_id")["ok"].all()
hr = ls[ls["role_l"] == "hr"].groupby("request_id")["ok"].all()
lr["manager_approved"] = lr["request_id"].map(mgr).fillna(False).astype(int)
lr["hr_approved"] = lr["request_id"].map(hr).fillna(False).astype(int)
lr["is_cancelled"] = (lr["cancelled_at"] != "").astype(int)
lr["is_counted"] = ((lr["manager_approved"] == 1) & (lr["hr_approved"] == 1)
                    & (lr["is_cancelled"] == 0)).astype(int)
lr.to_sql("stg_leave_requests", con, if_exists="replace", index=False)
ls[["request_id", "step", "approver_role", "approver_id", "action", "acted_at"]].to_sql(
    "stg_leave_approvals", con, if_exists="replace", index=False)
add_log("raw_leave_requests", len(recs), len(lr))
print("Leave requests:", len(lr), "| counted (fully approved, not cancelled):", int(lr["is_counted"].sum()))

# ---------- 4. Leave days ----------
emp_pl = pd.read_sql("SELECT emp_id, plant FROM stg_employees", con)


def plant_code(p):
    p = str(p).lower()
    if "head" in p:
        return "HO"
    if "korangi" in p:
        return "KOR"
    if "site" in p:
        return "SITE"
    if "faisal" in p:
        return "FSD"
    return "UNK"


emp_pl["plant_code"] = emp_pl["plant"].map(plant_code)
pc = dict(zip(emp_pl["emp_id"], emp_pl["plant_code"]))
hol = pd.read_sql("SELECT holiday_date, scope FROM stg_holidays", con)
hol_set = set(zip(hol["holiday_date"], hol["scope"]))

day_rows = []
ok = lr[lr["is_counted"] == 1]
for r in ok.itertuples():
    if not r.from_date or not r.to_date:
        continue
    for d in pd.date_range(r.from_date, r.to_date):
        ds = d.strftime("%Y-%m-%d")
        if d.dayofweek == 6:
            continue
        code = pc.get(r.emp_id, "UNK")
        if (ds, "ALL") in hol_set or (ds, code) in hol_set:
            continue
        day_rows.append((r.request_id, r.emp_id, r.leave_type, ds))
ld = pd.DataFrame(day_rows, columns=["request_id", "emp_id", "leave_type", "leave_date"])
ld.to_sql("stg_leave_days", con, if_exists="replace", index=False)
print("Leave days:", len(ld))

# ---------- 5. Overtime ----------
ot = pd.read_sql("SELECT * FROM raw_overtime_requests", con)
n_raw = len(ot)
for c in ot.columns:
    if not c.startswith("_"):
        ot[c] = txt(ot[c])
ot["ot_date"] = iso(ot["ot_date"])
ot["requested_hours"] = pd.to_numeric(ot["requested_hours"], errors="coerce")
ot["approved_hours"] = pd.to_numeric(ot["approved_hours"], errors="coerce")
ot["status"] = ot["status"].str.title()
print("OT status:", ot["status"].value_counts().to_dict())
print("Duplicate OT request_id:", int(ot["request_id"].duplicated().sum()))
ot[["request_id", "emp_id", "ot_date", "requested_hours", "approved_hours",
    "status", "approver_id", "requested_at"]].to_sql(
    "stg_overtime_requests", con, if_exists="replace", index=False)
add_log("raw_overtime_requests", n_raw, len(ot))

# ---------- 6. Payroll ----------
pl = pd.read_sql("SELECT * FROM raw_payroll_lines", con)
n_raw = len(pl)
for c in pl.columns:
    if not c.startswith("_"):
        pl[c] = txt(pl[c])
pl["component"] = pl["component"].str.upper()
pl["component_type"] = pl["component_type"].str.upper()
pl["units"] = pd.to_numeric(pl["units"], errors="coerce")
pl["amount"] = pd.to_numeric(pl["amount"], errors="coerce")
print("Components:", pl["component"].value_counts().to_dict())
print("Types:", pl["component_type"].value_counts().to_dict())
print("Duplicate line_id:", int(pl["line_id"].duplicated().sum()))
pl[["line_id", "payroll_month", "emp_id", "component", "component_type",
    "units", "amount"]].to_sql("stg_payroll_lines", con, if_exists="replace", index=False)
add_log("raw_payroll_lines", n_raw, len(pl))

add_log("raw_punches", 345280, int(con.execute("SELECT COUNT(*) FROM stg_punches").fetchone()[0]),
        int(con.execute("SELECT COUNT(*) FROM stg_rejected_punches").fetchone()[0]))
print(pd.read_sql("SELECT * FROM stg_load_log", con))
con.close()