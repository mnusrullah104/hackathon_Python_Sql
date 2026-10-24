WITH paid AS (
    SELECT e.emp_id, p.payroll_month AS year_month,
           ROUND(SUM(CASE WHEN p.component_type = 'EARNING' THEN p.amount ELSE 0 END), 2) AS earnings
    FROM fact_payroll_line p
    JOIN dim_employee e ON e.employee_key = p.employee_key
    GROUP BY e.emp_id, p.payroll_month
    HAVING SUM(CASE WHEN p.component_type = 'EARNING' THEN p.amount ELSE 0 END) > 0
),
att AS (
    SELECT e.emp_id, d.year_month,
           SUM(CASE WHEN f.status IN ('Present', 'Missing Punch') THEN 1 ELSE 0 END) AS attendance_days,
           SUM(CASE WHEN f.status = 'On Leave' THEN 1 ELSE 0 END) AS leave_days
    FROM fact_attendance_daily f
    JOIN dim_employee e ON e.employee_key = f.employee_key
    JOIN dim_date d ON d.date_key = f.date_key
    GROUP BY e.emp_id, d.year_month
),
cur AS (
    SELECT emp_id, full_name, dept_id, separation_date
    FROM dim_employee
    WHERE is_current = 1
)
SELECT p.year_month,
       p.emp_id,
       c.full_name,
       dp.dept_name,
       dp.plant,
       NULLIF(c.separation_date, '') AS separation_date,
       p.earnings,
       COALESCE(a.attendance_days, 0) AS attendance_days,
       COALESCE(a.leave_days, 0) AS leave_days
FROM paid p
LEFT JOIN att a ON a.emp_id = p.emp_id AND a.year_month = p.year_month
JOIN cur c ON c.emp_id = p.emp_id
JOIN dim_department dp ON dp.dept_id = c.dept_id
WHERE COALESCE(a.attendance_days, 0) = 0
ORDER BY p.year_month, p.emp_id;