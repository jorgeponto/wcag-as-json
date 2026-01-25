import json
from pathlib import Path
import html
import datetime

ROOT = Path(__file__).resolve().parent.parent

INPUT_JSON = ROOT / "wcag_pt-PT.json"
OUTPUT_DIR = ROOT / "docs"
OUTPUT_HTML = OUTPUT_DIR / "index.html"


def safe(s):
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def render_value(v):
    if v is None:
        return "<span class='muted'>—</span>"
    if isinstance(v, (int, float, bool)):
        return safe(v)
    if isinstance(v, str):
        return safe(v)
    if isinstance(v, list):
        if not v:
            return "<span class='muted'>[]</span>"
        items = "".join(f"<li>{render_value(x)}</li>" for x in v)
        return f"<ul class='inline-list'>{items}</ul>"
    if isinstance(v, dict):
        if not v:
            return "<span class='muted'>{{}}</span>"
        rows = "".join(
            f"<tr><th>{safe(k)}</th><td>{render_value(val)}</td></tr>"
            for k, val in v.items()
        )
        return f"<table class='kv'>{rows}</table>"
    return safe(v)


def main():
    data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))

    generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

    # Tentativa de inferir uma lista principal (depende do formato do JSON)
    # Se o topo for lista: assume que cada item é um "critério"
    # Se o topo for dict: tenta encontrar uma lista "criterios" ou similar
    items = None
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ["criterios", "criteria", "items", "wcag", "successCriteria"]:
            if key in data and isinstance(data[key], list):
                items = data[key]
                break

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Renderização de fallback (se não encontrarmos uma lista principal)
    if items is None:
        body = f"""
        <h1>WCAG pt-PT — Revisão</h1>
        <p class="meta">Gerado em {safe(generated_at)} a partir de <code>wcag_pt-PT.json</code>.</p>
        <p class="warn">Não foi possível inferir uma lista principal de itens. A mostrar o JSON completo.</p>
        <details open>
          <summary>JSON completo</summary>
          <pre>{safe(json.dumps(data, ensure_ascii=False, indent=2))}</pre>
        </details>
        """
    else:
        cards = []
        for i, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                cards.append(
                    f"<section class='card'><h2>Item {i}</h2><pre>{safe(item)}</pre></section>"
                )
                continue

            # Tenta detetar campos “bons” para título
            title = (
                item.get("id")
                or item.get("criterio")
                or item.get("criterion")
                or item.get("numero")
                or item.get("number")
                or f"Item {i}"
            )

            # E um subtítulo “bom”
            subtitle = item.get("titulo") or item.get("title") or item.get("nome") or ""

            # Mostra tudo numa tabela key-value
            rows = "".join(
                f"<tr><th>{safe(k)}</th><td>{render_value(v)}</td></tr>"
                for k, v in item.items()
            )

            cards.append(
                f"""
                <section class="card" id="item-{i}">
                  <header class="card-header">
                    <h2>{safe(title)}</h2>
                    <p class="subtitle">{safe(subtitle)}</p>
                  </header>
                  <div class="card-body">
                    <table class="kv">{rows}</table>
                  </div>
                </section>
                """
            )

        body = f"""
        <h1>WCAG pt-PT — Revisão</h1>
        <p class="meta">Gerado em {safe(generated_at)} a partir de <code>wcag_pt-PT.json</code>.</p>

        <div class="toolbar">
          <label for="q">Pesquisar</label>
          <input id="q" type="search" placeholder="Ex.: 1.1.1, texto, AAA..." />
          <p class="hint">Dica: pesquisa em texto (client-side).</p>
        </div>

        <main id="cards">
          {''.join(cards)}
        </main>
        """

    html_doc = f"""<!doctype html>
<html lang="pt-PT">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WCAG pt-PT — Revisão</title>
  <style>
    :root {{
      --bg: #ffffff;
      --fg: #111;
      --muted: #666;
      --border: #ddd;
      --card: #fafafa;
      --focus: #005fcc;
      --warn: #8a2a00;
      --max: 1100px;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      line-height: 1.5;
    }}
    header, main, .toolbar {{
      max-width: var(--max);
      margin: 0 auto;
      padding: 16px;
    }}
    h1 {{
      font-size: 1.8rem;
      margin: 0 0 8px 0;
    }}
    .meta {{
      margin: 0 0 16px 0;
      color: var(--muted);
    }}
    .toolbar {{
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      display: grid;
      gap: 8px;
    }}
    label {{
      font-weight: 600;
    }}
    input[type="search"] {{
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      font-size: 1rem;
    }}
    input[type="search"]:focus {{
      outline: 3px solid rgba(0, 95, 204, .35);
      border-color: var(--focus);
    }}
    .hint {{
      margin: 0;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .warn {{
      color: var(--warn);
      font-weight: 600;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      margin: 12px 0;
    }}
    .card-header h2 {{
      font-size: 1.25rem;
      margin: 0;
    }}
    .subtitle {{
      margin: 6px 0 0 0;
      color: var(--muted);
    }}
    table.kv {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }}
    table.kv th {{
      text-align: left;
      vertical-align: top;
      width: 220px;
      padding: 8px 10px;
      border-top: 1px solid var(--border);
      color: #222;
      font-weight: 700;
    }}
    table.kv td {{
      padding: 8px 10px;
      border-top: 1px solid var(--border);
    }}
    .muted {{
      color: var(--muted);
    }}
    ul.inline-list {{
      margin: 0;
      padding-left: 18px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      overflow: auto;
    }}
  </style>
</head>
<body>
  {body}

  <script>
    (function() {{
      const q = document.getElementById('q');
      const cards = document.getElementById('cards');
      if (!q || !cards) return;

      const items = Array.from(cards.querySelectorAll('.card'));
      q.addEventListener('input', () => {{
        const term = (q.value || '').trim().toLowerCase();
        for (const el of items) {{
          const text = el.innerText.toLowerCase();
          el.style.display = term === '' || text.includes(term) ? '' : 'none';
        }}
      }});
    }})();
  </script>
</body>
</html>
"""

    OUTPUT_HTML.write_text(html_doc, encoding="utf-8")
    print(f"OK: gerado {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
