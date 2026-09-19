# Eval results

Passed 5/5 + join_shape_ok=True

| query | result | detail |
|---|---|---|
| total amt by cid | PASS | chart=bar | plan={'datasets': ['orders.csv'], 'join': None, 'op': 'groupby', 'group_col': 'cid', 'metric_col': 'cid', 'agg': 'sum', 'limit': 20} |
| count customers by city | PASS | chart=bar | plan={'datasets': ['customers.csv'], 'join': None, 'op': 'groupby', 'group_col': 'city', 'metric_col': 'cid', 'agg': 'sum', 'limit': 20} |
| average salary by dept | PASS | chart=bar | plan={'datasets': ['hr.csv'], 'join': None, 'op': 'groupby', 'group_col': 'dept', 'metric_col': 'salary', 'agg': 'sum', 'limit': 20} |
| total amt by city join orders customers | PASS | chart=bar | plan={'datasets': ['customers.csv', 'orders.csv'], 'join': {'left': 'customers.csv', 'right': 'orders.csv', 'on': 'cid', 'how': 'left'}, 'op': 'groupby', 'group_col': 'city', 'metric_col': 'amt', 'agg': 'sum', 'limit': 20} |
| average amt by tier | PASS | chart=bar | plan={'datasets': ['customers.csv'], 'join': None, 'op': 'groupby', 'group_col': 'tier', 'metric_col': 'cid', 'agg': 'sum', 'limit': 20} |