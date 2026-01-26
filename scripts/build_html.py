import json
from pathlib import Path
import html
import datetime

ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "data" / "wcag_w3c.json"
OUTPUT_DIR = ROOT / "docs"
OUTPUT_HTML = OUTPUT_DIR / "index.html"


def esc(s):
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


# ---------- RENDERIZAÇÃO DE CONTEÚDO ----------

def render_details(details):
    if not details:
        return ""
    out = []
    for block in details:
        if block.get("type") == "ulist":
            items = "".join(
                f"<li><strong>{esc(i.get('handle'))}:</strong> {esc(i.get('text'))}</li>"
                for i in block.get("items", [])
            )
            out.append(f"<ul>{items}</ul>")
    return "".join(out)


def render_technique_item(t):
    if "and" in t:
        return "<ul>" + "".join(render_technique_item(x) for x in t["and"]) + "</ul>"

    tid = esc(t.get("id", ""))
    title = esc(t.get("title", ""))
    using = t.get("using")

    html_out = f"<li><code>{tid}</code> — {title}"
    if using:
        html_out += "<ul>" + "".join(render_technique_item(u) for u in using) + "</ul>"
    html_out += "</li>"
    return html_out


def render_techniques(techniques):
    if not techniques:
        return ""

    sections = []

    for group in techniques:
        if group.get("sufficient"):
            sections.append(render_tech_group(
                "Técnicas Suficientes",
                group["sufficient"]
            ))

        if group.get("advisory"):
            sections.append(render_tech_group(
                "Técnicas de Apoio",
                group["advisory"]
            ))

        if group.get("failure"):
            sections.append(render_tech_group(
                "Falhas Comuns",
                group["failure"]
            ))

    return "".join(sections)


def render_tech_group(label, items):
    if not items:
        return ""

    blocks = []

    for item in items:
        if "situations" in item:
            for s in item["situations"]:
                blocks.append(f"<h5>{esc(s.get('title'))}</h5>")
                blocks.append(
                    "<ul>" +
                    "".join(render_technique_item(t) for t in s.get("techniques", [])) +
                    "</ul>"
                )
        else:
            blocks.append("<ul>" + render_technique_item(item) + "</ul>")

    return f"""
    <details>
      <summary>{label}</summary>
      {''.join(blocks)}
    </details>
    """


def render_criterion(c):
    num = esc(c.get("num"))
    return f"""
    <article class="criterion" id="{num}">
      <h4>{num} — {esc(c.get('handle'))}
        <span class="level">{esc(c.get('level'))}</span>
      </h4>
      <p>{esc(c.get('title'))}</p>

      {render_details(c.get("details"))}
      {render_techniques(c.get("techniques"))}
    </article>
    """


def render_guideline(g):
    criteria = "".join(render_criterion(c) for c in g.get("successcriteria", []))
    num = esc(g.get("num"))
    return f"""
    <section class="guideline" id="{num}">
      <h3>{num} — {esc(g.get('handle'))}</h3>
      <p>{esc(g.get('title'))}</p>
      {criteria}
    </section>
    """


def render_principle(p):
    guidelines = "".join(render_guideline(g) for g in p.get("guidelines", []))
    num = esc(p.get("num"))
    return f"""
    <section class="principle" id="{num}">
      <h2>{num} — {esc(p.get('handle'))}</h2>
      <p>{esc(p.get('title'))}</p>
      {guidelines}
    </section>
    """


# ---------- ÍNDICE LATERAL ----------

def build_sidebar(principles):
    out = ["<nav class='sidebar'><ul>"]

    for p in principles:
        pnum = esc(p.get("num"))
        out.append(f"<li><a href='#{pnum}'>Princípio {pnum}</a><ul>")

        for g in p.get("guidelines", []):
            gnum = esc(g.get("num"))
            out.append(f"<li><a href='#{gnum}'>Diretriz {gnum}</a><ul>")

            for c in g.get("successcriteria", []):
                cnum = esc(c.get("num"))
                out.append(
                    f"<li><a href='#{cnum}'>Critério {cnum}</a></li>"
                )

            out.append("</ul></li>")

        out.append("</ul></li>")

    out.append("</ul></nav>")
    return "".join(out)


# ---------- MAIN ----------

def main():
    data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    principles = data.get("principles", [])

    generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

    sidebar = build_sidebar(principles)
    content = "".join(render_principle(p) for p in principles)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    OUTPUT_HTML.write_text(f"""<!doctype html>
<html lang="pt-PT">
<head>
  <meta charset="utf-8">
  <title>WCAG — Revisão</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <style>
    body {{
      margin: 0;
      font-family: system-ui, sans-serif;
      line-height: 1.6;
      display: grid;
      grid-template-columns: 20rem 1fr;
    }}

    .sidebar {{
      padding: 1rem;
      border-right: 1px solid #ccc;
      height: 100vh;
      overflow-y: auto;
      background: #f9f9f9;
    }}

    main {{
      padding: 2rem;
      overflow-y: auto;
      height: 100vh;
    }}

    h1, h2, h3, h4 {{ line-height: 1.25; }}
    section {{ margin-bottom: 2.5rem; }}
    article {{ border-left: 4px solid #ddd; padding-left: 1rem; margin: 1.5rem 0; }}

    nav ul {{ list-style: none; padding-left: 1rem; }}
    nav a {{ text-decoration: none; }}
    nav a:hover {{ text-decoration: underline; }}

    .level {{ font-weight: bold; margin-left: .5rem; }}
    details {{ margin: 1rem 0; }}
  </style>
</head>
<body>

{sidebar}

<main>
  <h1>WCAG — Revisão</h1>
  <p><small>Gerado em {esc(generated_at)} a partir de <code>data/wcag_w3c.json</code></small></p>
  {content}
</main>

</body>
</html>
""", encoding="utf-8")


if __name__ == "__main__":
    main()
