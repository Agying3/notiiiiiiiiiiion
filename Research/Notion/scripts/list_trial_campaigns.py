import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = t.find('campaign:"perfmark"')
seg = t[i: i+5000]
# 只打印 business 相关
for m in re.finditer(r'\{type:"trial",campaign:"([^"]+)",duration:\{days:(\d+)\},subscriptionTier:"(\w+)"', seg):
    print(f'{m.group(2):>3}d  {m.group(3):<9} {m.group(1)}')
