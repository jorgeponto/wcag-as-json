import json
from pathlib import Path
import html
import datetime
import re

ROOT = Path(__file__).resolve().parent.parent

# ✅ Novo ficheiro de input (W3C)
INPUT_JSON = ROOT / "data" / "wcag_w3c.json"

OUTPUT_DIR = ROOT / "docs"
OUTPUT_HTML = OUTPUT_DIR / "index.html"


def safe(s):
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def slugify(text: str) -> str:
    """
    Gera um id seguro para âncoras em HTML.
    """
    if not text:
        return "node"
    text = str(text).strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-\:\._]", "", text)
    return text or "node"


def render_inline_list(values):
    if not values:
        return "<span class='muted'>—</span>"
    items = "".join(f"<li>{safe(v)}</li>" for v in values)
    return f"<ul class='inline-list'>{items}</ul>"


def render_details(details):
    """
    Espera estrutura como:
    "details": [{"type": "ulist", "items": [{"handle": "...", "text": "..."}]}]
    """
    if not details:
        return ""

    out = []
    for block in details:
        if not isinstance(block, dict):
            continue

        btype = block.get("type")

        if btype == "ulist":
            items = block.get("items", [])
            if isinstance(items, list) and items:
                lis = []
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    handle = it.get("handle")
                    text = it.get("text")
                    if handle and text:
                        lis.append(f"<li><strong>{safe(handle)}:</strong> {safe(text)}</li>")
                    elif text:
                        lis.append(f"<li>{safe(text)}</li>")
                    elif handle:
                        lis.append(f"<li><strong>{safe(handle)}</strong></li>")
                if lis:
                    out.append(f"<ul>{''.join(lis)}</ul>")
        else:
            # fallback
            out.append(f"<pre class='json'>{safe(json.dumps(block, ensure_ascii=False, indent=2))}</pre>")

    return "\n".join(out)


def render_technique_item(t):
    """
    Renderiza uma técnica individual ou um bloco complexo:
    - {id,title}
    - {id,title,using:[...]}
    - {"and":[...]}
    """
    if not isinstance(t, dict):
        return f"<li><pre class='json'>{safe(t)}</pre></li>"

    # Caso AND (lista de técnicas)
    if "and" in t and isinstance(t["and"], list):
        inner = "".join(render_technique_item(x) for x in t["and"])
        return f"<li><div class='tech-and'><strong>Conjunto (AND)</strong><ul>{inner}</ul></div></li>"

    tid = t.get("id")
    title = t.get("title")

    header = []
    if tid:
        header.append(f"<code class='tag'>{safe(tid)}</code>")
    if title:
        header.append(f"<span>{safe(title)}</span>")

    header_html = " ".join(header) if header else "<span class='muted'>Técnica</span>"

    # Render "using" (pode conter lista de técnicas ou "and")
    using_html = ""
    using = t.get("using")
    if isinstance(using, list) and using:
        using_items = "".join(render_technique_item(x) for x in using)
        using_html = f"""
          <details class="using">
            <summary>Usando</summary>
            <ul>{using_items}</ul>
          </details>
        """

    return f"<li class='tech-item'>{header_html}{using_html}</li>"


def render_techniques(techniques):
    """
    Espera estrutura como:
    "techniques": [
        {"sufficient":[ ... ]},
        {"advisory":[ ... ]},
        {"failure":[ ... ]}
    ]
    """
    if not techniques or not isinstance(techniques, list):
        return ""

    sections = []

    for block in techniques:
        if not isinstance(block, dict):
            continue

        for k in ["sufficient", "advisory", "failure"]:
            if k not in block:
                continue

            items = block.get(k)
            if not items:
                continue

            label = {
                "sufficient": "Técnicas suficientes",
                "advisory": "Técnicas aconselhadas",
                "failure": "Falhas comuns",
            }.get(k, k)

            rendered = []

            # "sufficient" pode conter objetos com "situations"
            if isinstance(items, list):
                for entry in items:
                    if not isinstance(entry, dict):
                        rendered.append(f"<li><pre class='json'>{safe(entry)}</pre></li>")
                        continue

                    # Caso "situations"
                    if "situations" in entry and isinstance(entry["situations"], list):
                        sit_html = []
                        for sit in entry["situations"]:
                            if not isinstance(sit, dict):
                                continue
                            stitle = sit.get("title")
                            stechs = sit.get("techniques", [])

                            inner = ""
                            if isinstance(stechs, list) and stechs:
                                inner_items = "".join(render_technique_item(x) for x in stechs)
                                inner = f"<ul>{inner_items}</ul>"

                            sit_html.append(
                                f"""
                                <li class="situation">
                                  <strong>{safe(stitle) if stitle else "Situação"}</strong>
                                  {inner}
                                </li>
                                """
                            )

                        rendered.append(f"<li><ul class='situations'>{''.join(sit_html)}</ul></li>")
                        continue

                    # Caso normal: lista de técnicas diretas
                    if "id" in entry or "and" in entry:
                        rendered.append(render_technique_item(entry))
                        continue

                    # fallback
                    rendered.append(f"<li><pre class='json'>{safe(json.dumps(entry, ensure_ascii=False, indent=2))}</pre></li>")

            if rendered:
                sections.append(
                    f"""
                    <section class="tech-group">
                      <h4>{safe(label)}</h4>
                      <ul class="tech-list">{''.join(rendered)}</ul>
                    </section>
                    """
                )

    if not sections:
        return ""

    return f"<div class='techniques'>{''.join(sections)}</div>"


