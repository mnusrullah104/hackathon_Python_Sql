WITH annual AS (
    SELECT e.emp_id, COUNT(DISTINCT f.date_key) AS annual_days_taken
    FROM fact_leave_day f
    JOIN dim_employee e ON e.employee_key = f.employee_key
    WHERE f.leave_type = 'Annual'
    GROUP BY e.emp_id
),
cur AS (
    SELECT emp_id, full_name, dept_id, annual_leave_entitlement
    FROM dim_employee
    WHERE is_current = 1
)
SELECT c.emp_id,
       c.full_name,
       dp.dept_name,
       dp.plant,
       c.annual_leave_entitlement,
       a.annual_days_taken,
       a.annual_days_taken - c.annual_leave_entitlement AS days_over_entitlement
FROM annual a
JOIN cur c ON c.emp_id = a.emp_id
JOIN dim_department dp ON dp.dept_id = c.dept_id
WHERE a.annual_days_taken > c.annual_leave_entitlement
ORDER BY days_over_entitlement DESC, c.emp_id;