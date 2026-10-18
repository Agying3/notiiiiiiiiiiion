import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 281708 模块里的 My 导出
i = t.find("281708(e,t,a)")
seg = t[i:i+40000]
for m in re.finditer(r'a\.d\(t,\{[^}]{0,4000}\}\)', seg):
    s = m.group(0)
    if 'My' in s:
        print(re.sub(r"\s+"," ", s)[:3000])
        break
