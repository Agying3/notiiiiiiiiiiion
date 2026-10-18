import re, pathlib, collections
js = pathlib.Path(r"REPO_ROOT")
# 更宽的匹配：模型选择器 / chat 输入框相关组件名
pats = {
  "picker": re.compile(r'"([A-Za-z0-9_]*[Pp]icker[A-Za-z0-9_]*)"'),
  "aimn/chat": re.compile(r'"([A-Za-z0-9_]*(?:[Aa]imn|[Cc]hat[Ii]nput|[Cc]hat[Bb]ar)[A-Za-z0-9_]*)"'),
  "model 相关": re.compile(r'"([A-Za-z0-9_]*[Mm]odel[A-Za-z0-9_]{3,})"'),
}
for f in sorted(js.glob("*.js")):
    t = f.read_text(encoding="utf-8", errors="ignore")
    if "odel" not in t and "icker" not in t: continue
    print(f"\n== {f.name}")
    for name,pat in pats.items():
        c = collections.Counter(pat.findall(t))
        hits = [k for k,v in c.most_common(14) if any(x in k.lower() for x in ["model","picker","aimn","chatinput","chatbar"])]
        if hits: print(f"  [{name}] " + ", ".join(hits[:14]))
