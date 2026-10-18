import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 全部 campaign 名（大列表）
i = t.find('"dev_only_45d_reverse"')
seg = t[max(0,i-4000): i+800]
names = re.findall(r'"([a-z0-9_]{4,60})"', seg)
seen=[]
for n in names:
    if n not in seen and any(x in n for x in ["business","trial","reverse","creator","admin","startup","hackathon","recruiting","workshops","dev_only","commercial","smb","midmarket","enterprise"]):
        seen.append(n)
print(f"非 september 家族的全部 campaign 名（{len(seen)} 条）：")
for n in seen: print("  ", n)
