import re, pathlib
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
for k in ["onboardingSurvey","surveyAnswers","onboardingAnswers","submitSurvey","saveSurvey","survey_","onboarding_answer"]:
    ms=list(re.finditer(re.escape(k), t, re.I))
    print(f"== {k} hits={len(ms)}")
    for m in ms[:3]:
        s=max(0,m.start()-200); e=min(len(t), m.end()+260)
        print("   ", re.sub(r"\s+"," ", t[s:e])[:440])
