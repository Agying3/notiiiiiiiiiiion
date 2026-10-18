import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = t.find('campaign:"perfmark"')
seg = t[max(0,i-3000): i+6000]
# 全部 trial 条目
rows=[]
for m in re.finditer(r'\{type:"trial",campaign:"([^"]+)",duration:\{days:(\d+)\},subscriptionTier:"(\w+)",products:\[([^\]]+)\]', seg):
    rows.append((int(m.group(2)), m.group(3), m.group(1), m.group(4)))
print("trial 条目总数:", len(rows))
from collections import Counter
c=Counter((r[0], r[1]) for r in rows)
print("\n按 (天数, 套餐) 统计:")
for (d,tier),v in sorted(c.items()): print(f"  {d:>3}d {tier:<9} {v} 条")
print("\n14 天 business 的全部 campaign:")
for d,tier,name,prod in rows:
    if d==14 and tier=="business": print("  ", name)
