import pathlib, random, re, json, time
from curl_cffi import requests as creq
ROOT=pathlib.Path(r"REPO_ROOT"); OUT=ROOT/"research"/"notion"/"captures"/"community"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(20261017)
def px(l):
    h,po,u,pw=l.split(":",3); return {"http":f"http://{u}:{pw}@{h}:{po}","https":f"http://{u}:{pw}@{h}:{po}"}
s=creq.Session(impersonate="chrome")
# 1) Notion 官方社区（Discourse）
for attempt in range(6):
    P=px(random.choice(lines))
    try:
        r=s.get("https://community.notion.so/search.json",params={"q":"AI limit"},proxies=P,timeout=20)
        print("community",r.status_code,len(r.text))
        if r.status_code==200 and r.text.lstrip().startswith("{") or "topic" in r.text[:200]:
            d=r.json()
            for t in d.get("topics",[])[:12]:
                print("  *",t.get("title"))
            (OUT/"notion-forum.json").write_text(json.dumps(d,ensure_ascii=False)[:200000],encoding="utf-8")
            break
    except Exception as e:
        print(" attempt",attempt,"ERR",repr(e)[:60])
# 2) Bing 加引号精细查询
for q in ['"complimentary AI responses"', '"Notion AI" "usage allowance" limit', '"Notion AI" credits "per 1,000"']:
    P=px(random.choice(lines))
    try:
        r=s.get("https://www.bing.com/search",params={"q":q,"count":"30","setmkt":"en-US"},proxies=P,timeout=30)
        print("\nQ:",q,r.status_code)
        n=0
        for m in re.finditer(r'(?is)<li class="b_algo".*?</li>',r.text):
            blk=m.group(0)
            t=re.search(r"(?is)<h2[^>]*>(.*?)</h2>",blk); sn=re.search(r"(?is)<p[^>]*>(.*?)</p>",blk)
            cl=lambda x: re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",x or "")).strip()
            tt,ss=cl(t.group(1) if t else ""),cl(sn.group(1) if sn else "")
            if re.search(r"(ai|response|credit|limit|allowance)",(tt+ss).lower()):
                print("  *",tt[:95]); print("    ",ss[:220]); n+=1
        print("  命中",n)
    except Exception as e: print("bing err",repr(e)[:60])
    time.sleep(1)
