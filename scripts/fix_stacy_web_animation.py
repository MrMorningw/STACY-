from pathlib import Path

path = Path("android/app/src/main/assets/stacy_prototipo36.html")
text = path.read_text(encoding="utf-8")
old = "pesquisando:0,executando:0,respondendo:0"
new = "pesquisando:1,executando:1,respondendo:2"
if old not in text:
    if new in text:
        print("STACY web animation already patched")
    else:
        raise SystemExit("STACY web animation definition not found")
else:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("STACY web animation patched: pesquisando=1, executando=1, respondendo=2")
