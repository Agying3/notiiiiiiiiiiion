import re, json, pathlib
from curl_cffi import requests as creq

OUT = pathlib.Path(r"REPO_ROOT")
JS  = OUT / "js"; JS.mkdir(exist_ok=True)

html = (OUT / "page-signup-so.html").read_text(encoding="utf-8", errors="ignore")
srcs = [f"https://app.notion.com{s}" if s.startswith("/") else s
        for s in re.findall(r'src="([^"]+\.js[^"]*)"', html)]
srcs = [s for s in dict.fromkeys(srcs) if "notion" in s]

sess = creq.Session(impersonate="chrome")
found = {}
for u in srcs:
    fn = JS / u.split("/")[-1]
    if not fn.exists():
        try:
            r = sess.get(u, timeout=40)
            fn.write_text(r.text, encoding="utf-8", errors="ignore")
        except Exception as e:
            print("ERR", u, repr(e)[:120]); continue
    txt = fn.read_text(encoding="utf-8", errors="ignore")
    eps = set(re.findall(r'["\'](/api/v3/[A-Za-z0-9_\-/]+)["\']', txt))
    eps |= set(re.findall(r'["\']([A-Za-z]+[A-Za-z0-9]*Api)["\']', txt))
    if eps:
        found[u.split("/")[-1]] = sorted(eps)
    print(f"{u.split('/')[-1]:42s} {len(txt):>9d} bytes  eps={len(eps)}")

(OUT / "endpoints-from-js.json").write_text(json.dumps(found, indent=2, ensure_ascii=False), encoding="utf-8")
allv3 = sorted({e for v in found.values() for e in v if e.startswith("/api/v3/")})
print("\n=== unique /api/v3 endpoints:", len(allv3))
for e in allv3: print(" ", e)
