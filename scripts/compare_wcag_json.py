import json
import re
import html
from pathlib import Path
from difflib import unified_diff
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

TENON_JSON = ROOT / "data" / "wcag_tenon.json"
W3C_JSON = ROOT / "data" / "wcag_w3c.json"

OUTPUT_DIR = ROOT / "docs"
OUTPUT_HTML = OUTPUT_DIR / "compare.html"
OUTPUT_JSON = OUTPUT_DIR / "compare.json"


ID_RE = re.compile(r"^\d+\.\d+\.\d+$")


def safe(s):
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def normalize_text(v):
    if v is None:
        return ""
    if isinstance(v, str):
        # normalização leve para comparar melhor
        return re.sub(r"\s+", " ", v.strip())
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def guess_items(data):
    """
    Encontra uma lista de itens que pareçam critérios ou entradas semelhantes.
    Suporta formatos diferentes (top-level list, ou dict com keys comuns).
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # tentativas típicas
        candidate_keys = [
            "successCriteria",
            "criteria",
            "criterios",
            "items",
            "wcag",
            "guidelines",
            "Guidelines",
        ]
        for k in candidate_keys:
            if k in data and isinstance(data[k], list):
                return data[k]

        # fallback: procurar listas dentro do dict
        for k, v in data.items():
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                return v

    return None


def extract_id(item):
    """
    Tenta extrair um identificador tipo "1.1.1".
    """
    if not isinstance(item, dict):
        return None

    candidates = [
        item.get("id"),
        item.get("scId"),
        item.get("successCriterion"),
        item.get("criterion"),
        item.get("numero"),
        item.get("number"),
    ]

    for c in candidates:
        if isinstance(c, str):
            c = c.strip()
            if ID_RE.match(c):
                return c

    # alguns JSON têm algo como "1.1.1 Non-text Content"
    for c in candidates:
        if isinstance(c, str):
            m = re.search(r"(\d+\.\d+\.\d+)", c)
            if m:
                return m.group(1)

    return None


def flatten_items(data):
    """
    Produz mapa { "1.1.1": item_dict, ... }.
    Ignora entradas sem ID reconhecível.
    """
    items = guess_items(data)
    out = {}

    if not items:
        return out

    for item in items:
        _id = extract_id(item)
        if _id:
            out[_id] = item

    return out


def diff_for_item(a, b, key_whitelist=None):
    """
    Produz diferenças por campo, com diff textual quando adequado.
    """
    diffs = []

    keys = set()
    if isinstance(a, dict):
        keys |= set(a.keys())
    if isinstance(b, dict):
        keys |= set(b.keys())

    if key_whitelist:
        keys = keys.intersection(set(key_whitelist))

    for k in sorted(keys):
        va = a.get(k) if isinstance(a, dict) else None
        vb = b.get(k) if isinstance(b, dict) else None

        ta = normalize_text(va)
        tb = normalize_text(vb)

        if ta != tb:
            # diff textual amigável quando forem strings “grandes”
            if isinstance(va, str) and isinstance(vb, str) and (len(va) + len(vb) > 80):
                d = "\n".join(
                    unified_diff(
                        va.splitlines(),
                        vb.splitlines(),
                        fromfile="tenon",
                        tofile="w3c",
                        lineterm="",
                    )
                )
                diffs.append({"field": k, "tenon": va, "w3c": vb, "diff": d})
            else:
                diffs.append({"field": k, "tenon": va, "w3c": vb, "diff": None})

    return diffs


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tenon = json.loads(TENON_JSON.read_text(encoding="utf-8"))
    w3c = json.loads(W3C_JSON.read_text(encoding="utf-8"))

    tenon_map = flatten_items(tenon)
    w3c_map = flatten_items(w3c)

    tenon_ids = set(tenon_map.keys())
    w3c_ids = set(w3c_map.keys())

    only_tenon = sorted(tenon_ids - w3c_ids)
    only_w3c = sorted(w3c_ids - tenon_ids)
    common = sorted(tenon_ids & w3c_ids)

    # whitelist opcional de campos que interessam mais para tradução
    interesting_fields = None
    # exemplo, se quiseres restringir:
    # interesting_fields = ["id", "title", "titulo", "name", "nivel", "level", "text", "texto"]

    changes = []

    for _id in common:
        a = tenon_map[_id]
        b = w3c_map[_id]
        diffs = diff_for_item(a, b, key_whitelist=interesting_fields)
        if diffs:
            changes.append({"id": _id, "diffs": diffs})

    report = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ"),
        "counts": {
            "tenon_items": len(tenon_map),
            "w3c_items": len(w3c_map),
            "only_tenon": len(only_tenon),
            "only_w3c": len(only_w3c),
            "changed_common": len(changes),
            "common_total": len(common),
        },
        "only_tenon": only_tenon,
        "only_w3c": only_w3c,
        "changes": changes,
    }

    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # HTML report
    def render_change_block(entry):
        blocks = []
        for d in entry["diffs"]:
            field = safe(d["field"])
            tenon_val = safe(json.dumps(d["tenon"], ensure_ascii=False, indent=2))
            w3c_val = safe(json.dumps(d["w3c"], ensure_ascii=False, indent=2))

            blocks.append(f"""
              <details class="field" open>
                <summary><strong>{field}</strong></summary>
                <div class="grid">
                  <div>
                    <h4>Tenon</h4>
                    <pre>{tenon_val}</pre>
                  </div>
                  <div>
                    <h4>W3C</h4>
                    <pre>{w3c_val}</pre>
                  </div>
                </div>
              </details>
            """)

        return f"""
          <section class="card" id="sc-{safe(entry['id'])}">
            <h3>{safe(entry['id'])}</h3>
            {''.join(blocks)}
          </section>
        """

    html_doc = f"""<!doctype html>
