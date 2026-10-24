import sqlite3
import numpy as np
import pandas as pd

START = pd.Timestamp("2026-04-01")
END = pd.Timestamp("2026-09-30")

con = sqlite3.connect("db/hr.db")

n_hist = con.execute("SELECT COUNT(*) FROM stg_employment_history").fetchone()[0]
con.execute(
    "UPDATE stg_load_log SET staging_rows = ?, merged_or_dropped = raw_rows - ? - rejected_rows "
    "WHERE raw_table = 'raw_employment_history'", (n_hist, n_hist))
con.commit()


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


emp = pd.read_sql(
    "SELECT emp_id, hire_date, separation_date, plant FROM stg_employees", con)
emp["hire"] = pd.to_datetime(emp["hire_date"], errors="coerce")
emp["sep"] = pd.to_datetime(emp["separation_date"], errors="coerce")
emp["start"] = emp["hire"].clip(lower=START)
emp["end"] = emp["sep"].fillna(END).clip(upper=END)
emp = emp[emp["hire"].notna() & (emp["start"] <= emp["end"])]

grid = emp[["emp_id", "start", "end", "plant"]].merge(
    pd.DataFrame({"work_date": pd.date_range(START, END)}), how="cross")
grid = grid[(grid["work_date"] >= grid["start"]) & (grid["work_date"] <= grid["end"])]
grid = grid.drop(columns=["start", "end"]).sort_values("work_date")

hist = pd.read_sql("SELECT emp_id, valid_from, dept_id FROM stg_employment_history", con)
hist["valid_from"] = pd.to_datetime(hist["valid_from"])
hist = hist.sort_values("valid_from")
grid = pd.merge_asof(grid, hist, left_on="work_date", right_on="valid_from",
                     by="emp_id", direction="backward")

dep = pd.read_sql("SELECT dept_id, plant FROM stg_departments", con)
dep = dep.drop_duplicates("dept_id")
dep["dept_plant_code"] = dep["plant"].map(plant_code)
grid = grid.merge(dep[["dept_id", "dept_plant_code"]], on="dept_id", how="left")
grid["emp_plant_code"] = grid["plant"].map(plant_code)
valid = ["HO", "KOR", "SITE", "FSD"]
grid["plant_code"] = grid["dept_plant_code"].where(
    grid["dept_plant_code"].isin(valid), grid["emp_plant_code"])
print("Employees per plant:", grid.drop_duplicates("emp_id")["plant_code"].value_counts().to_dict())

ro = pd.read_sql("SELECT emp_id, week_start, shift_code FROM stg_shift_roster", con)
ro["week_start"] = pd.to_datetime(ro["week_start"], errors="coerce")
print("Roster shift codes:", ro["shift_code"].value_counts().to_dict())
print("Roster week_start jo Monday nahi:", int((ro["week_start"].dt.day_of_week != 0).sum()))
print("Roster duplicate emp-week:", int(ro.duplicated(["emp_id", "week_start"]).sum()))
ro = ro.drop_duplicates(["emp_id", "week_start"], keep="last")

weeks = pd.date_range("2026-03-23", "2026-09-28", freq="W-MON")
wk = pd.DataFrame({"emp_id": emp["emp_id"].unique()}).merge(
    pd.DataFrame({"week_start": weeks}), how="cross")
wk = wk.merge(ro, on=["emp_id", "week_start"], how="left")
wk = wk.sort_values(["emp_id", "week_start"])
wk["roster_missing"] = wk["shift_code"].isna()
wk["shift_code"] = wk.groupby("emp_id")["shift_code"].ffill()
wk["shift_code"] = wk.groupby("emp_id")["shift_code"].bfill()

grid["week_start"] = grid["work_date"] - pd.to_timedelta(grid["work_date"].dt.day_of_week, unit="D")
grid = grid.merge(wk[["emp_id", "week_start", "shift_code", "roster_missing"]],
                  on=["emp_id", "week_start"], how="left")
print("Employee-days jin ka roster week missing tha (pichla hafta copy hua):",
      int(grid["roster_missing"].sum()))
