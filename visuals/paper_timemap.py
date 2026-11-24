"""Interactive SISAL time map for the reviewers: one self-contained HTML page, slider over ka BP.
A cave is shown at a chosen age when that age lies inside the span of its published age model
(youngest..oldest over its d18O samples); the span does not claim the record is continuous."""
import json, re, sys
from pathlib import Path
from rdflib import Namespace, RDFS, RDF
import paper_figs as P
import cluster_archaeology as AY
L = Namespace("http://w3id.org/geo-lod/")
OUT = Path(P.OUT)

def main():
    D = AY.ArchData()
    arch = {str(c) for c in D.sa.subjects(RDF.type, L.ArchaeologicalCaveSite)}
    caves = []
    for c in sorted(D.ss.subjects(RDF.type, L.Cave)):
        lon, lat = AY._point(D.ss.value(D.ss.value(c, AY.GEO.hasGeometry), AY.GEO.asWKT))
        y, o, n = (D.ss.value(c, L.youngestAgeKaBP), D.ss.value(c, L.oldestAgeKaBP), D.ss.value(c, L.countDatedD18OSamples))
        caves.append([str(D.ss.value(c, RDFS.label) or c).replace("\"", "'"), round(lon, 3), round(lat, 3),
                      None if y is None else float(y), None if o is None else float(o),
                      int(n) if n is not None else 0, 1 if str(c) in arch else 0])
    svg = (OUT / "paper-sisal-map.svg").read_text(encoding="utf-8")
    land = re.search(r'<path d="([^"]+)" fill="#f4f1e8"', svg).group(1)
    html = TEMPLATE.replace("__LAND__", land).replace("__DATA__", json.dumps(caves, ensure_ascii=False))
    (OUT / "paper-sisal-timemap.html").write_text(html, encoding="utf-8")
    print(len(caves), len(html))

TEMPLATE = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SISAL caves through time</title>
<style>
body{margin:0;font-family:"Fira Sans",system-ui,sans-serif;background:#faf7f0;color:#1f1f1d}
main{max-width:1100px;margin:0 auto;padding:14px}
h1{font-size:20px;margin:0 0 4px}p{margin:4px 0;color:#55524b;font-size:14px}
.card{background:#fff;border-radius:10px;padding:10px;box-shadow:0 1px 3px #0002}
svg{width:100%;height:auto;display:block}
.ctl{display:flex;gap:12px;align-items:center;margin:10px 0;flex-wrap:wrap}
input[type=range]{flex:1;min-width:220px;accent-color:#9a3412}
button{background:#9a3412;color:#fff;border:0;border-radius:6px;padding:6px 14px;font-size:15px;cursor:pointer}
#age{font-size:22px;font-weight:600;min-width:180px}
.leg{font-size:13px;color:#55524b;display:flex;gap:16px;flex-wrap:wrap}
#tip{font-size:14px;min-height:20px}
</style></head><body><main>
<h1>SISAL caves through time</h1>
<p>A cave is drawn at a given age when that age lies within the span of its published age model (youngest to oldest sample with a &delta;<sup>18</sup>O value). The span marks where a record begins and ends; hiatuses lie inside it.</p>
<div class="ctl"><button id="play">Play</button><span id="age"></span><input id="sl" type="range" min="0" max="500" step="1" value="0">
<label><input type="checkbox" id="mis" checked> glacial stages</label></div>
<div class="card"><svg id="map" viewBox="0 0 1700 713"><rect width="1700" height="713" fill="#dcebf2"/>
<path d="__LAND__" fill="#f4f1e8" fill-rule="evenodd" stroke="#b9b4a8" stroke-width="1"/><g id="pts"></g></svg></div>
<p id="tip">Click a cave for its span.</p>
<div class="leg"><span><b style="color:#0072B2">&#9679;</b> cave with a record at the chosen age</span><span><b style="color:#b0b0b0">&#9679;</b> span does not include it</span><span><b style="color:#9a3412">&#9711;</b> archaeological cave</span><span id="cnt"></span></div>
<script>
const D=__DATA__, K=1700/360, X=l=>(l+180)*K, Y=l=>(85-l)*K, NS="http://www.w3.org/2000/svg";
// MIS limits in ka as in the graph's MIS vocabulary (Railsback et al.): stage, from, to
const MIS=[[1,0,14.5],[2,14.5,35],[3,35,57.3],[4,57.3,72.7],[5,72.7,132.2],[6,132.2,190.4],[7,190.4,244],[8,244,279],[9,279,337],[10,337,365.4],[11,365.4,428.3],[12,428.3,476.9],[13,476.9,533.5]];
const g=document.getElementById("pts"),sl=document.getElementById("sl"),ag=document.getElementById("age"),cnt=document.getElementById("cnt"),tip=document.getElementById("tip");
const els=D.map((d,i)=>{const c=document.createElementNS(NS,"circle");c.setAttribute("cx",X(d[1]));c.setAttribute("cy",Y(d[2]));c.setAttribute("r",d[6]?9:6.5);
 c.setAttribute("stroke",d[6]?"#9a3412":"#fff");c.setAttribute("stroke-width",d[6]?3:1.2);c.style.cursor="pointer";
 c.onclick=()=>{tip.textContent=d[0]+": "+(d[3]===null?"no dated d18O sample":d[3].toFixed(1)+" to "+d[4].toFixed(1)+" ka BP, "+d[5]+" dated samples")};g.appendChild(c);return c});
function upd(){const a=+sl.value;let n=0;
 D.forEach((d,i)=>{const on=d[3]!==null&&d[3]<=a&&a<=d[4];n+=on;els[i].setAttribute("fill",on?"#0072B2":"#d0d0d0");els[i].setAttribute("fill-opacity",on?1:.55);els[i].setAttribute("r",(d[6]?9:6.5)+(on?1.5:0))});
 const m=MIS.find(s=>a>=s[1]&&a<s[2]);const warm=m&&m[0]%2===1;
 ag.textContent=a+" ka BP"+(document.getElementById("mis").checked&&m?"  · MIS "+m[0]+(warm?" (warm)":" (cold)"):"");
 ag.style.color=document.getElementById("mis").checked&&m?(warm?"#b45309":"#1d4ed8"):"#1f1f1d";
 cnt.textContent=n+" of "+D.length+" caves have a record at this age"}
sl.oninput=upd;document.getElementById("mis").onchange=upd;
let t=null;document.getElementById("play").onclick=function(){if(t){clearInterval(t);t=null;this.textContent="Play";return}
 this.textContent="Pause";t=setInterval(()=>{sl.value=(+sl.value+2>+sl.max)?0:+sl.value+2;upd()},120)};
upd();
</script></main></body></html>'''
if __name__ == "__main__": main()
