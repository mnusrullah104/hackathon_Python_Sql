# CFO Findings: Indus Weave Textiles (Apr-Sep 2026)

Overtime cost isliye barh raha hai ke payroll approved OT requests ko bina punches se check kiye pay karta hai.
Punches se nikla OT 6 mahine mein lagbhag flat hai (6,067 se 6,472 ghante mahina).

## Finding 1: Faisalabad Stitching mein paid OT punches se 56% zyada
Faisalabad Plant ke Stitching department mein 6 mahine ka paid OT 7,659 ghante raha, jabke biometric punches se
sirf 4,906 ghante banta hai (+2,753 ghante, +56.1%). Paid OT 5 mahine mein computed se 15% se upar raha.
Koi aur department is threshold par nahi aaya.
Evidence: `analytics/q06_paid_exceeds_computed.sql`, `analytics/q05_overtime_comparison.sql`.
Action: OT payment ko punch-verified hours se jodein (approved aur computed mein se kam wali raqam pay ho),
aur Stitching ke OT approvers ka audit karein.

## Finding 2: Ghost pay, jahan kaam ya employment nahi, wahan bhi tankhwah
58 employee-months mein tankhwah gayi jab ke attendance aur leave dono zero thi (misaal: E10399, 85,925 PKR, April).
Alag se, 5 employees ko separation ke baad bhi tankhwah milti rahi, kul 1,948,000 PKR
(sab se bara E10471 Umair Baloch, 5 mahine, 660,000 PKR).
Evidence: `analytics/q07_paid_zero_attendance.sql`, `analytics/q08_paid_after_separation.sql`.
Action: payroll release se pehle HR ki separation list aur attendance se automatic match karein,
aur in 5 employees ki raqam recover karne ka process shuru karein.

## Finding 3: 20 employees ne annual leave entitlement se zyada leave li
20 employees ne 6 mahine mein apni 14 din ki annual entitlement se zyada approved leave li.
Sab se zyada E10770 Danish Iqbal (Spinning, Korangi) ne 28 din li, yaani 14 din zyada.
Evidence: `analytics/q10_leave_overuse.sql`.
Action: leave approval step mein balance check lazmi karein, aur zyada li hui leave ko unpaid ya adjust karein.