import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 模型选择器的显隐条件：搜 model picker 开关相关 gate 名
for k in ["modelPicker","model_picker","premiumModel","premium_model","showModelPicker","modelSelection","aiModelsEnabled","modelSettings"]:
    ms=list(re.finditer(re.escape(k), t))
    print(f"== {k}: {len(ms)}")
    for m in ms[:3]:
        s=max(0,m.start()-220); e=min(len(t), m.end()+280)
        print("   ", re.sub(r"\s+"," ", t[s:e])[:480])
