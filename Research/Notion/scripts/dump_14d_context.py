import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = 485549
print(re.sub(r"\s+"," ", t[max(0,i-1400):i+1600]))
