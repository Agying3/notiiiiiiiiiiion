# 快速验证：直连 vs 代理池 IP，能否拿到 app.notion.com 的关键静态资源
import json, pathlib, random, time
from curl_cffi import requests as creq

ROOT = pathlib.Path(r"REPO_ROOT")
PROXY_FILE = ROOT / "proxies.txt"
OUT = ROOT / "research" / "notion" / "captures"

TEST_URLS = [
    "https://app.notion.com/api/v3/ping",
    "https://app.notion.com/_assets/6793-fae6c663a8589fb2.js",
    "https://app.notion.com/signup",
]

proxies = []
for line in PROXY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
    line = line.strip()
    if not line or line.count(":") < 3:
        continue
    host, port, user, pwd = line.split(":", 3)
    proxies.append(f"http://{user}:{pwd}@{host}:{port}")

random.seed(20261017)
sample = random.sample(proxies, min(5, len(proxies)))
print(f"代理池共 {len(proxies)} 条，抽 {len(sample)} 条测试\n")

HEAD = {"Notion-Client-Version": "23.13.20261017.1134", "Notion-Audit-Log-Platform": "web"}
rows = []

def probe(label, proxy=None):
    s = creq.Session(impersonate="chrome")
    for url in TEST_URLS:
        t0 = time.time()
        try:
            kw = {"timeout": 25, "headers": HEAD}
            if proxy:
                kw["proxies"] = {"http": proxy, "https": proxy}
            r = s.post(url, json={}, **kw) if url.endswith("ping") else s.get(url, **kw)
            rows.append({"label": label, "url": url.rsplit("/", 1)[-1],
                         "status": r.status_code, "ms": int((time.time()-t0)*1000), "bytes": len(r.content)})
        except Exception as e:
            rows.append({"label": label, "url": url.rsplit("/", 1)[-1],
                         "status": "ERR", "ms": int((time.time()-t0)*1000), "err": repr(e)[:80]})

probe("直连")
for i, px in enumerate(sample, 1):
    probe(f"代理{i}", px)

(OUT / "proxy-vs-direct.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
for r in rows:
    print(f'{r["label"]:8s} {str(r["status"]):>4}  {r["ms"]:>6d}ms  {r.get("bytes","-"):>8}  {r["url"]}  {r.get("err","")}')
