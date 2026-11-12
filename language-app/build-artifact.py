# Builds dist/index.html: a single self-contained page for publishing as a claude.ai Artifact
# (the host adds <html>/<head>/<body>; CSS and JS are inlined).
import re, pathlib
root = pathlib.Path(__file__).parent
dist = root / "dist"; dist.mkdir(exist_ok=True)
src = (root / "index.html").read_text()
head = re.search(r"<head>(.*?)</head>", src, re.S).group(1)
body = re.search(r"<body>(.*?)</body>", src, re.S).group(1)
head = "\n".join(l for l in head.splitlines() if not re.search(r'charset|name="viewport"|rel="manifest"|rel="icon"|theme-color', l))
css = (root / "css/app.css").read_text()
head = head.replace('<link rel="stylesheet" href="css/app.css">', "<style>\n" + css + "\n</style>")
body = re.sub(r"<script>\s*if \(\"serviceWorker\".*?</script>", "", body, flags=re.S)
def inline(m):
    code = (root / m.group(1)).read_text()
    assert "</script" not in code, m.group(1)
    return "<script>\n" + code + "\n</script>"
body = re.sub(r'<script src="([^"]+)"></script>', inline, body)
out = head.strip() + "\n" + body.strip() + "\n"
(dist / "index.html").write_text(out)
print("built", dist / "index.html", len(out) // 1024, "KB")
