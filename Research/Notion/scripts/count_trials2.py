import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = t.find('campaign:"perfmark"')
seg = t[max(0,i-3000): i+6000]
rows=[]
for m in re.finditer(r'\{type:"trial",campaign:"([^"]+)",duration:\{days:(\d+)\},subscriptionTier:"(\w+)",products:\[([^\]]+)\]([^}]*)\}', seg):
    rows.append((int(m.group(2)), m.group(3), m.group(1), m.group(4), m.group(5).strip()))
print("90/180/365 天:")
for d,tier,name,prod,extra in rows:
    if d>=90: print(f"  {d:>3}d {tier:<9} {name:52s} {extra[:80]}")
print("\n30 天 business:")
for d,tier,name,prod,extra in rows:
    if d==30 and tier=="business": print("  ", name)
