import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["september_2026_auto_stacked_business_trial_14d","auto_stacked","_auto_"]:
    ms=[m.start() for m in re.finditer(re.escape(k), t)]
    print(f"\n### {k} -> {len(ms)} 处: {ms[:8]}")
# 找 auto 的定义上下文（第一次出现附近是否有 autoStart/autoConvert 语义）
i = t.find("september_2026_auto_stacked_business_trial_14d")
print("\n--- 上下文")
print(re.sub(r"\s+"," ", t[max(0,i-500):i+300])[:760])
