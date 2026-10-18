import json, pathlib
from playwright.sync_api import sync_playwright
OUT = pathlib.Path(r"REPO_ROOT")
with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(viewport={"width":1440,"height":900}, locale="en-US")
    pg = ctx.new_page()
    reqs=[]
    pg.on("request", lambda r: reqs.append(r.url))
    pg.goto("https://app.notion.com/signup", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(20000)
    print("body text:", repr(pg.inner_text("body")[:300]))
    print("inputs:", pg.locator("input").count())
    pg.screenshot(path=str(OUT/"screenshot-headful-signup.png"), full_page=True)
    print("URL:", pg.url)
    print("root html len:", len(pg.content()))
    b.close()
