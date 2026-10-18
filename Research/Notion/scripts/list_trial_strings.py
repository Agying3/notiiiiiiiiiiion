import re, pathlib, collections
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 找出所有含 trial 的字符串常量
cands = collections.Counter(re.findall(r'"([A-Za-z0-9_\-\.]*trial[A-Za-z0-9_\-\.]*)"', t, re.I))
for k,v in cands.most_common(60): print(f"{v:>3}  {k}")
