import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["PerfmarkTrialIneligibleToast","start_business_trial","start_trial","request_trial","trial_source","businessTrialsActions"]:
    ms=list(re.finditer(re.escape(k), t))
    print(f"\n===== {k} hits={len(ms)}")
    for m in ms[:2]:
        s=max(0,m.start()-350); e=min(len(t), m.end()+450)
        print("---", re.sub(r"\s+"," ", t[s:e])[:760])
