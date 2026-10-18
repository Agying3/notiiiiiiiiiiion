import json, pathlib, time
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(r"REPO_ROOT")
flow = []
KEEP = ("/api/v3/", "notion.com/api", "authValidate", "getLoginOptions", "signup", "login")

def on_response(resp):
    try:
        u = resp.url
        if not any(k in u for k in KEEP):
            return
        req = resp.request
        body = None
        try:
            body = resp.text()
        except Exception:
            body = "<binary/stream>"
        if body and len(body) > 4000:
            body = body[:4000] + "...<truncated>"
        flow.append({
            "method": req.method, "url": u, "status": resp.status,
            "post": (req.post_data or "")[:2000],
            "req_headers": {k: v for k, v in req.headers.items()
                            if k.lower() in ("content-type","notion-client-version","notion-audit-log-platform","x-notion-active-user-header","cookie","user-agent","notion-version")},
            "resp_body": body,
        })
    except Exception as e:
        flow.append({"error": repr(e)[:200]})

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=["--start-maximized"])
    ctx = b.new_context(viewport={"width":1440,"height":900}, locale="en-US")
    pg = ctx.new_page()
    pg.on("response", on_response)
    pg.goto("https://www.notion.com/signup", wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(4000)
    print("TITLE:", pg.title())
    print("URL:", pg.url)
    # 找邮箱输入框
    for sel in ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="mail" i]']:
        if pg.locator(sel).count():
            print("email input found:", sel)
            pg.locator(sel).first.fill("probe.placeholder@example.com")
            pg.wait_for_timeout(800)
            try:
                pg.keyboard.press("Enter")
            except Exception:
                pass
            pg.wait_for_timeout(6000)
            break
    print("URL after submit:", pg.url)
    pg.screenshot(path=str(OUT / "flow-signup-step1.png"), full_page=False)
    ctx.storage_state(path=str(OUT / "flow-signup-state.json"))
    b.close()

(OUT / "flow-signup-network.json").write_text(json.dumps(flow, indent=2, ensure_ascii=False), encoding="utf-8")
print("captured:", len(flow))
for f in flow:
    if "url" in f: print(f["status"], f["method"], f["url"][:120])
