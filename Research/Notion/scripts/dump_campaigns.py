import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = t.find('campaign:"perfmark"')
s = t.rfind("let", 0, i-2000)
seg = t[max(0,i-2200): i+2600]
print(re.sub(r"\},\{", "},\n{", seg))
