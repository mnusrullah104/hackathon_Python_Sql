SELECT e.emp_id,
       e.full_name,
       dp.dept_name,
       dp.plant,
       e.separation_date,
       COUNT(DISTINCT p.payroll_month) AS months_paid_after,
       MIN(p.payroll_month) AS first_month_after,
       MAX(p.payroll_month) AS last_month_after,
       ROUND(SUM(p.amount), 2) AS earnings_paid_after
FROM fact_payroll_line p
JOIN dim_employee e ON e.employee_key = p.employee_key
JOIN dim_department dp ON dp.dept_id = e.dept_id
WHERE p.component_type = 'EARNING'
  AND NULLIF(e.separation_date, '') IS NOT NULL
  AND p.payroll_month > substr(e.separation_date, 1, 7)
GROUP BY e.emp_id, e.full_name, dp.dept_name, dp.plant, e.separation_date
ORDER BY earnings_paid_after DESC, e.emp_id;