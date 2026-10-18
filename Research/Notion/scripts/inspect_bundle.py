import re, pathlib
js = pathlib.Path(r"REPO_ROOT")
for fn, keys in [("app-d0bdcae214317ae6.js", ["aiLimit","aiUsage","rateLimit"]),
                 ("2888-f33f695a245e29db.js", ["allowance","credits"])]:
    t = (js/fn).read_text(encoding="utf-8", errors="ignore")
    print("="*20, fn, len(t))
    for k in keys:
        for m in list(re.finditer(k, t, re.I))[:3]:
            s = max(0, m.start()-220); e = min(len(t), m.end()+320)
            print(f"-- {k}:", re.sub(r"\s+"," ", t[s:e])[:520])
            print()
