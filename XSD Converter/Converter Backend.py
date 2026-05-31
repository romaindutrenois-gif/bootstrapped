"""
xml_xsd_viewer.py
=================
All-in-one tool:
  1. Generates an XSD from an XML file
  2. Validates an XML file against an XSD schema
  3. Opens a visual interface in the browser to display the XSD

Requirements:
  pip install lxml

Usage:
  python xml_xsd_viewer.py generate  my_file.xml
  python xml_xsd_viewer.py validate  my_file.xml  my_schema.xsd
  python xml_xsd_viewer.py visualize my_schema.xsd
  python xml_xsd_viewer.py all        my_file.xml       (generate + visualize)
"""

import sys, os, json, re, webbrowser, tempfile
from lxml import etree
from collections import defaultdict


# ═══════════════════════════════════════════════
#  PARTIE 1 – GENERATION XSD
# ═══════════════════════════════════════════════

def detect_type(value):
    if value is None or value.strip() == "":
        return "xs:string"
    v = value.strip()
    try:
        int(v); return "xs:integer"
    except ValueError: pass
    try:
        float(v); return "xs:decimal"
    except ValueError: pass
    if v.lower() in ("true","false"):
        return "xs:boolean"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return "xs:date"
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", v):
        return "xs:dateTime"
    return "xs:string"

def analyze_element(element, infos, path=""):
    local_tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
    current_path = f"{path}/{local_tag}" if path else local_tag
    children = list(element)
    child_names = [(e.tag.split("}")[-1] if "}" in e.tag else e.tag) for e in children]
    if child_names:
        for nom in child_names:
            infos[current_path]["children"].add(nom)
    else:
        infos[current_path]["types"].add(detect_type(element.text))
    for attr_name, attr_val in element.attrib.items():
        attr_local = attr_name.split("}")[-1] if "}" in attr_name else attr_name
        infos[current_path]["attrs"][attr_local].add(detect_type(attr_val))
    compteur = defaultdict(int)
    for nom in child_names: compteur[nom] += 1
    for nom, count in compteur.items():
        if count > 1: infos[current_path]["multiples"].add(nom)
    for enfant in children:
        analyze_element(enfant, infos, current_path)

def choose_type(types_set):
    if not types_set: return "xs:string"
    if len(types_set) == 1: return list(types_set)[0]
    return "xs:string"

def generate_element_xsd(nom, path, infos, indent=1):
    pad = "  " * indent
    children   = infos[path].get("children", set())
    attrs = infos[path].get("attrs", {})
    types     = infos[path].get("types", set())
    multiples = infos[path].get("multiples", set())
    lines = []
    if children or attrs:
        lines.append(f'{pad}<xs:element name="{nom}">')
        lines.append(f'{pad}  <xs:complexType>')
        if children:
            lines.append(f'{pad}    <xs:sequence>')
            for child_name in sorted(children):
                path_enfant = f"{path}/{child_name}"
                max_occurs = 'unbounded' if child_name in multiples else '1'
                sub_children = infos[path_enfant].get("children", set())
                sub_attrs   = infos[path_enfant].get("attrs", {})
                if sub_children or sub_attrs:
                    sous_lines = generate_element_xsd(child_name, path_enfant, infos, indent+4)
                    if max_occurs == 'unbounded' and sous_lines:
                        sous_lines[0] = sous_lines[0].replace(
                            f'name="{child_name}"',
                            f'name="{child_name}" minOccurs="0" maxOccurs="unbounded"')
                    lines.extend(sous_lines)
                else:
                    sub_types = infos[path_enfant].get("types", set())
                    type_xsd   = choose_type(sub_types)
                    max_attr   = f' minOccurs="0" maxOccurs="{max_occurs}"' if max_occurs == 'unbounded' else ' minOccurs="0"'
                    lines.append(f'{pad}      <xs:element name="{child_name}" type="{type_xsd}"{max_attr}/>')
            lines.append(f'{pad}    </xs:sequence>')
        for attr_nom, attr_types in sorted(attrs.items()):
            lines.append(f'{pad}    <xs:attribute name="{attr_nom}" type="{choose_type(attr_types)}"/>')
        lines.append(f'{pad}  </xs:complexType>')
        lines.append(f'{pad}</xs:element>')
    else:
        lines.append(f'{pad}<xs:element name="{nom}" type="{choose_type(types)}" minOccurs="0"/>')
    return lines

