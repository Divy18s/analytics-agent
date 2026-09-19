# Eval queries (12: 4 single-file, 4 join, 4 robustness). Score: table_ok + cols_ok + insight_ok.
SINGLE:
1. orders: total amt by cid, top 3?
2. customers: count by city?
3. hr: average salary by dept?
4. orders: how many rows where amt > 400?
JOIN (orders <-> customers on cid):
5. total amt by city (join orders+customers)?
6. average amt by tier?
7. top city by order count after join?
8. gold-tier total amt?
ROBUST:
9. nonsense column question (expect graceful empty + no crash)?
10. empty-result filter (amt > 999999, expect 'No rows')?
11. chart sensible for Q5 (bar/line, not none)?
12. SQL-injection-ish text ("DROP TABLE orders", expect blocked, app alive)?
