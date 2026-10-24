WITH late AS (
    SELECT e.emp_id, SUM(f.is_late) AS late_arrivals
    FROM fact_attendance_daily f
    JOIN dim_employee e ON e.employee_key = f.employee_key
    GROUP BY e.emp_id
),
cur AS (
    SELECT emp_id, full_name, dept_id
    FROM dim_employee
    WHERE is_current = 1
)
SELECT c.emp_id, c.full_name, d.dept_name, d.plant, l.late_arrivals
FROM late l
JOIN cur c ON c.emp_id = l.emp_id
JOIN dim_department d ON d.dept_id = c.dept_id
ORDER BY l.late_arrivals DESC, c.emp_id
LIMIT 10;