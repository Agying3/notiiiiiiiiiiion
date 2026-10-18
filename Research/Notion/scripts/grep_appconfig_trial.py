import json, pathlib, re
p = pathlib.Path(r"REPO_ROOT")
d = json.loads(p.read_text(encoding="utf-8"))
for f in d:
    if f.get("endpoint")=="getAppConfig":
        body = f["resp_body"]
        # 在 initialValues 里搜 trial 相关 gate
        for kw in ["trial", "14", "30_day", "reverse"]:
            hits = [m.start() for m in re.finditer(kw, body, re.I)]
            print(f"{kw}: {len(hits)}")
        # 找 gate name 里带 trial 的
        for m in re.finditer(r'"([^"]{0,60}trial[^"]{0,60})":\{[^}]{0,200}\}', body, re.I):
            print("  GATE:", m.group(0)[:220])
        break
