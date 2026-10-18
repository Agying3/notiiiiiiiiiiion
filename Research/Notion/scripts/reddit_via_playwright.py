import json, pathlib, random, re, sys
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(r"REPO_ROOT"); OUT = ROOT/"research"/"notion"/"captures"/"community"
OUT.mkdir(parents=True, exist_ok=True)
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(4321)
results={}
with sync_playwright() as p:
    for attempt in range(6):
        h,po,u,pw = random.choice(lines).split(":",3)
        px={"server":f"http://{h}:{po}","username":u,"password":pw}
        b=None
        try:
            b=p.chromium.launch(headless=True, proxy=px, args=["--no-sandbox"])
            pg=b.new_page(locale="en-US")
            pg.goto("https://www.reddit.com/r/Notion/search/?q=AI+limit&restrict_sr=1&sort=relevance&t=year",
                    wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(6000)
            txt = pg.inner_text("body")
            if "Sorry" in txt[:400] or len(txt) < 500:
                print(f"#{attempt} blocked len={len(txt)}"); b.close(); b=None; continue
            (OUT/"reddit-notion-search.txt").write_text(txt, encoding="utf-8")
            print(f"#{attempt} OK proxy={h}:{po} len={len(txt)}")
            print(txt[:1800])
            results["ok"]=True
            b.close(); b=None
            break
        except Exception as e:
            print(f"#{attempt} ERR {repr(e)[:90]}")
            if b: b.close()
print(json.dumps(results))
