# 摸清 getLoginOptions 的行为：随机新邮箱 vs 已有邮箱，是否需要验证码令牌
import json, pathlib, random, string, time
from curl_cffi import requests as creq

ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT / "research" / "notion" / "captures"
PROXY_FILE = ROOT / "proxies.txt"

lines = [l.strip() for l in PROXY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
random.seed(7)
h, p_, u, pw = random.choice(lines).split(":", 3)
PROXY = {"http": f"http://{u}:{pw}@{h}:{p_}", "https": f"http://{u}:{pw}@{h}:{p_}"}
print("代理:", f"{h}:{p_}")

URL = "https://app.notion.com/api/v3/getLoginOptions"
HEAD = {
    "Content-Type": "application/json",
    "Notion-Client-Version": "23.13.20261017.1134",
    "Notion-Audit-Log-Platform": "web",
    "Origin": "https://app.notion.com",
    "Referer": "https://app.notion.com/signup",
    "Accept": "*/*",
}

def rand_mail():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=12)) + "@gmail.com"

cases = [
    ("随机 gmail", {"email": rand_mail()}),
    ("随机 gmail + requireWorkTypeEmail", {"email": rand_mail(), "requireWorkTypeEmail": False}),
    ("随机 qq", {"email": rand_mail().replace("@gmail.com", "@qq.com")}),
    ("randomuser 老邮箱", {"email": "randomuser@example.org"}),
]

sess = creq.Session(impersonate="chrome")
out = []
for label, body in cases:
    try:
        r = sess.post(URL, json=body, headers=HEAD, proxies=PROXY, timeout=30)
        j = r.json()
        out.append({"case": label, "email": body["email"], "status": r.status_code,
                    "hasAccount": j.get("hasAccount"), "keys": sorted(j.keys()),
                    "resp": j})
        print(f'{label:28s} {r.status_code}  hasAccount={j.get("hasAccount")}  keys={sorted(j.keys())}')
    except Exception as e:
        print("ERR", label, repr(e)[:120])
    time.sleep(1)

(OUT / "getLoginOptions-behavior.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
