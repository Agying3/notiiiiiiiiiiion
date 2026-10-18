import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["perfmark","eligib","Eligib","eduVerified","isStudent","schoolEmail","academicEmail"]:
    ms=list(re.finditer(re.escape(k), t, re.I))
    print(f"\n===== {k} hits={len(ms)}")
    for m in ms[:3]:
        s=max(0,m.start()-300); e=min(len(t), m.end()+380)
        print("---", re.sub(r"\s+"," ", t[s:e])[:660])
