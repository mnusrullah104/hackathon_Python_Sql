WITH months AS (
    SELECT DISTINCT year_month, month_end
    FROM dim_date
    WHERE full_date BETWEEN '2026-04-01' AND '2026-09-30'
),
comp AS (
    SELECT e.emp_id, d.year_month, SUM(f.overtime_hours) AS comp_ot
    FROM fact_attendance_daily f
    JOIN dim_employee e ON e.employee_key = f.employee_key
    JOIN dim_date d ON d.date_key = f.date_key
    GROUP BY e.emp_id, d.year_month
),
appr AS (
    SELECT e.emp_id, d.year_month, SUM(o.approved_hours) AS appr_ot
    FROM fact_overtime_approved o
    JOIN dim_employee e ON e.employee_key = o.employee_key
    JOIN dim_date d ON d.date_key = o.date_key
    WHERE o.status = 'Approved'
    GROUP BY e.emp_id, d.year_month
),
paid AS (
    SELECT e.emp_id, p.payroll_month AS year_month, SUM(p.units) AS paid_ot
    FROM fact_payroll_line p
    JOIN dim_employee e ON e.employee_key = p.employee_key
    WHERE p.component = 'OVERTIME'
    GROUP BY e.emp_id, p.payroll_month
),
keys AS (
    SELECT emp_id, year_month FROM comp
    UNION SELECT emp_id, year_month FROM appr
    UNION SELECT emp_id, year_month FROM paid
),
emp_month AS (
    SELECT k.emp_id, k.year_month, e.dept_id
    FROM keys k
    JOIN months m ON m.year_month = k.year_month
    JOIN dim_employee e
      ON e.emp_id = k.emp_id
     AND MIN(m.month_end, COALESCE(NULLIF(e.separation_date, ''), '9999-12-31'))
         BETWEEN e.valid_from AND e.valid_to
)
SELECT em.year_month,
       dp.plant,
       dp.dept_name,
       ROUND(SUM(COALESCE(c.comp_ot, 0)), 1) AS computed_ot_hours,
       ROUND(SUM(COALESCE(a.appr_ot, 0)), 1) AS approved_ot_hours,
       ROUND(SUM(COALESCE(p.paid_ot, 0)), 1) AS paid_ot_hours,
       ROUND(100.0 * (SUM(COALESCE(p.paid_ot, 0)) - SUM(COALESCE(c.comp_ot, 0)))
             / NULLIF(SUM(COALESCE(c.comp_ot, 0)), 0), 1) AS paid_vs_computed_pct
FROM emp_month em
LEFT JOIN comp c ON c.emp_id = em.emp_id AND c.year_month = em.year_month
LEFT JOIN appr a ON a.emp_id = em.emp_id AND a.year_month = em.year_month
LEFT JOIN paid p ON p.emp_id = em.emp_id AND p.year_month = em.year_month
JOIN dim_department dp ON dp.dept_id = em.dept_id
GROUP BY em.year_month, dp.plant, dp.dept_name
ORDER BY em.year_month, dp.plant, dp.dept_name;