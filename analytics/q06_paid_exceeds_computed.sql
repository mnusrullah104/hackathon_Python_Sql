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
paid AS (
    SELECT e.emp_id, p.payroll_month AS year_month, SUM(p.units) AS paid_ot
    FROM fact_payroll_line p
    JOIN dim_employee e ON e.employee_key = p.employee_key
    WHERE p.component = 'OVERTIME'
    GROUP BY e.emp_id, p.payroll_month
),
keys AS (
    SELECT emp_id, year_month FROM comp
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
),
monthly AS (
    SELECT em.dept_id, em.year_month,
           SUM(COALESCE(c.comp_ot, 0)) AS comp,
           SUM(COALESCE(p.paid_ot, 0)) AS paid
    FROM emp_month em
    LEFT JOIN comp c ON c.emp_id = em.emp_id AND c.year_month = em.year_month
    LEFT JOIN paid p ON p.emp_id = em.emp_id AND p.year_month = em.year_month
    GROUP BY em.dept_id, em.year_month
)
SELECT dp.plant,
       dp.dept_name,
       ROUND(SUM(m.comp), 1) AS computed_ot_hours,
       ROUND(SUM(m.paid), 1) AS paid_ot_hours,
       ROUND(SUM(m.paid) - SUM(m.comp), 1) AS excess_hours,
       ROUND(100.0 * (SUM(m.paid) - SUM(m.comp)) / NULLIF(SUM(m.comp), 0), 1) AS excess_pct,
       SUM(CASE WHEN m.paid > m.comp * 1.15 THEN 1 ELSE 0 END) AS months_over_15pct
FROM monthly m
JOIN dim_department dp ON dp.dept_id = m.dept_id
GROUP BY dp.dept_id, dp.plant, dp.dept_name
HAVING SUM(m.paid) > 1.15 * SUM(m.comp)
ORDER BY excess_pct DESC;