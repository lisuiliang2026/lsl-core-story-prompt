# 把种子 + 假 Claude + 正式页面拼成一个本地测试页：tests/out/index.html
import json, pathlib
here = pathlib.Path(__file__).resolve().parent
base = here.parent
seed = json.load(open(base / "example-mengfusheng" / "seed.json", encoding="utf-8"))
mock = (here / "mock.js").read_text(encoding="utf-8").replace("SEED_PLACEHOLDER", json.dumps(seed, ensure_ascii=False))
page = (base / "web" / "workbench.html").read_text(encoding="utf-8")
out = here / "out"; out.mkdir(exist_ok=True)
html = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<script>' + mock + '</script></head><body>' + page + '</body></html>')
(out / "index.html").write_text(html, encoding="utf-8")
print("built", out / "index.html", len(html))
