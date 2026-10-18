import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["spaceIntent","workspaceIntent","planIntent","intent:","useCase","industry","teamFunction"]:
    ms=list(re.finditer(re.escape(k), t))
    print(f"== {k} hits={len(ms)}")
    for m in ms[:2]:
        s=max(0,m.start()-230); e=min(len(t), m.end()+300)
        print("   ", re.sub(r"\s+"," ", t[s:e])[:520])
