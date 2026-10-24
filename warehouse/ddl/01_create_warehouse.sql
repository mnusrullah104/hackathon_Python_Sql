PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS fact_payroll_line;
DROP TABLE IF EXISTS fact_overtime_approved;
DROP TABLE IF EXISTS fact_leave_day;
DROP TABLE IF EXISTS fact_attendance_daily;
DROP TABLE IF EXISTS dim_employee;
DROP TABLE IF EXISTS dim_shift;
DROP TABLE IF EXISTS dim_department;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_date (
    date_key     INTEGER PRIMARY KEY,
    full_date    TEXT NOT NULL UNIQUE,
    year         INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    month_name   TEXT NOT NULL,
    year_month   TEXT NOT NULL,
    day          INTEGER NOT NULL,
    day_of_week  INTEGER NOT NULL,
    day_name     TEXT NOT NULL,
    is_sunday    INTEGER NOT NULL,
    week_start   TEXT NOT NULL,
    month_end    TEXT NOT NULL
);

CREATE TABLE dim_department (
    dept_id        TEXT PRIMARY KEY,
    dept_name      TEXT NOT NULL,
    plant          TEXT NOT NULL,
    plant_code     TEXT NOT NULL,
    cost_center    TEXT,
    previous_name  TEXT,
    renamed_on     TEXT
);

CREATE TABLE dim_shift (
    shift_code        TEXT PRIMARY KEY,
    shift_name        TEXT NOT NULL,
    start_time        TEXT NOT NULL,
    end_time          TEXT NOT NULL,
    crosses_midnight  INTEGER NOT NULL,
    grace_minutes     INTEGER NOT NULL
);

CREATE TABLE dim_employee (
    employee_key              INTEGER PRIMARY KEY,
    emp_id                    TEXT NOT NULL,
    full_name                 TEXT,
    gender                    TEXT,
    hire_date                 TEXT,
    separation_date           TEXT,
    employment_type           TEXT,
    emp_status                TEXT,
    annual_leave_entitlement  INTEGER,
    plant                     TEXT,
    dept_id                   TEXT NOT NULL REFERENCES dim_department (dept_id),
    designation               TEXT,
    grade                     TEXT,
    basic_salary              REAL,
    change_reason             TEXT,
    valid_from                TEXT NOT NULL,
    valid_to                  TEXT NOT NULL,
    is_current                INTEGER NOT NULL,
    UNIQUE (emp_id, valid_from),
    CHECK (valid_from <= valid_to)
);

CREATE TABLE fact_attendance_daily (
    attendance_id            INTEGER PRIMARY KEY,
    employee_key             INTEGER NOT NULL REFERENCES dim_employee (employee_key),
    date_key                 INTEGER NOT NULL REFERENCES dim_date (date_key),
    dept_id                  TEXT NOT NULL REFERENCES dim_department (dept_id),
    shift_code               TEXT NOT NULL REFERENCES dim_shift (shift_code),
    status                   TEXT NOT NULL CHECK (status IN
        ('Present', 'Absent', 'On Leave', 'Holiday', 'Weekly Off', 'Missing Punch')),
    punch_count              INTEGER NOT NULL,
    check_in                 TEXT,
    check_out                TEXT,
    worked_hours             REAL NOT NULL,
    late_minutes             INTEGER NOT NULL,
    early_departure_minutes  INTEGER NOT NULL,
    overtime_hours           REAL NOT NULL,
    is_late                  INTEGER NOT NULL,
    is_early_departure       INTEGER NOT NULL,
    is_sunday                INTEGER NOT NULL,
    is_holiday               INTEGER NOT NULL,
    UNIQUE (employee_key, date_key)
);

CREATE TABLE fact_leave_day (
    leave_day_id  INTEGER PRIMARY KEY,
    request_id    TEXT NOT NULL,
    employee_key  INTEGER NOT NULL REFERENCES dim_employee (employee_key),
    date_key      INTEGER NOT NULL REFERENCES dim_date (date_key),
    leave_type    TEXT NOT NULL CHECK (leave_type IN ('Annual', 'Casual', 'Sick')),
    UNIQUE (request_id, date_key)
);

CREATE TABLE fact_overtime_approved (
    request_id       TEXT PRIMARY KEY,
    employee_key     INTEGER NOT NULL REFERENCES dim_employee (employee_key),
    date_key         INTEGER NOT NULL REFERENCES dim_date (date_key),
    requested_hours  REAL,
    approved_hours   REAL,
    status           TEXT NOT NULL CHECK (status IN ('Approved', 'Rejected', 'Pending')),
    approver_id      TEXT,
    requested_at     TEXT
);

CREATE TABLE fact_payroll_line (
    line_id         TEXT PRIMARY KEY,
    payroll_month   TEXT NOT NULL,
    employee_key    INTEGER NOT NULL REFERENCES dim_employee (employee_key),
    date_key        INTEGER NOT NULL REFERENCES dim_date (date_key),
    component       TEXT NOT NULL CHECK (component IN
        ('BASIC', 'HOUSE_RENT', 'MEDICAL', 'CONVEYANCE', 'OVERTIME',
         'INCOME_TAX', 'EOBI', 'ABSENCE_DEDUCTION', 'LOAN_INSTALLMENT')),
    component_type  TEXT NOT NULL CHECK (component_type IN ('EARNING', 'DEDUCTION')),
    units           REAL,
    amount          REAL
);