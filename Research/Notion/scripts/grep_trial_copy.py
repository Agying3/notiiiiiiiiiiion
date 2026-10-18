import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["14-day","14 day","days left","trial ends","Trial ends","free trial","Free trial","days remaining","Business trial"]:
    ms=list(re.finditer(re.escape(k), t))
    print(f"== {k}: {len(ms)}")
    for m in ms[:2]:
        print("   ", re.sub(r"\s+"," ", t[max(0,m.start()-180):m.end()+220])[:380])
