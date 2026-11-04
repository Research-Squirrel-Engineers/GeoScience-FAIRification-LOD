"""The query page of the documentation: queries.yaml -> docu/sparql.html and docu/downloads/queries/*.rq.

Pattern of the wdt-sparql skill, without Jinja and without Quarto: the page is written with site_kit, so it carries the
same navigation as every other page. rdflib runs in the browser under Pyodide (versions pinned below); the graph is a
static N-Triples file next to the page. There is no endpoint.

Every query is executed here against the published graph. A query that returns no rows stops the build.
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import yaml
from rdflib import Graph

import sample_graph
import site_kit

HERE = Path(__file__).resolve().parent
QUERIES_YAML = HERE / "queries.yaml"
PYODIDE_VERSION = "0.26.4"
RDFLIB_VERSION = "7.1.1"
MAX_ROWS = 500


def load() -> dict:
    cfg = yaml.safe_load(QUERIES_YAML.read_text(encoding="utf-8"))
    for key in ("graph", "prefixes", "queries", "page"):
        if key not in cfg:
            sys.exit(f"queries.yaml must contain '{key}'")
    ids = [q["id"] for q in cfg["queries"]]
    if len(ids) != len(set(ids)):
        sys.exit("queries.yaml: duplicate query id")
    return cfg


def check(cfg: dict, graph_file: Path) -> int:
    g = Graph().parse(graph_file, format=cfg["graph"].get("format", "nt"))
    bad = []
    for q in cfg["queries"]:
        try:
            n = len(list(g.query(cfg["prefixes"] + "\n" + q["sparql"])))
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{q['id']}: {type(exc).__name__}: {exc}")
            continue
        q["rows"] = n
        if n == 0:
            bad.append(f"{q['id']}: no rows (parses, matches nothing)")
    if bad:
        sys.exit("query page: " + "; ".join(bad))
    return len(g)


def write_rq(cfg: dict, dest: Path) -> None:
    out = dest / "downloads" / "queries"
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.rq"):
        stale.unlink()
    for q in cfg["queries"]:
        intro = "\n".join(f"# {l}" for l in textwrap.wrap(" ".join(q["intro"].split()), 76))
        text = f"# {q['title']}\n{intro}\n\n{cfg['prefixes'].rstrip()}\n\n{q['sparql'].rstrip()}\n"
        (out / f"{q['id']}.rq").write_text(text, encoding="utf-8", newline="\n")


SCRIPT = """<script src="https://cdn.jsdelivr.net/pyodide/v%(py)s/full/pyodide.js"></script>
<script>
const PREFIXES = %(prefixes)s, QUERIES = %(queries)s, GRAPH = %(graph)s, MAX_ROWS = %(max)d;
const statusText = document.getElementById('status-text'), dot = document.getElementById('dot');
let pyodide = null;
function setStatus(t, s) { statusText.textContent = t; dot.className = 'dot ' + (s || ''); }
function esc(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function renderTable(cols, rows, id, total) {
  const out = document.getElementById(id);
  if (!rows.length) { out.innerHTML = '<p class="note">No results. The query is valid but matched nothing.</p>'; return; }
  let h = '<div class="tbl"><table><thead><tr>' + cols.map(c => '<th>' + esc(c) + '</th>').join('') + '</tr></thead><tbody>';
  for (const r of rows) {
    h += '<tr>' + cols.map(c => {
      const v = r[c];
      if (v === null || v === undefined) return '<td class="nil">&mdash;</td>';
      const s = String(v);
      return /^https?:\\/\\//.test(s) ? '<td><a href="' + esc(s) + '" target="_blank" rel="noopener">' + esc(s) + '</a></td>' : '<td>' + esc(s) + '</td>';
    }).join('') + '</tr>';
  }
  h += '</tbody></table></div><p class="note">' + (total > rows.length ? 'Showing the first ' + rows.length + ' of ' + total + ' rows.' : rows.length + ' row' + (rows.length === 1 ? '' : 's') + '.') + '</p>';
  out.innerHTML = h;
}
async function boot() {
  try {
    pyodide = await loadPyodide();
    setStatus('Installing rdflib\\u2026', 'busy');
    await pyodide.loadPackage('micropip');
    await pyodide.runPythonAsync('import micropip\\nawait micropip.install("rdflib==%(rd)s")');
    setStatus('Loading the graph\\u2026', 'busy');
    pyodide.globals.set('_url', GRAPH.url);
    pyodide.globals.set('_fmt', GRAPH.format);
    await pyodide.runPythonAsync(`
from pyodide.http import pyfetch
from rdflib import Graph
resp = await pyfetch(_url)
if resp.status != 200:
    raise RuntimeError(f"{_url} -> HTTP {resp.status}")
base = Graph()
base.parse(data=await resp.string(), format=_fmt)
n_base = len(base)
`);
    const n = pyodide.globals.get('n_base');
    const note = document.getElementById('graph-note');
    note.hidden = false;
    note.textContent = 'Graph loaded: ' + n + ' triples from ' + GRAPH.url + '.';
    setStatus('Ready \\u2014 edit a query and press Run.', 'ok');
    document.querySelectorAll('button.run').forEach(b => (b.disabled = false));
  } catch (err) { setStatus('Could not start: ' + err.message, 'err'); console.error(err); }
}
async function runQuery(id) {
  const btn = document.querySelector('button.run[data-q="' + id + '"]');
  const timing = document.getElementById('time-' + id), out = document.getElementById('out-' + id);
  btn.disabled = true; timing.textContent = 'running\\u2026'; out.innerHTML = '';
  const t0 = performance.now();
  try {
    pyodide.globals.set('_q', PREFIXES + '\\n' + document.getElementById('src-' + id).value);
    pyodide.globals.set('_max', MAX_ROWS);
    const json = await pyodide.runPythonAsync(`
import json
res = base.query(_q)
cols = [str(v) for v in res.vars]
_all = list(res)
rows = [{c: (None if r[i] is None else str(r[i])) for i, c in enumerate(cols)} for r in _all[:_max]]
json.dumps({"cols": cols, "rows": rows, "n": len(base), "total": len(_all)})
`);
    const d = JSON.parse(json);
    renderTable(d.cols, d.rows, 'out-' + id, d.total);
    timing.textContent = ((performance.now() - t0) / 1000).toFixed(1) + 's over ' + d.n + ' triples';
  } catch (err) { out.innerHTML = '<pre class="error">' + esc(err.message) + '</pre>'; timing.textContent = ''; }
  btn.disabled = false;
}
document.querySelectorAll('button.run').forEach(b => b.addEventListener('click', () => runQuery(b.dataset.q)));
document.querySelectorAll('button.reset').forEach(b => b.addEventListener('click', () => {
  const id = b.dataset.q;
  document.getElementById('src-' + id).value = QUERIES[id];
  document.getElementById('out-' + id).innerHTML = '';
  document.getElementById('time-' + id).textContent = '';
}));
boot();
</script>
"""


def build(dest: Path) -> int:
    """Write docu/sparql.html, the .rq files and the graph. Returns the number of queries."""
    cfg = load()
    graph_file = dest / cfg["graph"]["url"]
    n_lines = sample_graph.write(graph_file)
    n_triples = check(cfg, graph_file)
    write_rq(cfg, dest)
    esc = site_kit.esc
    sections = []
    for i, q in enumerate(cfg["queries"], 1):
        src = q["sparql"].rstrip("\n")
        sections.append(
            f'<section class="query" id="q-{q["id"]}">\n<h2>{i}. {esc(q["title"])}</h2>\n'
            f'<p class="intro">{esc(" ".join(q["intro"].split()))}</p>\n'
            f'<textarea class="sparql" id="src-{q["id"]}" spellcheck="false" rows="{max(6, src.count(chr(10)) + 2)}">{esc(src)}</textarea>\n'
            f'<div class="query-bar"><button type="button" class="run" data-q="{q["id"]}" disabled>Run</button>'
            f'<button type="button" class="reset" data-q="{q["id"]}">Reset</button><span class="timing" id="time-{q["id"]}"></span>'
            f'<a href="downloads/queries/{q["id"]}.rq" download>.rq</a></div>\n<div class="result" id="out-{q["id"]}"></div>\n</section>')
    note = ("<p class=\"note\">There is no SPARQL endpoint and no server. The graph is fetched as a static file and parsed in your "
            "browser with <code>rdflib</code> under Pyodide, so an archived copy of the repository stays queryable. "
            f"The sample holds {n_triples:,} triples ({esc(' '.join(cfg['graph']['note'].split()))}) "
            f'<a href="{esc(cfg["graph"]["url"])}">Download the graph</a>.</p>')
    status = ('<div class="status"><span class="dot" id="dot"></span>'
              '<span id="status-text">Loading the Python runtime (about 10 MB on first visit)&hellip;</span></div>'
              '<p class="note" id="graph-note" hidden></p>')
    script = SCRIPT % {"py": PYODIDE_VERSION, "rd": RDFLIB_VERSION, "max": MAX_ROWS,
                       "prefixes": json.dumps(cfg["prefixes"]), "graph": json.dumps(cfg["graph"], ensure_ascii=False),
                       "queries": json.dumps({q["id"]: q["sparql"].rstrip("\n") for q in cfg["queries"]}, ensure_ascii=False)}
    html = site_kit.page("docu", "sparql.html", cfg["page"]["title"], esc(" ".join(cfg["page"]["intro"].split())),
                         note + status + "\n".join(sections), script=script)
    site_kit.write_page(dest / "sparql.html", html)
    print(f"  sparql.html: {len(cfg['queries'])} queries, {n_triples} triples ({graph_file.stat().st_size/1e6:.1f} MB)")
    return len(cfg["queries"])
