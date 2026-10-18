import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for pos in [488708, 493273, 497931, 498469]:
    print(f"\n===== @{pos}")
    print(re.sub(r"\s+"," ", t[max(0,pos-700):pos+700])[:1200])
