# 验证「登录」链路是否也要 hCaptcha：决定能否用现成号直接测额度
import pathlib, random, json
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(r"REPO_ROOT"); OUT=ROOT/"research"/"notion"/"captures"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(20261017); h,po,u,pw=random.choice(lines).split(":",3)
PX={"server":f"http://{h}:{po}","username":u,"password":pw}
flow=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,proxy=PX,args=["--no-sandbox"])
    pg=b.new_page(locale="en-US")
    pg.on("response", lambda r: flow.append((r.status, r.url.split("/api/v3/")[-1], (r.request.post_data or "")[:120])) if "/api/v3/" in r.url else None)
    pg.goto("https://app.notion.com/login",wait_until="domcontentloaded",timeout=60000)
    pg.wait_for_timeout(10000)
    print("URL:",pg.url)
    print("inputs:",pg.locator("input").count())
    txt=pg.inner_text("body")
    print("body:",txt[:400].replace("\n"," | "))
    html=pg.content()
    for k in ("hcaptcha","turnstile","sitekey","g-recaptcha","challenge"):
        print(f"  {k}: {html.lower().count(k)}")
    pg.screenshot(path=str(OUT/"login-page.png"),full_page=True)
    b.close()
print("v3:",flow)
