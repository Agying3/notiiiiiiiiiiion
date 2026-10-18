# 深挖注册页卡在 loading 的原因：Statsig 外部域是否可达 + 页面内部状态
import json, pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(r"REPO_ROOT")
res = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = b.new_context(locale="en-US")
    pg = ctx.new_page()
    pg.on("request", lambda r: res.append({"phase": "req", "url": r.url[:180], "method": r.method}))
    pg.on("requestfinished", lambda r: res.append({"phase": "done", "url": r.url[:180]}))
    pg.on("requestfailed", lambda r: res.append({"phase": "FAIL", "url": r.url[:180], "err": r.failure}))
    pg.goto("https://app.notion.com/signup", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(20000)

    state = pg.evaluate("""() => {
        const keys = Object.keys(window).filter(k => /notion|statsig|__|redux|store/i.test(k)).slice(0, 60);
        return {
            readyState: document.readyState,
            htmlLen: document.documentElement.outerHTML.length,
            bodyChildren: [...document.body.children].map(e => e.tagName + '#' + (e.id||'') + '.' + (e.className||'').toString().slice(0, 40)).slice(0,15),
            root: (document.getElementById('root')||{}).innerHTML?.length ?? null,
            keys: keys,
            statsig: typeof window.statsig,
            errors: (window.__errors__||[]).slice(0,5),
        };
    }""")
    print(json.dumps(state, ensure_ascii=False, indent=2)[:2500])

    ext = [r for r in res if r["phase"] in ("done", "FAIL") and "notion" not in r["url"]]
    print("\n--- 外部域请求:", len(ext))
    for e in ext[:40]:
        print(" ", e["phase"], e["url"][:140])

    pend = [r for r in res if r["phase"] == "req"] 
    done = {r["url"] for r in res if r["phase"] == "done"}
    print("\n--- 未完成的请求:", len([r for r in pend if r["url"] not in done]))
    for r in [r for r in pend if r["url"] not in done][:25]:
        print("  PENDING", r["method"], r["url"][:140])
    b.close()

json.dump(res, open(OUT / "diagnose-signup-deep.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
