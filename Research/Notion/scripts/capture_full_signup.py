# 走完整注册链路（浏览器只用于观察/接码），抓全部 /api/v3 请求与响应
import json, pathlib, random, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT / "research" / "notion" / "captures"
PROXY_FILE = ROOT / "proxies.txt"
TEST_EMAIL = "probe.placeholder@example.com"   # 占位邮箱，只用于看接口行为

lines = [l.strip() for l in PROXY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
random.seed(20261018)
host, port, user, pwd = random.choice(lines).split(":", 3)
proxy_cfg = {"server": f"http://{host}:{port}", "username": user, "password": pwd}
print("代理:", f"{host}:{port}", "| 邮箱:", TEST_EMAIL)

flow = []


def on_resp(resp):
    try:
        u = resp.url
        if "/api/v3/" not in u:
            return
        try:
            body = resp.text()
        except Exception:
            body = "<binary>"
        if body and len(body) > 3000:
            body = body[:3000] + "...<trunc>"
        flow.append({"ts": round(time.time(), 3), "method": resp.request.method,
                     "endpoint": u.split("/api/v3/")[-1], "status": resp.status,
                     "post": (resp.request.post_data or "")[:1500], "resp_body": body})
    except Exception as e:
        flow.append({"error": repr(e)[:120]})


with sync_playwright() as p:
    b = p.chromium.launch(headless=True, proxy=proxy_cfg, args=["--no-sandbox"])
    ctx = b.new_context(locale="en-US", viewport={"width": 1440, "height": 1000})
    pg = ctx.new_page()
    pg.on("response", on_resp)
    pg.goto("https://app.notion.com/signup", wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(9000)

    # 步骤 1：填邮箱
    email_input = pg.locator('input[type="email"]').first
    if not email_input.count():
        email_input = pg.locator("input").first
    email_input.fill(TEST_EMAIL)
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT / "step1-email-filled.png"))

    mark = len(flow)
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(9000)

    print("\n--- 提交邮箱后的 URL:", pg.url)
    print("--- 页面文本:", pg.inner_text("body")[:500].replace("\n", " | "))
    pg.screenshot(path=str(OUT / "step2-after-submit.png"), full_page=True)
    (OUT / "step2-dom.html").write_text(pg.content(), encoding="utf-8", errors="ignore")
    ctx.storage_state(path=str(OUT / "state-after-submit.json"))

    print("\n--- 提交邮箱后新产生的 v3 调用:")
    for f in flow[mark:]:
        if "endpoint" in f:
            print(f'  {f["status"]} {f["endpoint"]}  <- {f["post"][:200]}')
            print(f'     resp: {f["resp_body"][:400]}')
    b.close()

(OUT / "flow-signup-full.json").write_text(json.dumps(flow, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n总 v3 请求:", len(flow))
