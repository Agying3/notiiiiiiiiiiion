import re, pathlib
js = pathlib.Path(r"REPO_ROOT")
for fn in ["56643-254b7f29e5762127.js","46790-63a147e2eaaf5fc4.js","95209-da5ed98f9c9e58df.js","29013-c582a878291fd719.js"]:
    t=(js/fn).read_text(encoding="utf-8",errors="ignore")
    hits=[m.start() for m in re.finditer(r'(?i)(trial|试用)', t)]
    print(f"== {fn}: {len(hits)} hits")
    for pos in hits[:4]:
        print("   ", re.sub(r"\s+"," ", t[max(0,pos-160):pos+200])[:340])
