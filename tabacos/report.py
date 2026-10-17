"""A Markdown report in this repo -> one static page (index.html plus its images) for the website.

    uv run --group report python -m tabacos.report docs/learnings.md OUT_DIR [--draft]
"""
import html
import posixpath
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

REPO = "https://github.com/OrsM/tabacos"


class DraftError(Exception):
    pass


@dataclass
class Page:
    title: str
    description: str
    draft: bool
    html: str
    images: list[str]  # repo-relative paths, copied beside index.html


def _relative(url):
    return not re.match(r"^([a-z][a-z0-9+.-]*:|#|/)", url)


class _Paths(Treeprocessor):
    def __init__(self, md, source, repo, images):
        super().__init__(md)
        self.base, self.repo, self.images = posixpath.dirname(source), repo, images

    def run(self, root):
        for el in root.iter():
            if el.tag == "a" and _relative(el.get("href", "")):
                path = posixpath.normpath(posixpath.join(self.base, el.get("href")))
                el.set("href", f"{self.repo}/blob/main/{path}")
            if el.tag == "img" and _relative(el.get("src", "")):
                path = posixpath.normpath(posixpath.join(self.base, el.get("src")))
                self.images.append(path)
                el.set("src", posixpath.basename(path))


class _PathsExtension(Extension):
    def __init__(self, source, repo, images):
        super().__init__()
        self.args = source, repo, images

    def extendMarkdown(self, md):
        md.treeprocessors.register(_Paths(md, *self.args), "paths", 0)


def render(text, source, repo=REPO):
    """Render the Markdown at repo-relative path `source`. Title is the first `# ` line; the description
    (the one line shown on the home page) is a `<!-- description: ... -->` comment; a paragraph starting
    `*Draft` marks the document as a draft."""
    title = re.search(r"^# (.+)$", text, re.M)
    description = re.search(r"<!--\s*description:\s*(.*?)\s*-->", text, re.S)
    if not title or not description:
        raise ValueError(f"{source}: needs a '# Title' line and a <!-- description: ... --> comment")
    body = text.replace(title.group(0), "", 1).replace(description.group(0), "", 1)
    images = []
    content = markdown.markdown(body, extensions=["tables", "toc", _PathsExtension(source, repo, images)])
    t, d = html.escape(title.group(1).strip()), html.escape(description.group(1))
    page = TEMPLATE.format(title=t, description=d, content=content, repo=repo, source=source)
    return Page(t, d, bool(re.search(r"^\*Draft", text, re.M)), page, images)


def publish(root, source, out, draft=False):
    """Write index.html and the images it uses into `out`. A draft is refused unless draft=True."""
    root, out = Path(root), Path(out)
    page = render((root / source).read_text(), source)
    if page.draft and not draft:
        raise DraftError(f"{source} is still marked *Draft*; remove that note to publish, or pass --draft")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "index.html").write_text(page.html)
    for image in page.images:
        shutil.copy(root / image, out / posixpath.basename(image))
    return page


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="icon" href="/favicon-32.png">
<style>
:root {{ --bg: #fff; --text: #111; --muted: #666; --border: #e0e0e0; --subtle: #f5f5f5; color-scheme: light; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg: #111; --text: #ededed; --muted: #9a9a9a; --border: #2c2c2c; --subtle: #1c1c1c; color-scheme: dark; }}
}}
body {{ margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.65 'Inter', system-ui, -apple-system, sans-serif; }}
main {{ max-width: 680px; margin: 0 auto; padding: 48px 24px 64px; }}
h1 {{ font-size: 26px; font-weight: 600; letter-spacing: -0.02em; line-height: 1.25; }}
h2 {{ font-size: 18px; font-weight: 600; margin-top: 2.2em; }}
a {{ color: inherit; text-underline-offset: 2px; }}
code {{ font-size: 0.88em; background: var(--subtle); padding: 1px 4px; border-radius: 4px; }}
img {{ max-width: 100%; height: auto; }}
table {{ border-collapse: collapse; font-size: 14px; display: block; overflow-x: auto; }}
th, td {{ border-bottom: 1px solid var(--border); padding: 4px 10px 4px 0; text-align: left; }}
li {{ margin-bottom: 0.5em; }}
nav, footer {{ font-size: 13px; color: var(--muted); }}
footer {{ margin-top: 56px; padding-top: 16px; border-top: 1px solid var(--border); }}
</style>
</head>
<body>
<main>
<nav><a href="/">🍋 Lemon Worlds</a></nav>
<h1>{title}</h1>
{content}
<footer>
<p>Source: monthly reports of the <a href="https://www.hacienda.gob.es/Tabacos/">Comisionado para el Mercado de Tabacos</a>,
BOE tax law and BOE retail-price resolutions, reused under Ley 37/2007 with attribution; values as published.</p>
<p>Code, data pipeline and every analysis: <a href="{repo}">{repo}</a>
(this page is <a href="{repo}/blob/main/{source}">{source}</a>).</p>
</footer>
</main>
</body>
</html>
"""


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--draft"]
    if len(args) != 2:
        sys.exit(__doc__)
    root = Path(__file__).resolve().parent.parent
    try:
        page = publish(root, args[0], args[1], draft="--draft" in sys.argv)
    except DraftError as e:
        sys.exit(str(e))
    print(f"{args[1]}: {page.title}" + (" (DRAFT)" if page.draft else ""))
