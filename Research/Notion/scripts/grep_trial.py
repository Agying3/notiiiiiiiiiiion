import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
print("len", len(t))
for k in ["businessTrial", "trialEligib", "trialUpsell"]:
    print("\n" + "="*34, k)
    for m in list(re.finditer(k, t, re.I))[:8]:
        s=max(0,m.start()-260); e=min(len(t), m.end()+320)
        print("---", re.sub(r"\s+"," ", t[s:e])[:580])
