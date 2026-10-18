import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 试用相关 UI 组件清单（从 module registry 提取）
names = re.findall(r'"([A-Za-z0-9_\-]*(?:Trial|trial)[A-Za-z0-9_\-]*)"', t)
from collections import Counter
for k,v in Counter(names).most_common(40): print(f"{v:>3}  {k}")
