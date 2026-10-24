WITH months AS (
    SELECT DISTINCT year_month, month_end
    FROM dim_date
    WHERE full_date BETWEEN '2026-04-01' AND '2026-09-30'
),
emp_month AS (
    SELECT m.year_month, e.emp_id, e.dept_id
    FROM months m
    JOIN dim_employee e
      ON m.month_end BETWEEN e.valid_from AND e.valid_to
    WHERE e.hire_date <= m.month_end
      AND COALESCE(NULLIF(e.separation_date, ''), '9999-12-31') > m.month_end
)
SELECT em.year_month,
       d.plant,
       d.dept_name,
       COUNT(DISTINCT em.emp_id) AS headcount
FROM emp_month em
JOIN dim_department d ON d.dept_id = em.dept_id
GROUP BY em.year_month, d.plant, d.dept_name
ORDER BY em.year_month, d.plant, d.dept_name;