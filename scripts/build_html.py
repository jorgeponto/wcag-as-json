import json
from pathlib import Path
import html
import datetime

ROOT = Path(__file__).resolve().parent.parent

# ✅ Novo ficheiro de input (W3C)
INPUT_JSON = ROOT / "data" / "wcag_w3c.json"

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
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"Não existe o ficheiro: {INPUT_JSON}")

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

    input_filename_label = "data/wcag_w3c.json"

    # Renderização de fallback (se não encontrarmos uma lista principal)
    if items is None:
        body = f"""
        <h1>WCAG — Revisão</h1>
        <p class="meta">Gerado em {safe(generated_at)} a partir de <code>{safe(input_filename_label)}</code>.</p>
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
        <h1>WCAG — Revisão</h1>
        <p class="meta">Gerado em {safe(generated_at)} a partir de <code>{safe(input_filename_label)}</code>.</p>

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
  <titl
