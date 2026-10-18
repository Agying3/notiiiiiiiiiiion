import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
print("len", len(t))
for k in ["onboarding", "student", "trial"]:
    print("\n" + "="*30, k)
    for m in list(re.finditer(k, t, re.I))[:6]:
        s=max(0,m.start()-300); e=min(len(t), m.end()+400)
        print("---", re.sub(r"\s+"," ", t[s:e])[:640])
