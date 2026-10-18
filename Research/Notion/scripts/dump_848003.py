import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = t.find("848003(e,t,a)")
print("848003 idx", i)
print(re.sub(r"\s+"," ", t[i:i+1800])[:1800])
