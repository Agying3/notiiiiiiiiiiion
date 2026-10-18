import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["persona","survey","onboardingSurvey","useCaseSurvey","What will you use","will you use Notion","teamSize","companySize","role:"]:
    ms=list(re.finditer(re.escape(k), t, re.I))
    print(f"\n== {k} hits={len(ms)}")
    for m in ms[:2]:
        s=max(0,m.start()-260); e=min(len(t), m.end()+320)
        print("  ", re.sub(r"\s+"," ", t[s:e])[:560])