print("Employee-days jin ka shift bilkul nahi mila (GEN laga):", int(grid["shift_code"].isna().sum()))
grid["shift_code"] = grid["shift_code"].fillna("GEN")

sh = pd.read_sql(
    "SELECT shift_code, start_time, end_time, crosses_midnight FROM stg_shifts", con)
sh["start_td"] = pd.to_timedelta(sh["start_time"] + ":00")
sh["end_td"] = pd.to_timedelta(sh["end_time"] + ":00")
grid = grid.merge(sh[["shift_code", "start_td", "end_td", "crosses_midnight"]],
                  on="shift_code", how="left")
grid["shift_start"] = grid["work_date"] + grid["start_td"]
grid["shift_end"] = (grid["work_date"] + grid["end_td"]
                     + pd.to_timedelta(grid["crosses_midnight"], unit="D"))
print("Shift time missing rows:", int(grid["shift_start"].isna().sum()))

cur = grid[["emp_id", "work_date", "shift_code"]].rename(
    columns={"work_date": "d", "shift_code": "cur_shift"})
prev = grid[["emp_id", "work_date", "shift_code"]].rename(
    columns={"work_date": "prev_d", "shift_code": "prev_shift"})

pu = pd.read_sql("SELECT emp_id, punch_ts FROM stg_punches", con)
pu["ts"] = pd.to_datetime(pu["punch_ts"])
pu["d"] = pu["ts"].dt.normalize()
pu["hour"] = pu["ts"].dt.hour
pu["prev_d"] = pu["d"] - pd.Timedelta(days=1)
pu = pu.merge(prev, on=["emp_id", "prev_d"], how="left")
pu = pu.merge(cur, on=["emp_id", "d"], how="left")

eve = pu.loc[pu["hour"] >= 18, ["emp_id", "d"]].drop_duplicates()
eve = eve.rename(columns={"d": "prev_d"})
eve["has_eve"] = 1
pu = pu.merge(eve, on=["emp_id", "prev_d"], how="left")
pu["has_eve"] = pu["has_eve"].fillna(0).astype(int) == 1

morning = pu["hour"] < 12
night_morning = (morning & (pu["prev_shift"] == "NIGHT")
                 & ((pu["cur_shift"] != "DAY") | pu["has_eve"]))
pu["shift_date"] = pd.to_datetime(np.where(night_morning, pu["prev_d"], pu["d"]))
print("Night shift punches jo pichli date par gaye:", int(night_morning.sum()))

before_start = morning & (pu["d"] == START) & (pu["cur_shift"] == "NIGHT")
print("31 March ki night shift ke checkouts (ignore kiye):", int(before_start.sum()))
pu = pu[~before_start]

agg = pu.groupby(["emp_id", "shift_date"]).agg(
    punch_count=("ts", "size"), first_ts=("ts", "min"), last_ts=("ts", "max")
).reset_index().rename(columns={"shift_date": "work_date"})

orph = agg.merge(grid[["emp_id", "work_date"]], on=["emp_id", "work_date"],
                 how="left", indicator=True)
orph = orph[orph["_merge"] == "left_only"]
print("Punch-days jo employment ke bahar hain:", len(orph),
      "| un mein 1 Oct:", int((orph["work_date"] == pd.Timestamp("2026-10-01")).sum()))

grid = grid.merge(agg, on=["emp_id", "work_date"], how="left")
grid["punch_count"] = grid["punch_count"].fillna(0).astype(int)

ho = pd.read_sql("SELECT holiday_date, scope FROM stg_holidays", con)
ho["holiday_date"] = pd.to_datetime(ho["holiday_date"])
h_all = ho[ho["scope"] == "ALL"][["holiday_date"]].drop_duplicates()
h_all = h_all.rename(columns={"holiday_date": "work_date"})
h_all["h_all"] = 1
h_pl = ho[ho["scope"] != "ALL"].rename(
    columns={"holiday_date": "work_date", "scope": "plant_code"})
