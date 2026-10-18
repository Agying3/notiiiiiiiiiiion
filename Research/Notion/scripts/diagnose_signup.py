# 诊断注册页为何没渲染出表单：抓 console 错误 + 失败的静态资源
import json, pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(r"REPO_ROOT")
failed, console, responses = [], [], []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = b.new_context(locale="en-US")
    pg = ctx.new_page()
    pg.on("requestfailed", lambda r: failed.append({"url": r.url[:160], "err": r.failure}))
    pg.on("console", lambda m: console.append({"type": m.type, "text": m.text[:300]}))
    pg.on("response", lambda r: responses.append({"status": r.status, "url": r.url[:160]}))
    pg.goto("https://app.notion.com/signup", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(15000)

    static = [r for r in responses if "/_assets/" in r["url"] or r["url"].endswith(".js")]
    bad = [r for r in static if r["status"] >= 400]
    print(f"静态资源 {len(static)} 个，失败 {len(bad)} 个")
    for r in bad[:20]:
        print("  BAD", r["status"], r["url"])
    print(f"requestfailed {len(failed)}")
    for f in failed[:20]:
        print("  FAIL", f["err"], f["url"])
    print(f"console {len(console)}")
    for c in console[:20]:
        print("  ", c["type"], c["text"][:180])
    print("body text:", repr(pg.inner_text("body")[:200]))

json.dump({"failed": failed, "console": console,
           "static_bad": [r for r in responses if r["status"] >= 400]},
          open(OUT / "diagnose-signup.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
