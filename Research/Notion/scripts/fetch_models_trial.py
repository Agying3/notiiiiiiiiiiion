import json, pathlib, random, re, time
from curl_cffi import requests as creq
ROOT = pathlib.Path(r"REPO_ROOT"); OUT = ROOT/"research"/"notion"/"captures"/"web"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(99); h,p_,u,pw = random.choice(lines).split(":",3)
PROXY={"http":f"http://{u}:{pw}@{h}:{p_}","https":f"http://{u}:{pw}@{h}:{p_}"}
URLS={
 "ai-toolbar-models":"https://www.notion.com/help/notion-ai-model-picker",
 "startups":"https://www.notion.com/notion-for-startups",
 "pricing-faq":"https://www.notion.com/pricing#faq",
 "ai-models-doc":"https://www.notion.com/help/models-in-notion-ai",
 "free-plan":"https://www.notion.com/help/notion-free-plan",
}
s=creq.Session(impersonate="chrome")
for n,url in URLS.items():
    try:
        r=s.get(url,proxies=PROXY,timeout=35); html=r.text
        b=re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>"," ",html)
        b=re.sub(r"(?s)<[^>]+>"," ",b); b=re.sub(r"\s+"," ",b)
        (OUT/f"{n}.txt").write_text(b,encoding="utf-8",errors="ignore")
        print(f"{n:20s} {r.status_code} {len(b)}")
        # 打印含模型名/价格/试用的片段
        for m in re.finditer(r".{60}(Claude|GPT-|Gemini|Opus|Sonnet|Fable|trial|14 day|14-day|free).{120}", b, re.I):
            print("   *", m.group(0)[:200])
    except Exception as e:
        print(n,"ERR",repr(e)[:90])
    time.sleep(0.8)
