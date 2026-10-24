SELECT d.year_month,
       p.plant,
       SUM(CASE WHEN f.status = 'Absent' THEN 1 ELSE 0 END) AS absent_days,
       SUM(CASE WHEN f.status IN ('Present', 'Absent', 'Missing Punch') THEN 1 ELSE 0 END)
           AS scheduled_working_days,
       ROUND(1.0 * SUM(CASE WHEN f.status = 'Absent' THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN f.status IN ('Present', 'Absent', 'Missing Punch')
                               THEN 1 ELSE 0 END), 0), 4) AS absenteeism_rate
FROM fact_attendance_daily f
JOIN dim_date d ON d.date_key = f.date_key
JOIN dim_department p ON p.dept_id = f.dept_id
GROUP BY d.year_month, p.plant
ORDER BY d.year_month, p.plant;