# 用可用的 SearXNG 实例做社区检索，解析标题/摘要/链接
import json, pathlib, random, re, time, html as htmlmod
from curl_cffi import requests as creq

ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT / "research" / "notion" / "captures" / "community"
OUT.mkdir(parents=True, exist_ok=True)
lines = [l.strip() for l in (ROOT / "proxies.txt").read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
random.seed(31415)
h, po, u, pw = random.choice(lines).split(":", 3)
PX = {"http": f"http://{u}:{pw}@{h}:{po}", "https": f"http://{u}:{pw}@{h}:{po}"}
s = creq.Session(impersonate="chrome")

QUERIES = [
    'notion ai complimentary responses limit',
    'notion ai free plan "responses" limit reddit',
    'notion ai usage allowance 6 hour window',
    'notion ai credits reset monthly carry over',
    'notion ai business trial model picker',
]

def clean(x):
    x = re.sub(r"<[^>]+>", "", x or "")
    return re.sub(r"\s+", " ", htmlmod.unescape(x)).strip()

all_rows = []
for q in QUERIES:
    print(f"\n===== {q}")
    for fmt, url in (("json", "https://search.marcia.cc/search"),):
        try:
            r = s.get(url, params={"q": q, "format": "json"}, proxies=PX, timeout=30)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                data = r.json()
                for it in data.get("results", [])[:12]:
                    row = {"q": q, "title": it.get("title"), "url": it.get("url"),
                           "content": (it.get("content") or "")[:400],
                           "engine": it.get("engine")}
                    all_rows.append(row)
                    print(f"  * {clean(row['title'])[:95]}")
                    print(f"    {clean(row['url'])[:110]}")
                    if row["content"]:
                        print(f"    {clean(row['content'])[:230]}")
                print(f"  [json ok, {len(data.get('results', []))} 条]")
                break
            else:
                print(f"  json 不可用 {r.status_code}, 转 HTML")
                r2 = s.get(url, params={"q": q}, proxies=PX, timeout=30)
                for m in re.finditer(r'(?is)<article class="result.*?</article>', r2.text):
                    blk = m.group(0)
                    t = re.search(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', blk)
                    p = re.search(r'(?is)<p class="content">(.*?)</p>', blk)
                    if t:
                        row = {"q": q, "title": clean(t.group(2)),
                               "url": t.group(1), "content": clean(p.group(1) if p else "")}
                        all_rows.append(row)
                        print(f"  * {row['title'][:95]}")
                        print(f"    {row['url'][:110]}")
                        print(f"    {row['content'][:230]}")
        except Exception as e:
            print("  ERR", repr(e)[:90])
    time.sleep(1)

(OUT / "searx-results.json").write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n总计 {len(all_rows)} 条")
