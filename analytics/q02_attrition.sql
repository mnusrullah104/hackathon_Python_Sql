WITH snaps(snap_date) AS (
    VALUES ('2026-03-31'), ('2026-04-30'), ('2026-05-31'), ('2026-06-30'),
           ('2026-07-31'), ('2026-08-31'), ('2026-09-30')
),
months(year_month, open_date, close_date) AS (
    VALUES ('2026-04', '2026-03-31', '2026-04-30'),
           ('2026-05', '2026-04-30', '2026-05-31'),
           ('2026-06', '2026-05-31', '2026-06-30'),
           ('2026-07', '2026-06-30', '2026-07-31'),
           ('2026-08', '2026-07-31', '2026-08-31'),
           ('2026-09', '2026-08-31', '2026-09-30')
),
hc AS (
    SELECT s.snap_date, e.dept_id, COUNT(DISTINCT e.emp_id) AS headcount
    FROM snaps s
    JOIN dim_employee e
      ON s.snap_date BETWEEN e.valid_from AND e.valid_to
    WHERE e.hire_date <= s.snap_date
      AND COALESCE(NULLIF(e.separation_date, ''), '9999-12-31') > s.snap_date
    GROUP BY s.snap_date, e.dept_id
),
seps AS (
    SELECT substr(e.separation_date, 1, 7) AS year_month,
           e.dept_id,
           COUNT(DISTINCT e.emp_id) AS separations
    FROM dim_employee e
    WHERE NULLIF(e.separation_date, '') IS NOT NULL
      AND e.separation_date BETWEEN e.valid_from AND e.valid_to
    GROUP BY substr(e.separation_date, 1, 7), e.dept_id
)
SELECT m.year_month,
       d.plant,
       d.dept_name,
       COALESCE(o.headcount, 0) AS opening_headcount,
       COALESCE(c.headcount, 0) AS closing_headcount,
       COALESCE(s.separations, 0) AS separations,
       ROUND(1.0 * COALESCE(s.separations, 0)
             / NULLIF((COALESCE(o.headcount, 0) + COALESCE(c.headcount, 0)) / 2.0, 0), 4)
           AS attrition_rate
FROM months m
CROSS JOIN dim_department d
LEFT JOIN hc o ON o.snap_date = m.open_date AND o.dept_id = d.dept_id
LEFT JOIN hc c ON c.snap_date = m.close_date AND c.dept_id = d.dept_id
LEFT JOIN seps s ON s.year_month = m.year_month AND s.dept_id = d.dept_id
ORDER BY m.year_month, d.plant, d.dept_name;