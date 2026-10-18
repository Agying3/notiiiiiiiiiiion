import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 找默认试用/默认季军逻辑
for k in ["defaultTrial","DEFAULT_TRIAL","defaultCampaign","trialDuration","businessTrialDays","days:14","14}"]:
    ms=list(re.finditer(re.escape(k), t))
    if ms: print(f"{k}: {len(ms)}")
# 找 business_reverse / business_cc 首次出现处的默认配置
i=t.find('campaign:"business_reverse"')
print("\n--- business_reverse 上下文")
print(re.sub(r"\s+"," ", t[max(0,i-900):i+400])[:1200])
