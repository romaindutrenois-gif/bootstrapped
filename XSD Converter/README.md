# XML to XSD Converter

> A free, browser-based tool to convert XML files to XSD schemas, annotate fields, visualize the structure as an interactive diagram, and export to annotated XSD or Excel.

**No installation required. No data sent to any server. Just open the HTML file.**

---

## ✨ Features

| Tab | Feature |
|-----|---------|
| **Convert** | Drag & drop an XML file → generate the XSD schema in one click |
| **Convert** | Copy or download the generated `.xsd` file |
| **Annotate** | Add a free-text comment on each field |
| **Annotate** | Assign a status per field: ✅ Validated · 🔄 In progress · ❓ To clarify · ⚠️ To update · ❌ Rejected |
| **Annotate** | Export annotated XSD with `xs:documentation` tags (compatible with Altova, oXygen…) |
| **Annotate** | Export an Excel tracking file with a summary dashboard and colour-coded statuses |
| **Diagram** | Visualize the schema as interactive boxes and arrows |
| **Diagram** | Navigate: drag to pan, scroll to zoom, buttons to zoom in/out, reset view |
| **Diagram** | Export the diagram as SVG (vector) or PNG (high resolution) |

---

## 🚀 Quick start

### Browser tool (no installation)

1. Download `xml_to_xsd_tool.html`
2. Double-click to open it in Chrome, Edge or Firefox
3. Drop your XML file → click **Convert to XSD**

That's it.

### Command-line tool (Python)

**Requirements:** Python 3.7+ and `lxml`

```bash
py -m pip install lxml
```

**Usage:**

```bash
# Generate XSD from XML (+ open visual browser interface)
py xml_xsd_viewer_en.py all my_file.xml

# Generate XSD only
py xml_xsd_viewer_en.py generate my_file.xml

# Validate an XML against an XSD
py xml_xsd_viewer_en.py validate my_file.xml my_schema.xsd

# Open the visual browser interface for an existing XSD
py xml_xsd_viewer_en.py visualize my_schema.xsd
```

---

## 📁 Files

| File | Description |
|------|-------------|
| `xml_to_xsd_tool.html` | **Main tool** — browser-based, no installation |
| `xml_xsd_viewer_en.py` | Command-line tool with XSD generation, validation and tree viewer |
| `test_project.xml` | Sample XML file to test the tool |
| `README.md` | This file |

---

## 🔍 How it works

The tool analyses the XML structure recursively and infers:

- **Element hierarchy** — nested `xs:sequence` blocks
- **XSD types** — `xs:string`, `xs:integer`, `xs:decimal`, `xs:boolean`, `xs:date`, `xs:dateTime`
- **Attributes** — mapped to `xs:attribute`
- **Repeating elements** — detected and marked as `maxOccurs="unbounded"`
- **Annotations** — stored as standard `xs:documentation` tags

Everything runs client-side in the browser (JavaScript) or locally via Python. **No data is ever transmitted to a server.**

---

## 📊 Excel export

The Excel tracking file contains two sheets:

**Annotations sheet**

| Full path | Field | XSD Type | Status | Comment | Last updated |
|-----------|-------|----------|--------|---------|--------------|
| project > team > member | member | complexType | ✅ Validated | Mandatory field | 31/05/2026 |

**Summary sheet**

- Total fields, annotated fields, fields without annotation
- Breakdown by status with counts

---

## 🗂️ Use case

This tool was built to solve a real problem: working with an external partner on a data exchange project that required XSD schemas, without access to expensive tools like Altova XMLSpy Professional.

Typical workflow:
1. **Convert** your XML → XSD in one click
2. **Annotate** fields with comments and statuses
3. **Export** the annotated XSD to share with your technical team
4. **Export** the Excel tracking file to share with non-technical stakeholders or external partners
5. **Diagram** to visualise and document the schema structure

---

## 🧩 Compatibility

- **Browser tool:** Chrome, Edge, Firefox (any modern browser)
- **Python tool:** Python 3.7+ on Windows, macOS, Linux
- **XSD output:** Compatible with Altova XMLSpy, oXygen XML Editor, and any XSD-compliant tool
- **Excel output:** Compatible with Microsoft Excel, LibreOffice Calc, Google Sheets

---

## 📄 License

MIT License — free to use, modify and distribute.

---

## 🤝 Contributing

Pull requests welcome. If you encounter a bug or have a feature request, open an issue.

Possible improvements:
- Support for XML namespaces
- `xs:choice` detection
- Custom type restrictions (min/max length, patterns, enumerations)
- Multi-file XSD with `xs:include`
- Import annotations from Excel back into the tool
