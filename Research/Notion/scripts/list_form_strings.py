import re, pathlib, collections
p = pathlib.Path(r"REPO_ROOT")
t = p.read_text(encoding="utf-8", errors="ignore")
# 所有 /api/v3 之外的动作名，找 questionnaire / form
c = collections.Counter(re.findall(r'"([a-zA-Z]*(?:[Qq]uestionnaire|[Ff]orm|[Ss]urvey|[Pp]oll)[a-zA-Z]*)"', t))
for k,v in c.most_common(40): print(f"{v:>3}  {k}")
print("----")
c2 = collections.Counter(re.findall(r'"([a-zA-Z]*(?:[Ii]ntent|persona|Persona)[a-zA-Z]*)"', t))
for k,v in c2.most_common(30): print(f"{v:>3}  {k}")
