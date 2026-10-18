# 用代理抓 Notion 官网/帮助中心的定价与 AI 说明页，落地成纯文本便于检索
import json, pathlib, random, re, time
from curl_cffi import requests as creq

ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT / "research" / "notion" / "captures" / "web"
OUT.mkdir(parents=True, exist_ok=True)
PROXY_FILE = ROOT / "proxies.txt"

lines = [l.strip() for l in PROXY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
random.seed(20261019)
h, p_, u, pw = random.choice(lines).split(":", 3)
PROXY = {"http": f"http://{u}:{pw}@{h}:{p_}", "https": f"http://{u}:{pw}@{h}:{p_}"}

PAGES = {
    "pricing": "https://www.notion.com/pricing",
    "credits": "https://www.notion.com/help/what-are-notion-credits",
    "allowance": "https://www.notion.com/help/manage-your-usage-allowance-for-notion-ai",
    "models": "https://www.notion.com/help/notion-ai-models",
    "plans": "https://www.notion.com/help/plans-and-billing",
    "trial": "https://www.notion.com/help/notion-business-trial",
    "ai-faq": "https://www.notion.com/help/notion-ai-faqs",
    "agent": "https://www.notion.com/help/notion-agent",
}

sess = creq.Session(impersonate="chrome")
summary = {}
for name, url in PAGES.items():
    try:
        r = sess.get(url, proxies=PROXY, timeout=40)
        html = r.text
        (OUT / f"{name}.html").write_text(html, encoding="utf-8", errors="ignore")
        # 粗暴正文提取
        body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
        body = re.sub(r"(?s)<[^>]+>", " ", body)
        body = re.sub(r"&nbsp;?", " ", body)
        body = re.sub(r"\s+", " ", body)
        (OUT / f"{name}.txt").write_text(body, encoding="utf-8", errors="ignore")
        summary[name] = {"status": r.status_code, "len": len(html), "text_len": len(body)}
        print(f"{name:10s} {r.status_code}  html={len(html):>7}  text={len(body):>7}")
    except Exception as e:
        summary[name] = {"status": "ERR", "err": repr(e)[:120]}
        print(f"{name:10s} ERR {repr(e)[:110]}")
    time.sleep(1.2)

(OUT / "_fetch-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
