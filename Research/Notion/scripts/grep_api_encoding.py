import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 已知 v3 接口名在 bundle 里怎么存的？
for k in ["getSpaces","getLoginOptions","getAppConfig","submitTransaction"]:
    ms=list(re.finditer(re.escape(k), t))
    print(f"== {k} hits={len(ms)}")
    for m in ms[:1]:
        s=max(0,m.start()-200); e=min(len(t), m.end()+200)
        print("   ", re.sub(r"\s+"," ", t[s:e])[:400])
# 找 plan/edu 判定
for k in ["educationPlan","edu_plan","spacePlan","planType","EduBackToSchool","studentVerification","verifyStudent"]:
    ms=list(re.finditer(re.escape(k), t, re.I))
    print(f"\n-- {k} hits={len(ms)}")
    for m in ms[:1]:
        s=max(0,m.start()-250); e=min(len(t), m.end()+300)
        print("   ", re.sub(r"\s+"," ", t[s:e])[:520])
