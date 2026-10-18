import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["startup-onboarding-survey","reimagined-startup-onboarding-survey","startup_trial_onboarding_flow"]:
    for m in list(re.finditer(re.escape(k), t))[:2]:
        s=max(0,m.start()-400); e=min(len(t), m.end()+400)
        print(f"\n=== {k}")
        print(re.sub(r"\s+"," ", t[s:e])[:780])
