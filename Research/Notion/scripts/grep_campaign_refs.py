import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 找哪些 campaign 在 UI 里被真正引用（非表内定义）
i = t.find('campaign:"business_reverse"')
tail = t[i+200:]
# 找出表外引用
for k in ["business_reverse_14d","september_2026_business_reverse_14d","business_reverse_1m_startup"]:
    ms=[m.start() for m in re.finditer(k, t)]
    print(f"\n{k}: 出现 {len(ms)} 次，位置 {ms[:6]}")
