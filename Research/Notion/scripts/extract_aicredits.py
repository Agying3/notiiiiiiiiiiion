import re, pathlib, json
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
i = t.find("aiCredits")
print("offset:", i, "len:", len(t))
blk = t[i-20:i+3000]
# 插入换行便于阅读
pretty = blk.replace("},", "},\n").replace("{", "{\n  ").replace("}", "\n}")
print(pretty[:4000])
