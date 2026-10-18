import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 找 281708 模块（My 导出）—— 可能含默认 campaign 选择
i = t.find("281708(e,t,a)")
print("mod idx", i)
if i>0: print(re.sub(r"\s+"," ", t[i:i+2600])[:2600])