h_pl = h_pl[["work_date", "plant_code"]].drop_duplicates()
h_pl["h_pl"] = 1
grid = grid.merge(h_all, on="work_date", how="left").merge(
    h_pl, on=["work_date", "plant_code"], how="left")
grid["is_holiday"] = grid["h_all"].notna() | grid["h_pl"].notna()

ld = pd.read_sql("SELECT DISTINCT emp_id, leave_date FROM stg_leave_days", con)
ld["work_date"] = pd.to_datetime(ld["leave_date"])
ld["on_leave"] = 1
grid = grid.merge(ld[["emp_id", "work_date", "on_leave"]],
                  on=["emp_id", "work_date"], how="left")

is_sun = grid["work_date"].dt.day_of_week == 6
no_punch = grid["punch_count"] == 0
conds = [
    is_sun & no_punch,
    grid["is_holiday"] & no_punch,
    grid["on_leave"].notna(),
    grid["punch_count"] >= 2,
    grid["punch_count"] == 1,
]
grid["status"] = np.select(
    conds, ["Weekly Off", "Holiday", "On Leave", "Present", "Missing Punch"],
    default="Absent")

pres = grid["status"] == "Present"
non_working = is_sun | grid["is_holiday"]
mins_worked = (grid["last_ts"] - grid["first_ts"]).dt.total_seconds() / 60
late = (grid["first_ts"] - grid["shift_start"]).dt.total_seconds() / 60
early = (grid["shift_end"] - grid["last_ts"]).dt.total_seconds() / 60
after_end = (grid["last_ts"] - grid["shift_end"]).dt.total_seconds() / 60

is_late = pres & ~non_working & (late > 10)
is_early = pres & ~non_working & (early > 10)
ot_minutes = np.where(non_working, mins_worked, np.maximum(after_end, 0))

grid["worked_hours"] = np.where(pres, mins_worked / 60, 0).round(2)
grid["late_minutes"] = np.where(is_late, np.floor(late), 0).astype(int)
grid["early_departure_minutes"] = np.where(is_early, np.floor(early), 0).astype(int)
grid["overtime_hours"] = np.where(pres, np.floor(ot_minutes / 30) * 0.5, 0)

fmt = "%Y-%m-%d %H:%M:%S"
out = pd.DataFrame({
    "emp_id": grid["emp_id"],
    "work_date": grid["work_date"].dt.strftime("%Y-%m-%d"),
    "dept_id": grid["dept_id"],
    "plant_code": grid["plant_code"],
    "shift_code": grid["shift_code"],
    "status": grid["status"],
    "punch_count": grid["punch_count"],
    "check_in": grid["first_ts"].dt.strftime(fmt),
    "check_out": grid["last_ts"].where(grid["punch_count"] >= 2).dt.strftime(fmt),
    "worked_hours": grid["worked_hours"],
    "late_minutes": grid["late_minutes"],
    "early_departure_minutes": grid["early_departure_minutes"],
    "overtime_hours": grid["overtime_hours"],
    "is_late": is_late.astype(int),
    "is_early_departure": is_early.astype(int),
    "is_sunday": is_sun.astype(int),
    "is_holiday": grid["is_holiday"].astype(int),
})
out = out.sort_values(["emp_id", "work_date"])
out.to_sql("stg_attendance_daily", con, if_exists="replace", index=False, chunksize=20000)

print("\nRows:", len(out), "| duplicate emp-date:", int(out.duplicated(["emp_id", "work_date"]).sum()))
print(out["status"].value_counts().to_dict())
print("Negative worked hours:", int((out["worked_hours"] < 0).sum()),
      "| shift > 16h:", int((out["worked_hours"] > 16).sum()),
      "| max worked:", out["worked_hours"].max())
print("On Leave rows jin mein punches bhi hain:",
      int(((out["status"] == "On Leave") & (out["punch_count"] > 0)).sum()))
print("Late rows:", int(out["is_late"].sum()), "| Early rows:", int(out["is_early_departure"].sum()))
print("Computed OT hours by month:")
print(out.groupby(out["work_date"].str[:7])["overtime_hours"].sum())
con.close()