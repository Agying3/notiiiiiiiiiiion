import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["How did you hear","hear about Notion","What kind of work","what kind of work","describe yourself","Which best describes"]:
    ms=list(re.finditer(re.escape(k), t, re.I))
    print(f"\n== {k} hits={len(ms)}")
    for m in ms[:2]:
        s=max(0,m.start()-500); e=min(len(t), m.end()+500)
        print("  ", re.sub(r"\s+"," ", t[s:e])[:900])