<html lang="pt-PT">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Comparação WCAG JSON (Tenon vs W3C)</title>
  <style>
    :root {{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      --border: #ddd;
      --muted: #666;
      --bg: #fff;
      --card: #fafafa;
      --max: 1200px;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: #111;
      line-height: 1.5;
    }}
    header, main {{
      max-width: var(--max);
      margin: 0 auto;
      padding: 16px;
    }}
    .summary {{
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px 14px;
      background: var(--card);
    }}
    .muted {{ color: var(--muted); }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border: 1px solid var(--border);
      border-radius: 999px;
      margin: 4px 6px 0 0;
      background: white;
    }}
    .card {{
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px 14px;
      margin: 12px 0;
      background: var(--card);
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      margin: 0;
    }}
    details.field {{
      margin-top: 10px;
    }}
    input[type="search"] {{
      width: 100%;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      font-size: 1rem;
      margin-top: 12px;
    }}
    .lists {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 12px;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Comparação WCAG JSON — Tenon vs W3C</h1>
    <p class="muted">Gerado em {safe(report["generated_at"])}.</p>

    <div class="summary">
      <div class="pill">Tenon (itens com ID): <strong>{report["counts"]["tenon_items"]}</strong></div>
      <div class="pill">W3C (itens com ID): <strong>{report["counts"]["w3c_items"]}</strong></div>
      <div class="pill">Só no Tenon: <strong>{report["counts"]["only_tenon"]}</strong></div>
      <div class="pill">Só no W3C: <strong>{report["counts"]["only_w3c"]}</strong></div>
      <div class="pill">Alterados (comuns): <strong>{report["counts"]["changed_common"]}</strong></div>
    </div>

    <input id="q" type="search" placeholder="Pesquisar (ex.: 1.1.1, 'texto', 'level')..." aria-label="Pesquisar diferenças" />

    <div class="lists">
      <div class="card">
        <h2>Só no Tenon</h2>
        <ul>{"".join(f"<li>{safe(x)}</li>" for x in only_tenon) or "<li class='muted'>—</li>"}</ul>
      </div>
      <div class="card">
        <h2>Só no W3C</h2>
        <ul>{"".join(f"<li>{safe(x)}</li>" for x in only_w3c) or "<li class='muted'>—</li>"}</ul>
      </div>
    </div>
  </header>

  <main id="changes">
    {"".join(render_change_block(c) for c in changes) or "<p class='muted'>Sem diferenças detetadas (por ID).</p>"}
  </main>

  <script>
    (function() {{
      const q = document.getElementById("q");
      const root = document.getElementById("changes");
      if (!q || !root) return;

      const cards = Array.from(root.querySelectorAll(".card"));

      q.addEventListener("input", () => {{
        const term = (q.value || "").trim().toLowerCase();
        for (const c of cards) {{
          const text = c.innerText.toLowerCase();
          c.style.display = term === "" || text.includes(term) ? "" : "none";
        }}
      }});
    }})();
  </script>
</body>
</html>
"""

    OUTPUT_HTML.write_text(html_doc, encoding="utf-8")
    print(f"OK: {OUTPUT_HTML}")
    print(f"OK: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
