import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = t.find('let n="default",r=["samsung_preload_onboarding_flow"')
seg = t[i:i+3000]
print(re.sub(r"\s+"," ", seg)[:2800])
