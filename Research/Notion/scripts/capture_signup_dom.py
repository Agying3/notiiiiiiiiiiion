# 抓取 Notion 注册页的真实 DOM + 网络请求，用于确认注册流程的 HTTP 步骤
import json, pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(r"REPO_ROOT")
flow = []
KEEP = ("api/v3", "statsig", "hcaptcha", "turnstile")


def on_response(resp):
    try:
        u = resp.url
        if not any(k in u for k in KEEP):
            return
        req = resp.request
        try:
            body = resp.text()
        except Exception:
            body = "<binary>"
        if body and len(body) > 3000:
            body = body[:3000] + "...<trunc>"
        flow.append({
            "method": req.method, "url": u, "status": resp.status,
            "post": (req.post_data or "")[:1500],
            "req_headers": {k: v for k, v in req.headers.items() if k.lower() in
                            ("content-type", "notion-client-version", "notion-audit-log-platform",
                             "x-notion-active-user-header", "user-agent", "notion-version")},
            "resp_body": body,
        })
    except Exception as e:
        flow.append({"error": repr(e)[:160]})


with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = b.new_context(
        viewport={"width": 1440, "height": 900}, locale="en-US",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    )
    pg = ctx.new_page()
    pg.on("response", on_response)
    # networkidle 永远等不到：页面会持续轮询 statsig/ping，改用 domcontentloaded
    pg.goto("https://app.notion.com/signup", wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(12000)
    print("URL:", pg.url, "| TITLE:", pg.title())

    html = pg.content()
    (OUT / "dom-signup.html").write_text(html, encoding="utf-8", errors="ignore")
    print("dom len:", len(html))

    inputs = pg.eval_on_selector_all(
        "input", "els => els.map(e=>({type:e.type,name:e.name,id:e.id,ph:e.placeholder,aria:e.getAttribute('aria-label')}))")
    print("inputs:", json.dumps(inputs, ensure_ascii=False))

    btns = pg.eval_on_selector_all(
        "button, [role=button], a[href]",
        "els => els.slice(0,60).map(e=>({t:(e.innerText||'').trim().slice(0,50),h:e.getAttribute('href')}))")
    print("buttons:", json.dumps([x for x in btns if x["t"] or x["h"]], ensure_ascii=False)[:2500])
    print("body:", pg.inner_text("body")[:1500].replace("\n", " | "))

    pg.screenshot(path=str(OUT / "dom-signup.png"), full_page=True)
    ctx.storage_state(path=str(OUT / "state-signup.json"))
    b.close()

(OUT / "flow-signup-network-2.json").write_text(
    json.dumps(flow, indent=2, ensure_ascii=False), encoding="utf-8")
print("captured:", len(flow))
for f in flow:
    if "url" in f:
        print(f["status"], f["method"], f["url"][:130])
