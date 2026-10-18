import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 模型名常量（sonnet/gemini/grok/gpt）附近的选择器逻辑
from collections import Counter
models = Counter()
for m in re.finditer(r'"((?:claude|gemini|grok|gpt|o3|o4)[A-Za-z0-9_\-\.]{0,40})"', t, re.I):
    models[m.group(1)] += 1
for k,v in models.most_common(30): print(f"{v:>3}  {k}")
