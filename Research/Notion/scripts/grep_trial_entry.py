import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 找 sidebar trial / upgrade trial entry 的相邻上下文
for k in ["SidebarTrialButton","SidebarTrial","trial_home"]:
    for m in list(re.finditer(re.escape(k), t))[:1]:
        s=max(0,m.start()-120); e=min(len(t),m.end()+120)
        print(f"[{k}]", re.sub(r"\s+"," ", t[s:e])[:240])
# 找是否可从 settings 触发试用
for k in ["startTrial","beginTrial","claimTrial","activateTrial","trial.start","start-trial"]:
    n=len(re.findall(re.escape(k), t, re.I))
    print(f"{k}: {n}")
