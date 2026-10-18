import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = t.find("281708).My")
print("idx", i)
print(re.sub(r"\s+"," ", t[max(0,i-5200):i+200])[:5400])
