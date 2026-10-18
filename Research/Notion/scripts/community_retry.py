# Reddit 换代理重试 + HN Algolia 定向 + Notion 官方社区，找社区对 AI 额度的实测说法
import json, pathlib, random, re, time
from curl_cffi import requests as creq

ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT / "research" / "notion" / "captures" / "community"
OUT.mkdir(parents=True, exist_ok=True)
lines = [l.strip() for l in (ROOT / "proxies.txt").read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
random.seed(606)
proxies = []
for line in random.sample(lines, 40):
    h, p_, u, pw = line.split(":", 3)
    proxies.append({"http": f"http://{u}:{pw}@{h}:{p_}", "https": f"http://{u}:{pw}@{h}:{p_}"})

s = creq.Session(impersonate="chrome")
H = {"Accept-Language": "en-US,en;q=0.9", "Accept": "application/json"}

print("=== Reddit 搜索（换代理重试）")
reddit_items = []
for i, px in enumerate(proxies[:20], 1):
    try:
        r = s.get("https://www.reddit.com/r/Notion/search.json",
                  params={"q": "AI limit", "restrict_sr": 1, "limit": 25, "sort": "relevance", "t": "year"},
                  proxies=px, headers=H, timeout=25)
        if r.status_code == 200 and r.text.lstrip().startswith("{"):
            for c in r.json()["data"]["children"]:
                d = c["data"]
                reddit_items.append({"title": d["title"], "score": d["score"],
                                     "comments": d["num_comments"],
                                     "text": (d.get("selftext") or "")[:1500],
                                     "url": "https://reddit.com" + d["permalink"]})
            print(f"  代理#{i} 成功，拿到 {len(reddit_items)} 条")
            break
        print(f"  代理#{i} -> {r.status_code}")
    except Exception as e:
        print(f"  代理#{i} ERR {repr(e)[:60]}")
    time.sleep(0.4)

for it in reddit_items[:12]:
    print(f"  [R] {it['title'][:95]}  ({it['score']}p/{it['comments']}c)")
    if it["text"].strip():
        print(f"      {it['text'].strip()[:300]}")

print("\n=== HN Algolia（限定 Notion）")
hn = []
for q in ["Notion AI limit", "Notion AI usage allowance", "Notion AI free"]:
    try:
        r = s.get("https://hn.algolia.com/api/v1/search",
                  params={"query": q, "tags": "comment", "hitsPerPage": 30},
                  proxies=proxies[0], timeout=30)
        for hh in r.json().get("hits", []):
            txt = re.sub(r"<[^>]+>", " ", hh.get("comment_text") or "")
            if re.search(r"notion", txt, re.I) and re.search(r"(AI|limit|credit|allowance)", txt, re.I):
                hn.append({"story": hh.get("story_title"), "text": txt[:700],
                           "id": hh.get("objectID")})
        print(f"  query={q} -> 命中 {len(hn)}")
    except Exception as e:
        print("  HN ERR", repr(e)[:70])
    time.sleep(0.5)

for it in hn[:8]:
    print(f"  [H] {(it['story'] or '')[:70]}")
    print(f"      {it['text'][:250]}")

print("\n=== Notion 官方社区搜索页")
for url in ["https://community.notion.so/search?q=AI%20limit",
            "https://community.notion.so/t/notion-ai-usage"]:
    try:
        r = s.get(url, proxies=proxies[0], timeout=30)
        print(f"  {r.status_code} {url} len={len(r.text)}")
        if r.status_code == 200:
            body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", r.text)
            body = re.sub(r"(?s)<[^>]+>", " ", body)
            body = re.sub(r"\s+", " ", body)
            print("   TEXT:", body[:600])
    except Exception as e:
        print("  ERR", repr(e)[:70])

json.dump({"reddit": reddit_items, "hn": hn},
          open(OUT / "community-findings.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
