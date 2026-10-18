import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")

# 1) 完整 campaign 定义表（name -> days）
i = t.find('campaign:"default",duration:{days:14}')
seg = t[max(0,i-6000): i+9000]
defs = {}
for m in re.finditer(r'\{type:"trial",campaign:"([^"]+)",duration:\{days:(\d+)\},subscriptionTier:"(\w+)"', seg):
    defs[m.group(1)] = (int(m.group(2)), m.group(3))

# 2) 分组表（@497931 附近）
j = 497931
gseg = t[max(0,j-3000): j+1600]
groups = {}
for m in re.finditer(r'([A-Za-z_$][A-Za-z0-9_$]{0,24}):\[("(?:[^"]*)"(?:,"[^"]*")*)\]', gseg):
    names = re.findall(r'"([^"]+)"', m.group(2))
    groups[m.group(1)] = names

print("=== campaign 定义（按天数）")
from collections import defaultdict
byd = defaultdict(list)
for n,(d,tier) in defs.items(): byd[d].append((tier,n))
for d in sorted(byd):
    print(f"\n[{d} 天]  共 {len(byd[d])} 条")
    for tier,n in sorted(byd[d]): print(f"   {tier:<9} {n}")

print("\n\n=== 关键分组：cc 家族 (O9/s)")
for k in ["O9","X0","X0","iM","d","l"]:
    if k in groups: print(f"  {k} ({len(groups[k])}): {groups[k]}")
print("\n=== reverse 家族 (y)")
if "y" in groups:
    for n in groups["y"]:
        d = defs.get(n,("?","?"))[0]
        print(f"   {n:<52} {d}d")
