import re, pathlib
js = pathlib.Path(r"REPO_ROOT")
for fn in ["8563-9e3514d19f7f9efe.js","72240-045bfff3440653a4.js","ClientFramework-0694bcdd87fcdc47.js"]:
    t=(js/fn).read_text(encoding="utf-8",errors="ignore")
    print("="*20, fn, len(t))
    for k in ["quota","rateLimit"]:
        for m in list(re.finditer(k,t,re.I))[:3]:
            s=max(0,m.start()-200); e=min(len(t),m.end()+260)
            print(f"-- {k}:", re.sub(r"\s+"," ", t[s:e])[:460])
