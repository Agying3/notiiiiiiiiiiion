import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["autoConvert","autoStart","auto_start","BusinessTrialAutoConvert","autoConvertPreview","trialAutoConvert"]:
    ms=list(re.finditer(re.escape(k), t))
    print(f"== {k}: {len(ms)}")
    for m in ms[:2]:
        print("   ", re.sub(r"\s+"," ", t[max(0,m.start()-200):m.end()+300])[:460])
