# 通过代理池跑注册页，验证是否能正常渲染出表单（直连被 RST 导致卡 loading）
import json, pathlib, random
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT / "research" / "notion" / "captures"
PROXY_FILE = ROOT / "proxies.txt"

lines = [l.strip() for l in PROXY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
random.seed(20261017)
host, port, user, pwd = random.choice(lines).split(":", 3)
proxy_cfg = {"server": f"http://{host}:{port}", "username": user, "password": pwd}
print("使用代理:", f"{host}:{port}")

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
        if body and len(body) > 2500:
            body = body[:2500] + "...<trunc>"
        flow.append({"method": resp.request.method, "url": u, "status": resp.status,
                     "post": (resp.request.post_data or "")[:1200], "resp_body": body})
    except Exception as e:
        flow.append({"error": repr(e)[:120]})


with sync_playwright() as p:
    b = p.chromium.launch(headless=True, proxy=proxy_cfg, args=["--no-sandbox"])
    ctx = b.new_context(locale="en-US", viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    pg.on("response", on_resp)
    pg.goto("https://app.notion.com/signup", wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(12000)

    print("URL:", pg.url)
    print("body text:", pg.inner_text("body")[:400].replace("\n", " | "))
    print("input count:", pg.locator("input").count())
    print("buttons:", pg.locator("button").count())

    pg.screenshot(path=str(OUT / "signup-via-proxy.png"), full_page=True)
    (OUT / "signup-via-proxy.html").write_text(pg.content(), encoding="utf-8", errors="ignore")
    ctx.storage_state(path=str(OUT / "state-proxy.json"))
    b.close()

(OUT / "flow-signup-proxy.json").write_text(json.dumps(flow, ensure_ascii=False, indent=2), encoding="utf-8")
print("v3 请求数:", len(flow))
for f in flow:
    if "url" in f:
        print(" ", f["status"], f["method"], f["url"].replace("https://app.notion.com", ""))
