import json
from pathlib import Path
import html
import datetime

ROOT = Path(__file__).resolve().parent.parent

INPUT_JSON = ROOT / "data" / "wcag_w3c.json"
OUTPUT_DIR = ROOT / "docs"
OUTPUT_HTML = OUTPUT_DIR / "index.html"


# -------------------------
# Helpers
# -------------------------

def safe(value):
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def render_text_block(text):
    if not text:
        return ""
    return f"<p>{safe(text)}</p>"


def render_list(items):
    if not items:
        return "<p class='muted'>—</p>"
    lis = "".join(f"<li>{safe(i)}</li>" for i in items)
    return f"<ul>{lis}</ul>"


# -------------------------
# Renderização de técnicas
# -------------------------

def render_technique(t):
    title = safe(t.get("title", ""))
    tid = safe(t.get("id", ""))

    body = ""
    if "using" in t:
        body = "<div class='using'>" + render_techniques(t["using"]) + "</div>"

    return f"""
    <li>
      <strong>{tid}</strong> — {title}
      {body}
    </li>
    """


def render_techniques(techniques):
    if not techniques:
        return "<p class='muted'>—</p>"

    out = "<ul>"
    for t in techniques:
        if "and" in t:
            out += "<li><em>Todos:</em><ul>"
            for sub in t["and"]:
                out += render_technique(sub)
            out += "</ul></li>"
        elif "situations" in t:
            for s in t["situations"]:
                out += f"<li><strong>{safe(s.get('title'))}</strong>"
                out += render_techniques(s.get("techniques", []))
                out += "</li>"
        else:
            out += render_technique(t)
    out += "</ul>"
    return out


def render_techniques_block(techniques):
    if not techniques:
        return ""

    sections = []
    for block in techniques:
        if "sufficient" in block:
            sections.append(
                "<section><h5>Técnicas suficientes</h5>"
                + render_techniques(block["sufficient"])
                + "</section>"
            )
        if "advisory" in block:
            sections.append(
                "<section><h5>Técnicas aconselhadas</h5>"
                + render_techniques(block["advisory"])
                + "</section>"
            )
        if "failure" in block:
            sections.append(
                "<section><h5>Falhas comuns</h5>"
                + render_techniques(block["failure"])
                + "</section>"
            )

    return "".join(sections)


# -------------------------
# Critérios de Sucesso
# -------------------------

def render_success_criterion(sc):
    details_html = ""
    if "details" in sc:
        for d in sc["details"]:
            if d.get("type") == "ulist":
                details_html += render_list(
                    [i.get("text", "") for i in d.get("items", [])]
                )

    return f"""
    <article class="criterion" id="{safe(sc.get('num'))}">
      <h4>{safe(sc.get('num'))} — {safe(sc.get('handle'))}</h4>
      <p class="level">Nível {safe(sc.get('level', ''))}</p>
      {render_text_block(sc.get('title'))}
      {details_html}
      {render_techniques_block(sc.get('techniques', []))}
    </article>
    """


# -------------------------
# Diretrizes
# -------------------------

def render_guideline(g):
    criteria = "".join(
        render_success_criterion(sc)
        for sc in g.get("successcriteria", [])
    )

    return f"""
    <section class="guideline" id="{safe(g.get('num'))}">
      <h3>{safe(g.get('num'))} — {safe(g.get('handle'))}</h3>
      {render_text_block(g.get('title'))}
      {criteria}
    </section>
    """


# -------------------------
# Princípio
# -------------------------

def render_principle(p):
    guidelines_html = "".join(
        render_guideline(g) for g in p.get("guidelines", [])
    )

    return f"""
    <section class="principle" id="{safe(p.get('num'))}">
      <h2>{safe(p.get('num'))} — {safe(p.get('handle'))}</h2>
      {render_text_block(p.get('title'))}
      {guidelines_html}
    </section>
    """


# -------------------------
# Main
# -------------------------

def main():
    if not INPUT_JSON.exists():
        raise FileNotFoundError(INPUT_JSON)

    data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))

    generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    content = render_principle(data)

    html_doc = f"""<!doctype html>
<html lang="pt-PT">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WCAG — Revisão</title>
  <style>
    body {{ font-family: system-ui, sans-serif; line-height: 1.6; margin: 2rem; }}
    h1, h2, h3, h4 {{ line-height: 1.25; }}
    .muted {{ color: #666; }}
    .level {{ font-weight: bold; }}
    section {{ margin-bottom: 2rem; }}
    article {{ border-left: 4px solid #ddd; padding-left: 1rem; margin-bottom: 1.5rem; }}
    ul {{ margin-left: 1.5rem; }}
  </style>
</head>
<body>

<h1>WCAG — Revisão</h1>
<p class="muted">Gerado em {safe(generated_at)} a partir de <code>data/wcag_w3c.json</code></p>

{content}

</body>
</html>
"""

    OUTPUT_HTML.write_text(html_doc, encoding="utf-8")


if __name__ == "__main__":
    main()
