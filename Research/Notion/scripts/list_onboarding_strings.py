import re, pathlib, collections
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 找所有以 setOnboarding / onboarding 动作名 的字符串
c = collections.Counter(re.findall(r'"([A-Za-z0-9_\-]*(?:[Oo]nboarding|persona|quest)[A-Za-z0-9_\-]*)"', t))
for k,v in c.most_common(70): print(f"{v:>3}  {k}")
