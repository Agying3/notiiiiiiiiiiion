import re, pathlib, collections
js = pathlib.Path(r"REPO_ROOT")
pat = re.compile(r'"([A-Za-z0-9_]*(?:[Mm]odel[Pp]icker|ModelSelector|model_selection|modelPicker|PremiumModel|modelPicker)[A-Za-z0-9_]*)"')
for f in sorted(js.glob("*.js")):
    t = f.read_text(encoding="utf-8", errors="ignore")
    hits = collections.Counter(pat.findall(t))
    if hits:
        print(f"== {f.name}")
        for k,v in hits.most_common(20): print(f"  {v:>2}  {k}")