def node_title(node):
    """
    Gera título humano para qualquer nó WCAG.
    """
    if not isinstance(node, dict):
        return "Nó"

    num = node.get("num")
    handle = node.get("handle")
    title = node.get("title")

    parts = []
    if num:
        parts.append(str(num))
    if handle:
        parts.append(str(handle))
    elif title:
        parts.append(str(title))

    if parts:
        return " — ".join(parts)

    return node.get("id") or "Nó"


def node_subtitle(node):
    """
    Subtitle extra (por ex. nível, versões, alt_id, id).
    """
    if not isinstance(node, dict):
        return ""

    level = node.get("level")
    versions = node.get("versions", [])
    alt_id = node.get("alt_id", [])
    nid = node.get("id")

    out = []
    if level is not None and str(level).strip() != "":
        out.append(f"Nível {safe(level)}")
    if isinstance(versions, list) and versions:
        out.append("WCAG " + ", ".join(safe(v) for v in versions))
    if isinstance(alt_id, list) and alt_id:
        out.append("Alt IDs: " + ", ".join(safe(x) for x in alt_id))
    if nid:
        out.append(f"ID: {safe(nid)}")

    return " · ".join(out)


def node_anchor_id(node):
    """
    Usa preferencialmente o id WCAG (ex.: WCAG2:robust)
    senão num (ex.: 1.2.1), senão fallback.
    """
    if not isinstance(node, dict):
        return "node"

    return slugify(node.get("id") or node.get("num") or node.get("handle") or node.get("title") or "node")


def render_node(node, depth=1):
    """
    Render recursivo:
    - render header (title + subtitle)
    - render details, techniques
    - render children: guidelines / successcriteria
    """
    if not isinstance(node, dict):
        return f"<section class='card'><pre class='json'>{safe(node)}</pre></section>"

    nid = node_anchor_id(node)
    title = node_title(node)
    subtitle = node_subtitle(node)

    details_html = render_details(node.get("details"))
    techniques_html = render_techniques(node.get("techniques"))

    # children
    children_html = []

    if "guidelines" in node and isinstance(node["guidelines"], list) and node["guidelines"]:
        for g in node["guidelines"]:
            children_html.append(render_node(g, depth=depth + 1))

    if "successcriteria" in node and isinstance(node["successcriteria"], list) and node["successcriteria"]:
        for sc in node["successcriteria"]:
            children_html.append(render_node(sc, depth=depth + 1))

    # Compose
    return f"""
    <section class="card depth-{depth}" id="{safe(nid)}">
      <header class="card-header">
        <h2>{safe(title)}</h2>
        {"<p class='subtitle'>" + safe(subtitle) + "</p>" if subtitle else ""}
      </header>

      <div class="card-body">
        {f"<div class='details'>{details_html}</div>" if details_html else ""}
        {techniques_html}
        {f"<div class='children'>{''.join(children_html)}</div>" if children_html else ""}
      </div>
    </section>
    """


def build_toc(nodes):
    """
    TOC simples (apenas nível topo).
    """
    if not isinstance(nodes, list) or not nodes:
        return ""

    links = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        anchor = node_anchor_id(n)
        label = node_title(n)
        links.append(f"<li><a href='#{safe(anchor)}'>{safe(label)}</a></li>")

    if not links:
        return ""

    return f"""
    <nav class="toc" aria-label="Índice">
      <h2>Índice</h2>
      <ul>
        {''.join(links)}
      </ul>
    </nav>
    """


