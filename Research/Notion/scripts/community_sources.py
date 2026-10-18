# 社区源逐个试通：reddit(old/www)、bing site: 定向、Notion 官方社区
import json, pathlib, random, re, time
from curl_cffi import requests as creq

ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT / "research" / "notion" / "captures" / "community"
OUT.mkdir(parents=True, exist_ok=True)
lines = [l.strip() for l in (ROOT / "proxies.txt").read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
random.seed(9091)
h, p_, u, pw = random.choice(lines).split(":", 3)
PROXY = {"http": f"http://{u}:{pw}@{h}:{p_}", "https": f"http://{u}:{pw}@{h}:{p_}"}
s = creq.Session(impersonate="chrome")
H = {"Accept-Language": "en-US,en;q=0.9"}


def try_get(label, url, **kw):
    try:
        r = s.get(url, proxies=PROXY, headers=H, timeout=35, **kw)
        print(f"{label:28s} {r.status_code}  {len(r.text):>8}")
        return r
    except Exception as e:
        print(f"{label:28s} ERR {repr(e)[:80]}")
        return None


# 1) reddit 多入口
for host in ["old.reddit.com", "www.reddit.com"]:
    r = try_get(f"reddit-{host}", f"https://{host}/r/Notion/search.json",
                params={"q": "AI limits", "restrict_sr": 1, "limit": 10, "sort": "relevance"})
    if r is not None and r.status_code == 200:
        try:
            items = [(c["data"]["title"], c["data"]["score"], c["data"]["permalink"])
                     for c in r.json()["data"]["children"]]
            for t in items[:8]:
                print("    ", t[0][:90], "|", t[1])
            (OUT / "reddit-notion-sub.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            break
        except Exception as e:
            print("     parse err", repr(e)[:60])
    time.sleep(1)

# 2) Bing 定向 site: 搜索
for q in ["site:reddit.com notion ai free limit responses",
          "notion ai \"complimentary\" responses how many",
          "notion ai usage allowance limit reached"]:
    r = try_get("bing", "https://www.bing.com/search", params={"q": q, "setlang": "en", "cc": "US"})
    if r is not None and r.status_code == 200:
        hits = 0
        for m in re.finditer(r'(?is)<li class="b_algo".*?</li>', r.text):
            blk = m.group(0)
            t = re.search(r"(?is)<h2[^>]*>(.*?)</h2>", blk)
            sn = re.search(r"(?is)<p[^>]*>(.*?)</p>", blk)
            clean = lambda x: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x or "")).strip()
            title, snip = clean(t.group(1) if t else ""), clean(sn.group(1) if sn else "")
            if "notion" in (title + snip).lower():
                print("   [B]", title[:85], "|", snip[:140])
                hits += 1
        if not hits:
            print("   [B] 无 notion 相关结果")
    time.sleep(1)

# 3) Notion 官方社区
for url in ["https://community.notion.so/", "https://www.notion.so/help"]:
    try_get("notion-community", url)
