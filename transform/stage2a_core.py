import sqlite3
import pandas as pd

con = sqlite3.connect("db/hr.db")


def raw(table):
    return pd.read_sql(f"SELECT * FROM {table}", con)


def txt(s):
    return s.fillna("").astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def iso(s):
    s = txt(s)
    out = pd.to_datetime(pd.Series([None] * len(s), index=s.index))
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"):
        out = out.fillna(pd.to_datetime(s, format=fmt, errors="coerce"))
    return out.dt.strftime("%Y-%m-%d")


def clean_all(df):
    for c in df.columns:
        if not c.startswith("_"):
            df[c] = txt(df[c])
    return df


log = []

d = clean_all(raw("raw_departments"))
d["renamed_on"] = iso(d["renamed_on"])
d.drop(columns=[c for c in d.columns if c.startswith("_")]).to_sql(
    "stg_departments", con, if_exists="replace", index=False)
log.append(("raw_departments", len(d), len(d), 0))

mapping = {}
for r in d.itertuples():
    mapping.setdefault(r.dept_name.lower(), r.dept_name)
    if r.previous_name:
        mapping.setdefault(r.previous_name.lower(), r.dept_name)

e = clean_all(raw("raw_employees"))
raw_count = len(e)
e["updated_ts"] = pd.to_datetime(e["updated_at"], errors="coerce")
e = e.sort_values(["emp_id", "updated_ts", "_row_hash"])
dup = e.duplicated("emp_id", keep="last")
dropped = e[dup].copy()
kept = e[~dup].set_index("emp_id")["updated_at"]
dropped["kept_updated_at"] = dropped["emp_id"].map(kept)
dropped["reason"] = "older updated_at for same emp_id"
dropped[["emp_id", "updated_at", "kept_updated_at", "reason", "_row_hash"]].to_sql(
    "stg_employee_merge_log", con, if_exists="replace", index=False)
e = e[~dup].copy()

for c in ["date_of_birth", "hire_date", "separation_date"]:
    e[c] = iso(e[c])
e["annual_leave_entitlement"] = pd.to_numeric(e["annual_leave_entitlement"], errors="coerce")

key = e["department"].str.lower()
e["department"] = key.map(mapping).fillna(e["department"].str.title())
unmapped = sorted(set(e["department"]) - set(d["dept_name"]))
print("Departments jo departments.csv se match nahi hue:", unmapped)

cols = ["emp_id", "full_name", "gender", "email", "phone", "date_of_birth", "hire_date",
        "separation_date", "plant", "department", "designation", "grade",
        "employment_type", "status", "annual_leave_entitlement", "updated_at"]
e[cols].to_sql("stg_employees", con, if_exists="replace", index=False)
log.append(("raw_employees", raw_count, len(e), 0))
print("Employees merged:", len(dropped))

h = clean_all(raw("raw_employment_history"))
h["valid_from"] = iso(h["effective_from"])
h["orig_effective_to"] = iso(h["effective_to"])
h["basic_salary"] = pd.to_numeric(h["basic_salary"], errors="coerce")
h = h.sort_values(["emp_id", "valid_from"])
nxt = pd.to_datetime(h.groupby("emp_id")["valid_from"].shift(-1))
h["valid_to"] = (nxt - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
bad = h[h["valid_to"].notna() & (h["valid_to"] < h["valid_from"])]
print("History rows jinka valid_to < valid_from:", len(bad))
hc = ["emp_id", "valid_from", "valid_to", "orig_effective_to", "dept_id", "designation",
      "grade", "basic_salary", "change_reason"]
h[hc].to_sql("stg_employment_history", con, if_exists="replace", index=False)
log.append(("raw_employment_history", len(h), len(h), 0))

r = clean_all(raw("raw_shift_roster"))
r["week_start"] = iso(r["week_start"])
r["shift_code"] = r["shift_code"].str.upper()
r[["emp_id", "week_start", "shift_code"]].to_sql(
    "stg_shift_roster", con, if_exists="replace", index=False)
log.append(("raw_shift_roster", len(r), len(r), 0))

ho = clean_all(raw("raw_holidays"))
ho["holiday_date"] = iso(ho["holiday_date"])
ho["scope"] = ho["scope"].str.upper()
ho[["holiday_date", "holiday_name", "scope"]].to_sql(
    "stg_holidays", con, if_exists="replace", index=False)
log.append(("raw_holidays", len(ho), len(ho), 0))

dm = clean_all(raw("raw_device_mapping"))
dm["enrolled_on"] = iso(dm["enrolled_on"])
dm[["device_id", "device_user_id", "emp_id", "enrolled_on"]].to_sql(
    "stg_device_mapping", con, if_exists="replace", index=False)
log.append(("raw_device_mapping", len(dm), len(dm), 0))

lg = pd.DataFrame(log, columns=["raw_table", "raw_rows", "staging_rows", "rejected_rows"])
lg["merged_or_dropped"] = lg["raw_rows"] - lg["staging_rows"] - lg["rejected_rows"]
lg.to_sql("stg_load_log", con, if_exists="replace", index=False)
print(lg)
con.close()