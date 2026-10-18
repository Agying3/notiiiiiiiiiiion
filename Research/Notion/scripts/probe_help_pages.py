# 批量探测 Notion 帮助中心候选页面，找到「AI 模型清单 / 免费额度 / 试用与推荐奖励」的权威页
import json, pathlib, random, re, time
from curl_cffi import requests as creq

ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT / "research" / "notion" / "captures" / "web"
OUT.mkdir(parents=True, exist_ok=True)
PROXY_FILE = ROOT / "proxies.txt"

lines = [l.strip() for l in PROXY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
random.seed(4242)
h, p_, u, pw = random.choice(lines).split(":", 3)
PROXY = {"http": f"http://{u}:{pw}@{h}:{p_}", "https": f"http://{u}:{pw}@{h}:{p_}"}

CANDIDATES = [
    "manage-notion-ai-models", "notion-ai-models", "choose-an-ai-model", "select-an-ai-model",
    "notion-ai-model-picker", "manage-ai-models-and-member-credit-spend",
    "notion-business-trial", "start-your-notion-business-trial", "notion-enterprise-trial",
    "free-plan-limits", "what-is-the-free-plan", "blocks-limit-free-plan",
    "referral-program", "invite-friends-and-earn-credit", "notion-referral",
    "student-plan", "free-plus-for-students", "notion-for-startups", "startup-program",
    "upgrade-or-downgrade-your-plan", "plans-and-pricing", "notion-ai-usage",
    "notion-ai-faqs", "custom-agents", "notion-agent-pricing",
]

sess = creq.Session(impersonate="chrome")
report = []
for slug in CANDIDATES:
    url = f"https://www.notion.com/help/{slug}"
    try:
        r = sess.get(url, proxies=PROXY, timeout=40)
        html = r.text
        title = ""
        m = re.search(r"(?is)<title>(.*?)</title>", html)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()[:90]
        ok = r.status_code == 200
        if ok:
            body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
            body = re.sub(r"(?s)<[^>]+>", " ", body)
            body = re.sub(r"\s+", " ", body)
            (OUT / f"help-{slug}.txt").write_text(body, encoding="utf-8", errors="ignore")
        report.append({"slug": slug, "status": r.status_code, "title": title})
        print(f"{r.status_code}  {slug:46s} {title}")
    except Exception as e:
        report.append({"slug": slug, "status": "ERR", "err": repr(e)[:100]})
        print(f"ERR {slug} {repr(e)[:80]}")
    time.sleep(1.0)

(OUT / "help-candidates.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
