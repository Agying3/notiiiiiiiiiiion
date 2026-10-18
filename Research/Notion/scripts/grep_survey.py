import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 找问卷选项
for k in ["What brings you", "brings you to Notion", "personal_use", "school", "work_use", "useCase", "occupation"]:
    ms = list(re.finditer(k, t, re.I))
    print(f"\n===== {k}  hits={len(ms)}")
    for m in ms[:3]:
        s=max(0,m.start()-350); e=min(len(t), m.end()+450)
        print("---", re.sub(r"\s+"," ", t[s:e])[:700])
