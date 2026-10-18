# 社区口碑检索：Reddit / HN / Bing，查 Notion AI 额度、complimentary 次数、是否每月刷新
import json, pathlib, random, re, time, urllib.parse
from curl_cffi import requests as creq

ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT / "research" / "notion" / "captures" / "community"
OUT.mkdir(parents=True, exist_ok=True)
PROXY_FILE = ROOT / "proxies.txt"

lines = [l.strip() for l in PROXY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
random.seed(31337)
h, p_, u, pw = random.choice(lines).split(":", 3)
PROXY = {"http": f"http://{u}:{pw}@{h}:{p_}", "https": f"http://{u}:{pw}@{h}:{p_}"}

sess = creq.Session(impersonate="chrome")
UA = {"Accept-Language": "en-US,en;q=0.9"}

QUERIES = [
    "notion ai complimentary responses how many",
    "notion ai credits reset monthly",
    "notion ai usage allowance 6 hour",
    "notion ai free plan limit reddit",
]

def reddit_search(q):
    url = "https://www.reddit.com/search.json"
    r = sess.get(url, params={"q": q, "sort": "relevance", "limit": 15, "t": "year"},
                 proxies=PROXY, headers=UA, timeout=40)
    if r.status_code != 200:
        return {"status": r.status_code, "body": r.text[:300]}
    data = r.json()
    items = []
    for c in data.get("data", {}).get("children", []):
        d = c.get("data", {})
        items.append({"title": d.get("title"), "sub": d.get("subreddit"),
                      "score": d.get("score"), "num_comments": d.get("num_comments"),
                      "created": d.get("created_utc"), "selftext": (d.get("selftext") or "")[:1200],
                      "permalink": "https://reddit.com" + (d.get("permalink") or "")})
    return {"status": 200, "items": items}

def hn_search(q):
    r = sess.get("https://hn.algolia.com/api/v1/search",
                 params={"query": q, "tags": "(story,comment)", "hitsPerPage": 15},
                 proxies=PROXY, timeout=30)
    if r.status_code != 200:
        return {"status": r.status_code}
    hits = []
    for hh in r.json().get("hits", []):
        txt = hh.get("comment_text") or hh.get("title") or ""
        hits.append({"title": hh.get("title") or hh.get("story_title"),
                     "text": re.sub(r"<[^>]+>", " ", txt)[:800],
                     "points": hh.get("points"), "url": hh.get("url"),
                     "objectID": hh.get("objectID")})
    return {"status": 200, "hits": hits}

def bing(q):
    r = sess.get("https://www.bing.com/search", params={"q": q, "count": 20},
                 proxies=PROXY, headers=UA, timeout=40)
    if r.status_code != 200:
        return {"status": r.status_code}
    html = r.text
    out = []
    for m in re.finditer(r'(?is)<li class="b_algo".*?</li>', html):
        blk = m.group(0)
        t = re.search(r"(?is)<h2[^>]*>(.*?)</h2>", blk)
        sn = re.search(r"(?is)<p[^>]*>(.*?)</p>", blk)
        href = re.search(r'href="(http[^"]+)"', blk)
        clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()
        out.append({"title": clean(t.group(1) if t else ""),
                    "snippet": clean(sn.group(1) if sn else ""),
                    "url": href.group(1) if href else ""})
    return {"status": 200, "results": out}

report = {}
for q in QUERIES:
    print(f"\n===== {q}")
    for name, fn in (("reddit", reddit_search), ("hn", hn_search), ("bing", bing)):
        try:
            res = fn(q)
            report.setdefault(name, {})[q] = res
            if name == "reddit" and res.get("status") == 200:
                for it in res["items"][:6]:
                    print(f"  [R] {it['title'][:90]} (r/{it['sub']}, {it['score']}p)")
                    if it["selftext"]:
                        print(f"      {it['selftext'][:220]}")
            elif name == "hn" and res.get("status") == 200:
                for it in res["hits"][:4]:
                    print(f"  [H] {(it['title'] or '')[:80]} :: {it['text'][:200]}")
            elif name == "bing" and res.get("status") == 200:
                for it in res["results"][:6]:
                    print(f"  [B] {it['title'][:80]} | {it['snippet'][:160]}")
            else:
                print(f"  [{name}] status={res.get('status')}")
        except Exception as e:
            print(f"  [{name}] ERR {repr(e)[:100]}")
        time.sleep(0.8)

(OUT / "community-search.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
