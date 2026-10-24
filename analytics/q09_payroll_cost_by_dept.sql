WITH emp_cost AS (
    SELECT p.payroll_month, e.emp_id, e.dept_id,
           SUM(CASE WHEN p.component_type = 'EARNING' THEN p.amount ELSE 0 END) AS cost
    FROM fact_payroll_line p
    JOIN dim_employee e ON e.employee_key = p.employee_key
    GROUP BY p.payroll_month, e.emp_id, e.dept_id
),
dept_month AS (
    SELECT payroll_month, dept_id,
           COUNT(DISTINCT emp_id) AS employees_paid,
           SUM(cost) AS total_cost,
           SUM(cost) / COUNT(DISTINCT emp_id) AS cost_per_employee
    FROM emp_cost
    WHERE cost > 0
    GROUP BY payroll_month, dept_id
),
with_prev AS (
    SELECT dm.*,
           LAG(cost_per_employee) OVER (PARTITION BY dept_id ORDER BY payroll_month) AS prev_cpe
    FROM dept_month dm
)
SELECT w.payroll_month,
       dp.plant,
       dp.dept_name,
       w.employees_paid,
       ROUND(w.total_cost, 2) AS total_cost,
       ROUND(w.cost_per_employee, 2) AS cost_per_employee,
       ROUND(w.prev_cpe, 2) AS prev_month_cost_per_employee,
       ROUND(w.cost_per_employee - w.prev_cpe, 2) AS mom_change,
       ROUND(100.0 * (w.cost_per_employee - w.prev_cpe) / NULLIF(w.prev_cpe, 0), 2) AS mom_change_pct
FROM with_prev w
JOIN dim_department dp ON dp.dept_id = w.dept_id
ORDER BY w.payroll_month, dp.plant, dp.dept_name;