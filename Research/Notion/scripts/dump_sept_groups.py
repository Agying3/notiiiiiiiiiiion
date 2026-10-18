import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for pos in [493398, 496750, 497470]:
    print(f"\n{'='*25} @{pos}")
    print(re.sub(r"\s+"," ", t[max(0,pos-1100):pos+700])[:1700])
