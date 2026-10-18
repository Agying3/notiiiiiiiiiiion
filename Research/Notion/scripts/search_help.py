import pathlib, random, re, json
from curl_cffi import requests as creq
ROOT = pathlib.Path(r"REPO_ROOT"); OUT = ROOT/"research"/"notion"/"captures"/"web"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(777); h,p_,u,pw=random.choice(lines).split(":",3)
PROXY={"http":f"http://{u}:{pw}@{h}:{p_}","https":f"http://{u}:{pw}@{h}:{p_}"}
s=creq.Session(impersonate="chrome")
# 帮助中心站内搜索
for q in ["trial","referral","complimentary ai","free plan blocks","model"]:
    try:
        r=s.get("https://www.notion.com/help/search",params={"q":q},proxies=PROXY,timeout=30)
        print("SEARCH",q,r.status_code,len(r.text))
    except Exception as e: print("err",e)
# Algolia 检索（Notion 帮助中心常用）
try:
    body={"query":"trial","hitsPerPage":8}
    r=s.post("https://NOTION_APP_ID-dsn.algolia.net/1/indexes/help/query",json=body,proxies=PROXY,timeout=20)
    print("algolia",r.status_code)
except Exception as e: print("algolia err",repr(e)[:60])
