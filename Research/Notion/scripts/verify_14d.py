import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")

# 验证：september_2026 家族里 reverse 有哪些时长
sept = sorted(set(re.findall(r'"(september_2026[a-z0-9_]*)"', t)))
print("=== september_2026 家族（当前在推的一波）：")
for s in sept:
    m = re.search(r'campaign:"'+re.escape(s)+r'",duration:\{days:(\d+)\}', t)
    d = m.group(1)+"d" if m else "?"
    print(f"   {d:>5}  {s}")

print("\n=== 是否存在 september_2026_business_reverse_1m ?")
print("  ", "september_2026_business_reverse_1m" in t)

print("\n=== reverse 家族按天数")
for n in sorted(set(re.findall(r'campaign:"([a-z0-9_]*reverse[a-z0-9_]*)"', t))):
    m = re.search(r'campaign:"'+re.escape(n)+r'",duration:\{days:(\d+)\}', t)
    if m: print(f"   {m.group(1):>4}d  {n}")
