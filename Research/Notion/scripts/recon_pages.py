import json, pathlib, time
from curl_cffi import requests as creq

OUT = pathlib.Path(r"REPO_ROOT")
OUT.mkdir(parents=True, exist_ok=True)

targets = [
    ("signup-www", "https://www.notion.com/signup"),
    ("signup-so", "https://www.notion.so/signup"),
    ("login-so", "https://www.notion.so/login"),
    ("home-www", "https://www.notion.com/"),
]

sess = creq.Session(impersonate="chrome")
rec = []
for name, url in targets:
    try:
        r = sess.get(url, timeout=30, allow_redirects=True)
        body = r.text
        (OUT / f"page-{name}.html").write_text(body, encoding="utf-8", errors="ignore")
        info = {
            "name": name, "url": url, "final_url": str(r.url), "status": r.status_code,
            "len": len(body),
            "server": r.headers.get("server"), "cf_ray": r.headers.get("cf-ray"),
            "cf_mitigated": r.headers.get("cf-mitigated"),
            "content_type": r.headers.get("content-type"),
            "set_cookie": r.headers.get("set-cookie"),
            "markers": {k: (k.lower() in body.lower()) for k in
                        ["hcaptcha","turnstile","cf-challenge","notion-next","__NEXT_DATA__","_notion","grecaptcha","datadome","cloudflare"]},
        }
        rec.append(info)
        print(json.dumps(info, ensure_ascii=False))
    except Exception as e:
        print("ERR", name, repr(e)[:300])
    time.sleep(1.5)

(OUT / "page-recon.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
