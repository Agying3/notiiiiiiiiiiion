import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")

print("=== 当前在推的一波（september_2026）")
print("  reverse 只有 14d 版：", "september_2026_business_reverse_14d" in t)
print("  存在 1m 版 reverse 吗：", "september_2026_business_reverse_1m" in t)
print("  1m 版只有 stacked：", "september_2026_stacked_business_trial_1m" in t)

print("\n=== block_limit 那条（撞 1000 block 上限触发的）")
i = t.find("business_cc_14d_block_limit")
print(" ", re.sub(r"\s+"," ", t[max(0,i-260):i+180])[:420])

print("\n=== 统计：14d vs 30d 谁多")
allc = re.findall(r'\{type:"trial",campaign:"([^"]+)",duration:\{days:(\d+)\}', t)
from collections import Counter
c = Counter(d for _,d in allc)
print(" ", dict(c))
