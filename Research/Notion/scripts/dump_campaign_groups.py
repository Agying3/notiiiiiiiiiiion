import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = 497931
print(re.sub(r"\s+"," ", t[max(0,i-2600):i-100])[:2600])
