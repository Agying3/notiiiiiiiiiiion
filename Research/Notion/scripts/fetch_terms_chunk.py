import pathlib, random, re, json
from curl_cffi import requests as creq
ROOT=pathlib.Path(r"REPO_ROOT"); OUT=ROOT/"research"/"notion"/"captures"/"web"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(2468); h,po,u,pw=random.choice(lines).split(":",3)
PX={"http":f"http://{u}:{pw}@{h}:{po}","https":f"http://{u}:{pw}@{h}:{po}"}
s=creq.Session(impersonate="chrome")
url="https://notion.notion.site/Notion-s-Promotional-Offer-for-Business-Plan-Discount-27eefdeead05804ea4adff45330b86e9"
r=s.get(url,proxies=PX,timeout=35)
print("status",r.status_code,"len",len(r.text))
print(r.text[:600])
# notion.site 是客户端渲染，走 loadPageChunk
import uuid
bid=re.search(r'([0-9a-f]{32})', url)
print("blockId?", bid.group(1) if bid else None)
if bid:
    page_id=bid.group(1)
    body={"page":{"id":page_id},"limit":100,"cursor":{"stack":[]},"chunkNumber":0,"verticalColumns":False}
    r2=s.post("https://www.notion.so/api/v3/loadCachedPageChunkV2",json=body,proxies=PX,timeout=35,
              headers={"Content-Type":"application/json","Notion-Client-Version":"23.13.20261017.1134"})
    print("chunk status",r2.status_code,len(r2.text))
    (OUT/"terms-notion-site.json").write_text(r2.text,encoding="utf-8")
    if r2.status_code==200:
        d=r2.json()
        rm=d.get("recordMap",{})
        titles=[v["value"]["value"].get("title") for k,v in rm.get("block",{}).items() if isinstance(v,dict)]
        for b in rm.get("block",{}).values():
            val=b.get("value",{})
            if isinstance(val,dict) and val.get("type")=="page":
                print("PAGE TITLE:", val.get("title"))