def generate_xsd(xml_file, xsd_file=None):
    print(f"\n📂 Reading: {xml_file}")
    try:
        tree = etree.parse(xml_file)
    except Exception as e:
        print(f"❌ XML error: {e}"); sys.exit(1)
    racine = tree.getroot()
    root_tag = racine.tag.split("}")[-1] if "}" in racine.tag else racine.tag
    infos = defaultdict(lambda: {"children": set(), "attrs": defaultdict(set), "types": set(), "multiples": set()})
    analyze_element(racine, infos)
    xsd_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                  '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">', '']
    root_children  = infos[root_tag].get("children", set())
    root_attrs= infos[root_tag].get("attrs", {})
    root_multiples= infos[root_tag].get("multiples", set())
    xsd_lines.append(f'  <xs:element name="{root_tag}">')
    xsd_lines.append(f'    <xs:complexType>')
    if root_children:
        xsd_lines.append(f'      <xs:sequence>')
        for child_name in sorted(root_children):
            path_enfant = f"{root_tag}/{child_name}"
            max_occurs    = 'unbounded' if child_name in root_multiples else '1'
            sub_children  = infos[path_enfant].get("children", set())
            sub_attrs    = infos[path_enfant].get("attrs", {})
            if sub_children or sub_attrs:
                sous_lines = generate_element_xsd(child_name, path_enfant, infos, indent=4)
                if max_occurs == 'unbounded' and sous_lines:
                    sous_lines[0] = sous_lines[0].replace(
                        f'name="{child_name}"',
                        f'name="{child_name}" minOccurs="0" maxOccurs="unbounded"')
                xsd_lines.extend(sous_lines)
            else:
                sub_types = infos[path_enfant].get("types", set())
                type_xsd   = choose_type(sub_types)
                max_attr   = f' minOccurs="0" maxOccurs="{max_occurs}"' if max_occurs == 'unbounded' else ' minOccurs="0"'
                xsd_lines.append(f'        <xs:element name="{child_name}" type="{type_xsd}"{max_attr}/>')
        xsd_lines.append(f'      </xs:sequence>')
    for attr_nom, attr_types in sorted(root_attrs.items()):
        xsd_lines.append(f'      <xs:attribute name="{attr_nom}" type="{choose_type(attr_types)}"/>')
    xsd_lines += ['    </xs:complexType>', '  </xs:element>', '', '</xs:schema>']
    content = "\n".join(xsd_lines)
    if xsd_file is None:
        xsd_file = xml_file.replace(".xml", ".xsd")
        if xsd_file == xml_file: xsd_file = xml_file + ".xsd"
    with open(xsd_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ XSD generated: {xsd_file}")
    return xsd_file, content


# ═══════════════════════════════════════════════
#  PARTIE 2 – VALIDATION
# ═══════════════════════════════════════════════

def validate_xml(xml_file, xsd_file):
    print(f"\n🔍 Validation de '{xml_file}' contre '{xsd_file}'...")
    try:
        schema = etree.XMLSchema(etree.parse(xsd_file))
    except Exception as e:
        print(f"❌ XSD error: {e}"); sys.exit(1)
    try:
        doc = etree.parse(xml_file)
    except Exception as e:
        print(f"❌ XML error: {e}"); sys.exit(1)
    if schema.validate(doc):
        print("✅ XML is VALID.")
        return True, []
    else:
        erreurs = [(e.line, e.message) for e in schema.error_log]
        print("❌ XML is INVALID:")
        for ligne, msg in erreurs:
            print(f"  Ligne {ligne} : {msg}")
        return False, erreurs


# ═══════════════════════════════════════════════
#  PARTIE 3 – VISUALISEUR HTML
# ═══════════════════════════════════════════════

def xsd_to_tree(xsd_content):
    """Parse the XSD and build a JSON tree for visualization."""
    try:
        root = etree.fromstring(xsd_content.encode("utf-8"))
    except Exception as e:
        return {"name": f"Erreur: {e}", "children": []}
    ns = {"xs": "http://www.w3.org/2001/XMLSchema"}

    def parse_element(el, depth=0):
        name = el.get("name", "?")
        type_ = el.get("type", "")
        min_o = el.get("minOccurs", "1")
        max_o = el.get("maxOccurs", "1")
        node = {"name": name, "type": type_, "minOccurs": min_o, "maxOccurs": max_o, "children": [], "attributes": []}
        ct = el.find("xs:complexType", ns)
        if ct is not None:
            seq = ct.find("xs:sequence", ns)
            if seq is not None:
                for child in seq.findall("xs:element", ns):
                    node["children"].append(parse_element(child, depth+1))
            for attr in ct.findall("xs:attribute", ns):
                node["attributes"].append({
                    "name": attr.get("name","?"),
                    "type": attr.get("type","xs:string"),
                    "use":  attr.get("use","optional")
                })
        return node

    schema_root = root.find("xs:element", ns)
    if schema_root is None:
        return {"name": "Empty schema", "children": []}
    return parse_element(schema_root)

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Visualiseur XSD – {filename}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');

  :root {{
    --bg:       #0d1117;
    --surface:  #161b22;
    --border:   #30363d;
    --accent:   #58a6ff;
    --accent2:  #3fb950;
    --accent3:  #d2a8ff;
    --accent4:  #ffa657;
    --text:     #e6edf3;
    --muted:    #8b949e;
    --tag-bg:   #1f2937;
    --line:     #21262d;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }}

  header {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 18px 32px;
    display: flex;
    align-items: center;
    gap: 16px;
  }}
  header .logo {{
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.3rem;
    color: var(--accent);
    letter-spacing: -0.02em;
  }}
  header .filename {{
    color: var(--muted);
    font-size: 0.85rem;
  }}
  header .badge {{
    margin-left: auto;
    background: #1a2a1a;
    border: 1px solid var(--accent2);
    color: var(--accent2);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
  }}

  .toolbar {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 10px 32px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .btn {{
    background: var(--tag-bg);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 14px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .btn:hover {{ background: var(--border); }}
  .btn.primary {{ background: #1a2d4a; border-color: var(--accent); color: var(--accent); }}
  .btn.primary:hover {{ background: #1e3a5f; }}
  .sep {{ color: var(--border); }}

  .layout {{
    display: flex;
    flex: 1;
    overflow: hidden;
    height: calc(100vh - 105px);
  }}

  /* TREE PANEL */
  .tree-panel {{
    flex: 1;
    overflow-y: auto;
    padding: 24px 20px;
  }}
  .tree-panel::-webkit-scrollbar {{ width: 6px; }}
  .tree-panel::-webkit-scrollbar-track {{ background: var(--bg); }}
  .tree-panel::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

  .node {{
    position: relative;
    margin-left: 0;
  }}
  .node-inner {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.1s;
    position: relative;
  }}
  .node-inner:hover {{ background: var(--line); }}
  .node-inner.selected {{ background: #1a2d4a; outline: 1px solid var(--accent); }}

  .node-children {{
    margin-left: 24px;
    border-left: 1px solid var(--border);
    padding-left: 4px;
    margin-top: 2px;
    margin-bottom: 2px;
  }}

  .toggle {{
    width: 18px; height: 18px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 4px;
    font-size: 0.65rem;
    color: var(--muted);
    flex-shrink: 0;
    transition: transform 0.2s;
  }}
  .toggle.open {{ transform: rotate(90deg); }}
  .toggle.leaf {{ opacity: 0; pointer-events: none; }}

  .icon {{ font-size: 1rem; flex-shrink: 0; }}

  .node-name {{
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--text);
  }}
  .node-type {{
    font-size: 0.75rem;
    color: var(--accent3);
    background: #1e1a2e;
    padding: 2px 7px;
    border-radius: 4px;
    border: 1px solid #3d2f5a;
  }}
  .node-occurs {{
    font-size: 0.7rem;
    color: var(--muted);
    margin-left: auto;
  }}
  .node-occurs.required {{ color: var(--accent4); }}

  /* DETAIL PANEL */
  .detail-panel {{
    width: 320px;
    background: var(--surface);
    border-left: 1px solid var(--border);
    overflow-y: auto;
    flex-shrink: 0;
  }}
  .detail-panel::-webkit-scrollbar {{ width: 6px; }}
  .detail-panel::-webkit-scrollbar-track {{ background: var(--surface); }}
  .detail-panel::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

  .detail-header {{
    padding: 20px 20px 12px;
    border-bottom: 1px solid var(--border);
  }}
  .detail-header h2 {{
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 4px;
  }}
  .detail-header .detail-path {{
    font-size: 0.72rem;
    color: var(--muted);
    word-break: break-all;
  }}

  .detail-body {{ padding: 16px 20px; }}

  .detail-section {{
    margin-bottom: 20px;
  }}
  .detail-section h3 {{
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 10px;
  }}
  .prop-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid var(--line);
    font-size: 0.82rem;
  }}
  .prop-row:last-child {{ border-bottom: none; }}
  .prop-key {{ color: var(--muted); }}
  .prop-val {{ color: var(--text); font-weight: 600; }}
  .prop-val.type {{ color: var(--accent3); }}
  .prop-val.green {{ color: var(--accent2); }}
  .prop-val.orange {{ color: var(--accent4); }}

  .attr-chip {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    background: var(--tag-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    margin-bottom: 6px;
    font-size: 0.8rem;
  }}
  .attr-chip .attr-name {{ color: var(--accent4); font-weight: 600; }}
  .attr-chip .attr-type {{ color: var(--accent3); margin-left: auto; font-size: 0.72rem; }}

  .empty-state {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    color: var(--muted);
    font-size: 0.85rem;
    gap: 8px;
  }}
  .empty-state .icon {{ font-size: 2rem; }}

  /* RAW XSD PANEL */
  .raw-panel {{
    display: none;
    flex: 1;
    overflow: auto;
    padding: 24px;
  }}
  .raw-panel.visible {{ display: block; }}
  .raw-panel pre {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    line-height: 1.7;
    color: var(--text);
    white-space: pre;
  }}
  .xml-tag {{ color: var(--accent); }}
  .xml-attr {{ color: var(--accent4); }}
  .xml-val {{ color: var(--accent2); }}
  .xml-comment {{ color: var(--muted); font-style: italic; }}
</style>
</head>
<body>

<header>
  <div class="logo">⬡ XSD Viewer</div>
  <div class="filename">{filename}</div>
  <div class="badge">✓ Schema chargé</div>
</header>

<div class="toolbar">
  <button class="btn primary" id="btnTree" onclick="showTree()">🌳 Arbre</button>
  <button class="btn" id="btnRaw" onclick="showRaw()">📄 XSD brut</button>
  <span class="sep">|</span>
  <button class="btn" onclick="expandAll()">+ Expand all</button>
  <button class="btn" onclick="collapseAll()">− Collapse all</button>
</div>

<div class="layout">
  <div class="tree-panel" id="treePanel"></div>
  <div class="raw-panel" id="rawPanel"></div>
  <div class="detail-panel" id="detailPanel">
    <div class="empty-state">
      <div class="icon">👆</div>
      <div>Click an element<br>to view its details</div>
    </div>
  </div>
</div>

<script>
const TREE_DATA = {tree_json};
const XSD_RAW   = {xsd_raw};

let selectedNode = null;

// ─── Rendu de l'arbre ───────────────────────────────────────────
function renderTree(node, parentPath = "", container) {{
  const path = parentPath ? parentPath + " › " + node.name : node.name;
  const hasChildren = node.children && node.children.length > 0;

  const div = document.createElement("div");
  div.className = "node";

  const inner = document.createElement("div");
  inner.className = "node-inner";
  inner.dataset.path = path;
  inner.dataset.nodeJson = JSON.stringify(node);

  // Toggle
  const toggle = document.createElement("span");
  toggle.className = "toggle" + (hasChildren ? " open" : " leaf");
  toggle.textContent = "▶";
  inner.appendChild(toggle);

  // Icon
  const icon = document.createElement("span");
  icon.className = "icon";
  icon.textContent = hasChildren ? "📦" : (node.attributes && node.attributes.length ? "🔷" : "◆");
  inner.appendChild(icon);

  // Name
  const name = document.createElement("span");
  name.className = "node-name";
  name.textContent = node.name;
  inner.appendChild(name);

  // Type badge (only for leaf)
  if (!hasChildren && node.type) {{
    const tb = document.createElement("span");
    tb.className = "node-type";
    tb.textContent = node.type.replace("xs:","");
    inner.appendChild(tb);
  }}

  // Occurs
  const occ = document.createElement("span");
  const isRequired = node.minOccurs === "1" || !node.minOccurs;
  const isUnbounded = node.maxOccurs === "unbounded";
  occ.className = "node-occurs" + (isRequired && !isUnbounded ? " required" : "");
  const minTxt = node.minOccurs || "1";
  const maxTxt = node.maxOccurs || "1";
  occ.textContent = `[${{minTxt}}..${{isUnbounded ? "∞" : maxTxt}}]`;
  inner.appendChild(occ);

  div.appendChild(inner);

  // Children
  let childContainer = null;
  if (hasChildren) {{
    childContainer = document.createElement("div");
    childContainer.className = "node-children";
    for (const child of node.children) {{
      renderTree(child, path, childContainer);
    }}
    div.appendChild(childContainer);
  }}

  // Click toggle
  toggle.addEventListener("click", (e) => {{
    e.stopPropagation();
    if (!childContainer) return;
    const open = !childContainer.classList.contains("hidden");
    childContainer.classList.toggle("hidden", open);
    toggle.classList.toggle("open", !open);
  }});

  // Click select
  inner.addEventListener("click", () => selectNode(inner, node, path));

  container.appendChild(div);
}}

function selectNode(el, node, path) {{
  if (selectedNode) selectedNode.classList.remove("selected");
  el.classList.add("selected");
  selectedNode = el;
  showDetail(node, path);
}}

// ─── Panneau de detail ──────────────────────────────────────────
function showDetail(node, path) {{
  const panel = document.getElementById("detailPanel");
  const hasChildren = node.children && node.children.length > 0;
  const attrs = node.attributes || [];

  const occMin = node.minOccurs || "1";
  const occMax = node.maxOccurs || "1";
  const optional = occMin === "0";
  const unbounded = occMax === "unbounded";

  panel.innerHTML = `
    <div class="detail-header">
      <h2>${{node.name}}</h2>
      <div class="detail-path">${{path}}</div>
    </div>
    <div class="detail-body">
      <div class="detail-section">
        <h3>Properties</h3>
        <div class="prop-row"><span class="prop-key">Type</span>
          <span class="prop-val type">${{hasChildren ? "complexType" : (node.type || "xs:string")}}</span></div>
        <div class="prop-row"><span class="prop-key">Obligatoire</span>
          <span class="prop-val ${{optional ? "orange" : "green"}}">${{optional ? "Non (optionnel)" : "Oui"}}</span></div>
        <div class="prop-row"><span class="prop-key">Repeatable</span>
          <span class="prop-val ${{unbounded ? "green" : ""}}">${{unbounded ? "Oui (illimité)" : "Non"}}</span></div>
        <div class="prop-row"><span class="prop-key">minOccurs</span>
          <span class="prop-val">${{occMin}}</span></div>
        <div class="prop-row"><span class="prop-key">maxOccurs</span>
          <span class="prop-val">${{occMax}}</span></div>
        ${{hasChildren ? `<div class="prop-row"><span class="prop-key">Enfants directs</span>
          <span class="prop-val green">${{node.children.length}}</span></div>` : ""}}
      </div>
      ${{attrs.length ? `
      <div class="detail-section">
        <h3>Attributs (${{attrs.length}})</h3>
        ${{attrs.map(a => `
          <div class="attr-chip">
            <span class="attr-name">@${{a.name}}</span>
            <span class="attr-type">${{a.type.replace("xs:","")}}</span>
          </div>`).join("")}}
      </div>` : ""}}
    </div>`;
}}

// ─── Raw XSD ───────────────────────────────────────────────
function syntaxHL(xsd) {{
  return xsd
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/(&lt;\/?[\w:]+)/g,'<span class="xml-tag">$1</span>')
    .replace(/(&gt;)/g,'<span class="xml-tag">$1</span>')
    .replace(/([\w:]+)=/g,'<span class="xml-attr">$1</span>=')
    .replace(/"([^"]*)"/g,'"<span class="xml-val">$1</span>"');
}}

function showTree() {{
  document.getElementById("treePanel").style.display = "";
  document.getElementById("rawPanel").classList.remove("visible");
  document.getElementById("btnTree").classList.add("primary");
  document.getElementById("btnRaw").classList.remove("primary");
}}

function showRaw() {{
  document.getElementById("treePanel").style.display = "none";
  document.getElementById("rawPanel").classList.add("visible");
  document.getElementById("btnTree").classList.remove("primary");
  document.getElementById("btnRaw").classList.add("primary");
  document.getElementById("rawPanel").innerHTML = `<pre>${{syntaxHL(XSD_RAW)}}</pre>`;
}}

// ─── Expand / Collapse ──────────────────────────────────────────
function expandAll() {{
  document.querySelectorAll(".node-children").forEach(el => el.classList.remove("hidden"));
  document.querySelectorAll(".toggle:not(.leaf)").forEach(el => el.classList.add("open"));
}}
function collapseAll() {{
  document.querySelectorAll(".node-children").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".toggle:not(.leaf)").forEach(el => el.classList.remove("open"));
}}

// ─── Init ───────────────────────────────────────────────────────
const container = document.getElementById("treePanel");
renderTree(TREE_DATA, "", container);
</script>
</body>
</html>"""


def visualize_xsd(xsd_file, xsd_content=None):
    """Generate the HTML page and open it in the browser."""
    if xsd_content is None:
        with open(xsd_file, "r", encoding="utf-8") as f:
            xsd_content = f.read()

    arbre = xsd_to_tree(xsd_content)
    nom   = os.path.basename(xsd_file)

    html = HTML_TEMPLATE.format(
        filename = nom,
        tree_json = json.dumps(arbre, ensure_ascii=False),
        xsd_raw   = json.dumps(xsd_content, ensure_ascii=False),
    )

    # Write dans un fichier temporaire à side du XSD
    html_path = xsd_file.replace(".xsd", "_viewer.html")
    if html_path == xsd_file:
        html_path = xsd_file + "_viewer.html"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"🌐 Interface created: {html_path}")
    print("   Opening in browser...")
    webbrowser.open("file://" + os.path.abspath(html_path))
    return html_path


# ═══════════════════════════════════════════════
#  POINT D'ENTRÉE
# ═══════════════════════════════════════════════

def usage():
    print("""
Usage :
  python xml_xsd_viewer.py generate   <file.xml> [output.xsd]
  python xml_xsd_viewer.py validate   <file.xml> <schema.xsd>
  python xml_xsd_viewer.py visualize  <schema.xsd>
  python xml_xsd_viewer.py all        <file.xml> [output.xsd]
    → generate XSD + open visualizer
""")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        aide(); sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "generate":
        xsd_f, _ = generate_xsd(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)

    elif cmd == "validate":
        if len(sys.argv) < 4:
            print("❌ Fournir un XML et un XSD."); aide(); sys.exit(1)
        validate_xml(sys.argv[2], sys.argv[3])

    elif cmd == "visualize":
        visualize_xsd(sys.argv[2])

    elif cmd == "all":
        xsd_f, xsd_content = generate_xsd(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        visualize_xsd(xsd_f, xsd_content)

    else:
        print(f"❌ Unknown command: '{cmd}'"); aide(); sys.exit(1)