def main():
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"Não existe o ficheiro: {INPUT_JSON}")

    data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    input_filename_label = "data/wcag_w3c.json"

    # ✅ Esperado: lista no topo (princípios ou blocos)
    if not isinstance(data, list):
        body = f"""
        <h1>WCAG — Revisão</h1>
        <p class="meta">Gerado em {safe(generated_at)} a partir de <code>{safe(input_filename_label)}</code>.</p>
        <p class="warn">O JSON não é uma lista no topo. A mostrar JSON completo.</p>
        <details open>
          <summary>JSON completo</summary>
          <pre class="json">{safe(json.dumps(data, ensure_ascii=False, indent=2))}</pre>
        </details>
        """
    else:
        toc = build_toc(data)
        content = "".join(render_node(n, depth=1) for n in data)

        body = f"""
        <h1>WCAG — Revisão</h1>
        <p class="meta">Gerado em {safe(generated_at)} a partir de <code>{safe(input_filename_label)}</code>.</p>

        <div class="toolbar">
          <label for="q">Pesquisar</label>
          <input id="q" type="search" placeholder="Ex.: 1.1.1, 4.1.2, Nome, Papel..." />
          <p class="hint">Pesquisa em texto (client-side).</p>
        </div>

        {toc}

        <main id="cards">
          {content}
        </main>
        """

    html_doc = f"""<!doctype html>
<html lang="pt-PT">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WCAG — Revisão</title>
  <style>
    :root {{
      --fg: #111;
      --bg: #fff;
      --muted: #6b7280;
      --border: #e5e7eb;
      --card: #ffffff;
      --shadow: 0 1px 8px rgba(0,0,0,.06);
      --radius: 14px;
    }}

    body {{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      margin: 0;
      padding: 24px;
      color: var(--fg);
      background: var(--bg);
      line-height: 1.4;
    }}

    h1 {{
      margin: 0 0 8px 0;
      font-size: 28px;
    }}

    .meta {{
      margin: 0 0 16px 0;
      color: var(--muted);
      font-size: 14px;
    }}

    .warn {{
      padding: 12px 14px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: #fff7ed;
    }}

    .toolbar {{
      display: grid;
      gap: 8px;
      margin: 16px 0 16px 0;
      padding: 12px 14px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: #fafafa;
    }}

    .toolbar label {{
      font-weight: 600;
    }}

    .toolbar input {{
      padding: 10px 12px;
      font-size: 16px;
      border: 1px solid var(--border);
      border-radius: 10px;
    }}

    .hint {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }}

    .toc {{
      margin: 16px 0 18px 0;
      padding: 12px 14px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: #fafafa;
    }}

    .toc h2 {{
      font-size: 18px;
      margin: 0 0 8px 0;
    }}

    .toc ul {{
      margin: 0;
      padding-left: 18px;
    }}

    .card {{
      border: 1px solid var(--border);
      background: var(--card);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 14px 16px;
      margin: 14px 0;
    }}

    .card-header h2 {{
      font-size: 18px;
      margin: 0;
    }}

    .subtitle {{
      margin: 4px 0 0 0;
      color: var(--muted);
      font-size: 13px;
    }}

    .details {{
      margin-top: 10px;
    }}

    .children {{
      margin-top: 12px;
      border-left: 3px solid var(--border);
      padding-left: 12px;
    }}

    .depth-2 {{ margin-top: 12px; }}
    .depth-3 {{ margin-top: 10px; }}
    .depth-4 {{ margin-top: 10px; }}

    .tag {{
      display: inline-block;
      padding: 2px 6px;
      border: 1px solid var(--border);
      border-radius: 999px;
      font-size: 12px;
      background: #f3f4f6;
      margin-right: 6px;
      vertical-align: middle;
    }}

    .muted {{
      color: var(--muted);
    }}

    .json {{
      overflow: auto;
      padding: 12px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: #0b1020;
      color: #e5e7eb;
      font-size: 13px;
      line-height: 1.35;
    }}

    .techniques {{
      margin-top: 12px;
      display: grid;
      gap: 10px;
    }}

    .tech-group h4 {{
      margin: 0 0 6px 0;
      font-size: 14px;
    }}

    .tech-list {{
      margin: 0;
      padding-left: 18px;
    }}

    .tech-item {{
      margin: 6px 0;
    }}

    details.using {{
      margin: 6px 0 8px 0;
    }}

    details.using summary {{
      cursor: pointer;
      font-size: 13px;
      color: var(--muted);
    }}

    .situations {{
      margin: 6px 0;
      padding-left: 18px;
    }}

    .situation {{
      margin: 8px 0;
    }}

    a {{
      color: inherit;
      text-decoration: underline;
    }}

    a:focus {{
      outline: 3px solid #111;
      outline-offset: 3px;
    }}

    @media (prefers-reduced-motion: reduce) {{
      * {{
        scroll-behavior: auto !important;
      }}
    }}
  </style>
</head>
<body>
  {body}

  <script>
    // Pesquisa client-side: filtra cards pelo texto
    const q = document.getElementById('q');
    const cards = document.getElementById('cards');

    if (q && cards) {{
      q.addEventListener('input', () => {{
        const term = q.value.trim().toLowerCase();
        const all = Array.from(cards.querySelectorAll('.card'));
        all.forEach(card => {{
          const text = card.innerText.toLowerCase();
          card.style.display = text.includes(term) ? '' : 'none';
        }});
      }});
    }}
  </script>
</body>
</html>
"""

    OUTPUT_HTML.write_text(html_doc, encoding="utf-8")
    print(f"✅ HTML gerado em: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
