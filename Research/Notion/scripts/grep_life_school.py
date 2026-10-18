import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = t.find('"life","school","work","personal"')
print("idx", i)
print(re.sub(r"\s+"," ", t[max(0,i-2600):i+400]))
