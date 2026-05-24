#!/usr/bin/env python3
"""
PowerShell-based Office tools (Zero external dependencies)
Replaces python-docx, openpyxl, python-pptx with Windows COM
Works on Python 3.7 + Office 2010

Two execution modes:
- _run_ps: inline -Command (simple string data)
- _run_ps_file: temp .ps1 file (complex list/dict data via base64+JSON)
"""
import os
import json
import subprocess
import tempfile
import base64
from .base import Tool


def _ps_str(s):
    """Escape string for PowerShell single-quote context."""
    return s.replace("'", "''") if s else ""


def _ps_b64(data):
    """Convert Python data to base64 JSON for PowerShell parsing."""
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.b64encode(json_str.encode('utf-16-le')).decode()


def _run_ps(script, timeout=120):
    """Run PowerShell via -Command (inline, for string-only scripts)."""
    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
        capture_output=True, text=True, encoding='gbk', errors='replace', timeout=timeout
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _run_ps_file(script, timeout=120):
    """Run PowerShell via -EncodedCommand (avoids temp file encoding issues on Win7/GBK)."""
    # UTF-16-LE base64 so PowerShell can decode correctly regardless of system codepage
    b64 = base64.b64encode(script.encode('utf-16-le')).decode()
    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-EncodedCommand', b64],
        capture_output=True, text=True, encoding='gbk', errors='replace', timeout=timeout
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# =============================================================================
# DOCX Operations
# =============================================================================

class DocxCreateTool(Tool):
    name = "docx_create"
    description = "Create Word document with headings, paragraphs, tables"
    parameters = [
        {"name": "output_path", "type": "string", "required": True, "description": "Output .docx path"},
        {"name": "title", "type": "string", "required": False, "description": "Document title"},
        {"name": "paragraphs", "type": "list", "required": False, "description": "List of paragraph texts"},
        {"name": "tables", "type": "list", "required": False, "description": "List of table dicts: {headers:[...], rows:[[...]]}"},
        {"name": "font_name", "type": "string", "required": False, "description": "Font name"},
        {"name": "font_size", "type": "int", "required": False, "description": "Font size in points"}
    ]
    
    def execute(self, **kwargs):
        output_path = kwargs.get("output_path", "")
        title = kwargs.get("title", "")
        paragraphs = kwargs.get("paragraphs", [])
        tables = kwargs.get("tables", [])
        font_name = kwargs.get("font_name", "微软雅黑")
        font_size = kwargs.get("font_size", 11)
        
        if not output_path:
            return {"success": False, "error": "Missing output_path"}
        
        out_ps = _ps_str(output_path)
        title_ps = _ps_str(title)
        font_ps = _ps_str(font_name)
        size_ps = str(font_size)
        paras_b64 = _ps_b64(paragraphs)
        tables_b64 = _ps_b64(tables)
        
        script = """
$ErrorActionPreference = 'Stop'
$paras = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String('{paras_b64}')) | ConvertFrom-Json
$tables = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String('{tables_b64}')) | ConvertFrom-Json

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Add()

if ('{title_ps}') {{
    $p = $doc.Paragraphs.Add()
    $p.Range.Text = '{title_ps}'
    $p.Range.Font.Size = 24
    $p.Range.Font.Bold = 1
    $p.Range.Font.Name = '{font_ps}'
    $p.Alignment = 1
}}

foreach ($para in $paras) {{
    $p = $doc.Paragraphs.Add()
    $p.Range.Text = [string]$para
    $p.Range.Font.Size = {size_ps}
    $p.Range.Font.Name = '{font_ps}'
}}

foreach ($tbl in $tables) {{
    $hdr = $tbl['headers']
    $rows = $tbl['rows']
    $cols = $hdr.Count
    $rowCount = 1 + $rows.Count
    if ($cols -gt 0 -and $rowCount -gt 1) {{
        $t = $doc.Tables.Add($doc.Paragraphs.Add().Range, $rowCount, $cols)
        $t.Style = 1
        for ($c = 0; $c -lt $cols; $c++) {{
            $t.Cell(1, $c+1).Range.Text = [string]$hdr[$c]
            $t.Cell(1, $c+1).Range.Font.Bold = 1
        }}
        for ($r = 0; $r -lt $rows.Count; $r++) {{
            for ($c = 0; $c -lt $cols; $c++) {{
                $t.Cell($r+2, $c+1).Range.Text = [string]$rows[$r][$c]
            }}
        }}
    }}
}}

$doc.SaveAs('{out_ps}')
$doc.Close()
$word.Quit()
Write-Output 'SUCCESS'
""".format(paras_b64=paras_b64, tables_b64=tables_b64, 
           title_ps=title_ps, font_ps=font_ps, size_ps=size_ps, out_ps=out_ps)
        
        stdout, stderr, rc = _run_ps_file(script)
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Docx created", "path": output_path}
        return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "output_path" not in params:
            return False, "Missing output_path"
        return True, None


class DocxEditTool(Tool):
    name = "docx_edit"
    description = "Find and replace text in Word document"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .docx path"},
        {"name": "output_path", "type": "string", "required": False, "description": "Output path"},
        {"name": "find", "type": "string", "required": True, "description": "Text to find"},
        {"name": "replace", "type": "string", "required": True, "description": "Replacement text"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        output_path = kwargs.get("output_path", input_path)
        find_text = kwargs.get("find", "")
        replace_text = kwargs.get("replace", "")
        
        if not input_path or not find_text:
            return {"success": False, "error": "Missing required params"}
        
        in_ps = _ps_str(input_path)
        out_ps = _ps_str(output_path)
        find_ps = _ps_str(find_text)
        repl_ps = _ps_str(replace_text)
        
        script = """
$ErrorActionPreference = 'Stop'
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Open('{in_ps}')
    $find = $doc.Content.Find
    $find.Text = '{find_ps}'
    $find.Replacement.Text = '{repl_ps}'
    $count = 0
    while ($find.Execute($false,$false,$false,$false,$false,$false,1,$false,$false,0)) {{ $count++ }}
    $doc.SaveAs('{out_ps}')
    $doc.Close()
    $word.Quit()
    Write-Output ('SUCCESS: ' + $count + ' replacements')
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $word.Quit() }} catch {{}}
}}
""".format(in_ps=in_ps, out_ps=out_ps, find_ps=find_ps, repl_ps=repl_ps)
        
        stdout, stderr, rc = _run_ps_file(script)
        if "SUCCESS" in stdout:
            return {"success": True, "result": stdout}
        return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "input_path" not in params or "find" not in params:
            return False, "Missing required params"
        return True, None


class DocxReadTool(Tool):
    name = "docx_read"
    description = "Read text content from Word document"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .docx path"},
        {"name": "max_chars", "type": "int", "required": False, "description": "Max chars to read"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        max_chars = kwargs.get("max_chars", 10000)
        
        if not input_path:
            return {"success": False, "error": "Missing input_path"}
        if not os.path.exists(input_path):
            return {"success": False, "error": "File not found"}
        
        in_ps = _ps_str(input_path)
        script = """
$ErrorActionPreference = 'Stop'
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Open('{in_ps}')
    $text = $doc.Content.Text
    $doc.Close()
    $word.Quit()
    Write-Output $text
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $word.Quit() }} catch {{}}
}}
""".format(in_ps=in_ps)
        
        stdout, stderr, rc = _run_ps_file(script)
        if "ERROR" not in stdout:
            return {"success": True, "content": stdout[:max_chars], "length": len(stdout)}
        return {"success": False, "error": stdout}
    
    def validate(self, params):
        if "input_path" not in params:
            return False, "Missing input_path"
        return True, None


# =============================================================================
# XLSX Operations
# =============================================================================

class XlsxCreateTool(Tool):
    name = "xlsx_create"
    description = "Create Excel workbook with data and tables"
    parameters = [
        {"name": "output_path", "type": "string", "required": True, "description": "Output .xlsx path"},
        {"name": "sheets", "type": "list", "required": False, "description": "List of sheet dicts: [{name, headers, rows}]"},
        {"name": "sheet_name", "type": "string", "required": False, "description": "Default sheet name"}
    ]
    
    def execute(self, **kwargs):
        output_path = kwargs.get("output_path", "")
        sheets_data = kwargs.get("sheets", [])
        default_sheet = kwargs.get("sheet_name", "Sheet1")
        
        if not output_path:
            return {"success": False, "error": "Missing output_path"}
        
        out_ps = _ps_str(output_path)
        sheets_b64 = _ps_b64(sheets_data)
        
        script = """
$ErrorActionPreference = 'Stop'
$sheets = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String('{sheets_b64}')) | ConvertFrom-Json

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$wb = $excel.Workbooks.Add()

$firstSheet = $true
foreach ($s in $sheets) {{
    if ($firstSheet) {{
        $ws = $wb.Sheets[1]
        $firstSheet = $false
    }} else {{
        $ws = $wb.Worksheets.Add()
    }}
    $ws.Name = $s.name
    
    if ($s.headers) {{
        for ($c = 0; $c -lt $s.headers.Count; $c++) {{
            $ws.Cells.Item(1, $c+1).Value = [string]$s.headers[$c]
            $ws.Cells.Item(1, $c+1).Font.Bold = $true
        }}
    }}
    if ($s.rows) {{
        for ($r = 0; $r -lt $s.rows.Count; $r++) {{
            for ($c = 0; $c -lt $s.rows[$r].Count; $c++) {{
                $ws.Cells.Item($r+2, $c+1).Value = [string]$s.rows[$r][$c]
            }}
        }}
    }}
}}

$wb.SaveAs('{out_ps}')
$wb.Close()
$excel.Quit()
Write-Output 'SUCCESS'
""".format(sheets_b64=sheets_b64, out_ps=out_ps)
        
        stdout, stderr, rc = _run_ps_file(script)
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Xlsx created", "path": output_path}
        return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "output_path" not in params:
            return False, "Missing output_path"
        return True, None


class XlsxWriteTool(Tool):
    name = "xlsx_write"
    description = "Write data to Excel cells"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .xlsx path"},
        {"name": "output_path", "type": "string", "required": False, "description": "Output path"},
        {"name": "cell", "type": "string", "required": True, "description": "Cell like A1"},
        {"name": "value", "type": "string", "required": True, "description": "Value"},
        {"name": "sheet_name", "type": "string", "required": False, "description": "Sheet name"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        output_path = kwargs.get("output_path", input_path)
        cell = kwargs.get("cell", "")
        value = kwargs.get("value", "")
        sheet_name = kwargs.get("sheet_name", "")
        
        if not input_path or not cell:
            return {"success": False, "error": "Missing required params"}
        
        in_ps = _ps_str(input_path)
        out_ps = _ps_str(output_path)
        cell_ps = _ps_str(cell)
        val_ps = _ps_str(str(value))
        sheet_line = "$ws = $wb.Worksheets.Item('{0}')".format(_ps_str(sheet_name)) if sheet_name else "$ws = $wb.ActiveSheet"
        
        script = """
$ErrorActionPreference = 'Stop'
try {{
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $wb = $excel.Workbooks.Open('{in_ps}')
    SHEET_LINE
    $ws.Range('CELL_PLACEHOLDER').Value = 'VAL_PLACEHOLDER'
    $wb.SaveAs('{out_ps}')
    $wb.Close()
    $excel.Quit()
    Write-Output 'SUCCESS'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $excel.Quit() }} catch {{}}
}}
""".replace("IN_PLACEHOLDER", in_ps) \
           .replace("OUT_PLACEHOLDER", out_ps) \
           .replace("CELL_PLACEHOLDER", cell_ps) \
           .replace("VAL_PLACEHOLDER", val_ps) \
           .replace("SHEET_LINE", sheet_line)
        
        stdout, stderr, rc = _run_ps_file(script)
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Written to " + cell}
        return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "input_path" not in params or "cell" not in params:
            return False, "Missing required params"
        return True, None


class XlsxReadTool(Tool):
    name = "xlsx_read"
    description = "Read data from Excel workbook"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .xlsx path"},
        {"name": "sheet_name", "type": "string", "required": False, "description": "Sheet name"},
        {"name": "max_rows", "type": "int", "required": False, "description": "Max rows"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        sheet_name = kwargs.get("sheet_name", "")
        max_rows = kwargs.get("max_rows", 100)
        
        if not input_path:
            return {"success": False, "error": "Missing input_path"}
        if not os.path.exists(input_path):
            return {"success": False, "error": "File not found"}
        
        in_ps = _ps_str(input_path)
        sheet_line = "$wb.Worksheets.Item('{0}').Select()".format(_ps_str(sheet_name)) if sheet_name else ""
        
        script = """
$ErrorActionPreference = 'Stop'
try {{
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $wb = $excel.Workbooks.Open('IN_PLACEHOLDER')
    SHEET_LINE
    $ws = $wb.ActiveSheet
    $used = $ws.UsedRange
    $rows = [math]::Min($used.Rows.Count, MAXROWS_PLACEHOLDER)
    $cols = [math]::Min($used.Columns.Count, 20)
    $data = @()
    for ($r = 1; $r -le $rows; $r++) {{
        $rowData = @()
        for ($c = 1; $c -le $cols; $c++) {{
            $rowData += [string]$ws.Cells.Item($r, $c).Text
        }}
        $data += ($rowData -join '`t')
    }}
    $wb.Close()
    $excel.Quit()
    $data -join '`n'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $excel.Quit() }} catch {{}}
}}
""".replace("IN_PLACEHOLDER", in_ps) \
           .replace("SHEET_LINE", sheet_line) \
           .replace("MAXROWS_PLACEHOLDER", str(max_rows))
        
        stdout, stderr, rc = _run_ps_file(script)
        if "ERROR" not in stdout:
            lines = stdout.split('\n') if stdout else []
            return {"success": True, "rows": lines, "count": len(lines)}
        return {"success": False, "error": stdout}
    
    def validate(self, params):
        if "input_path" not in params:
            return False, "Missing input_path"
        return True, None


# =============================================================================
# PPTX Operations
# =============================================================================

class PptxCreateTool(Tool):
    name = "pptx_create"
    description = "Create PowerPoint presentation with slides"
    parameters = [
        {"name": "output_path", "type": "string", "required": True, "description": "Output .pptx path"},
        {"name": "title", "type": "string", "required": False, "description": "Title slide text"},
        {"name": "slides", "type": "list", "required": False, "description": "List of slide dicts with type/title/bullets/headers/rows/text"},
        {"name": "style", "type": "string", "required": False, "description": "business_blue/academic_white/creative_purple/tech_dark/minimal_gray"}
    ]

    def execute(self, **kwargs):
        output_path = kwargs.get("output_path", "")
        title = kwargs.get("title", "Presentation")
        slides = kwargs.get("slides", [])
        style = kwargs.get("style", "business_blue")

        if not output_path:
            return {"success": False, "error": "Missing output_path"}

        # Resolve relative paths to absolute
        if not os.path.isabs(output_path):
            output_path = os.path.abspath(output_path)

        out_ps = _ps_str(output_path)
        title_ps = _ps_str(title)
        slides_json = json.dumps(slides, ensure_ascii=False)
        slides_b64 = base64.b64encode(slides_json.encode('utf-16-le')).decode()

        script = """
$ErrorActionPreference = 'Stop'
$slideData = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String('{slides_b64}')) | ConvertFrom-Json

$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = 1
$pres = $ppt.Presentations.Add()
if ('{title_ps}') {{
    $slide = $pres.Slides.Add(1, 1)
    $slide.Shapes.Title.TextFrame.TextRange.Text = '{title_ps}'
}}

foreach ($s in $slideData) {{
    $type = [string]$s.type
    $title = [string]$s.title
    $bullets = @()
    if ($s.bullets) {{ $bullets = @($s.bullets) }}
    $headers = @()
    if ($s.headers) {{ $headers = @($s.headers) }}
    $rows = @()
    if ($s.rows) {{ $rows = @($s.rows) }}

    if ($type -eq 'section') {{
        $slide = $pres.Slides.Add($pres.Slides.Count + 1, 7)
        $slide.Shapes.Title.TextFrame.TextRange.Text = [string]$s.text
    }} elseif ($type -eq 'table' -and $headers.Count -gt 0) {{
        $slide = $pres.Slides.Add($pres.Slides.Count + 1, 2)
        if ($title) {{ $slide.Shapes.Title.TextFrame.TextRange.Text = $title }}
        $rowsCount = $rows.Count
        $colsCount = $headers.Count
        if ($colsCount -gt 0 -and $rowsCount -gt 0) {{
            $tbl = $slide.Shapes.AddTable($rowsCount + 1, $colsCount, 50, 1500, 8500, 4500).Table
            for ($c = 0; $c -lt $colsCount; $c++) {{
                $tbl.Cell(1, $c+1).Shape.TextFrame.TextRange.Text = [string]$headers[$c]
            }}
            for ($r = 0; $r -lt $rowsCount; $r++) {{
                for ($c = 0; $c -lt $colsCount; $c++) {{
                    $val = ''
                    if ($rows[$r] -and $rows[$r][$c] -ne $null) {{ $val = [string]$rows[$r][$c] }}
                    $tbl.Cell($r+2, $c+1).Shape.TextFrame.TextRange.Text = $val
                }}
            }}
        }}
    }} else {{
        $slide = $pres.Slides.Add($pres.Slides.Count + 1, 2)
        if ($title) {{ $slide.Shapes.Title.TextFrame.TextRange.Text = $title }}
        if ($bullets.Count -gt 0) {{
            $textParts = $bullets | ForEach-Object {{ [char]9679 + ' ' + [string]$_ }}
            $combined = $textParts -join [char]10
            $shape = $slide.Shapes.AddTextbox(1, 500, 1000, 8000, 5000)
            $tf = $shape.TextFrame
            $tf.WordWrap = $true
            $tf.TextRange.Text = $combined
        }}
    }}
}}

$pres.SaveAs('{out_ps}')
$pres.Close()
$ppt.Quit()
Write-Output 'SUCCESS'
""".format(slides_b64=slides_b64, title_ps=title_ps, out_ps=out_ps)

        stdout, stderr, rc = _run_ps_file(script)
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Pptx created", "path": output_path}
        return {"success": False, "error": stdout if "ERROR" in stdout else stderr}

    def validate(self, params):
        if "output_path" not in params:
            return False, "Missing output_path"
        return True, None


# =============================================================================
# PDF Operations (via Office COM)
# =============================================================================

class PdfMergeTool(Tool):
    """PDF merge requires Adobe Acrobat. For Office files, use office_word_to_pdf etc."""
    
    name = "pdf_merge"
    description = "Merge multiple PDF files (requires Adobe Acrobat)"
    parameters = [
        {"name": "input_paths", "type": "list", "required": True, "description": "List of input PDF paths"},
        {"name": "output_path", "type": "string", "required": True, "description": "Output merged PDF path"}
    ]
    
    def execute(self, **kwargs):
        return {"success": False, "error": "PDF merge requires Adobe Acrobat. For Office-to-PDF, use office_word_to_pdf / office_excel_to_pdf / office_ppt_to_pdf"}
    
    def validate(self, params):
        if "input_paths" not in params or "output_path" not in params:
            return False, "Missing required params"
        return True, None


def register_tools(registry):
    registry.register(DocxCreateTool())
    registry.register(DocxEditTool())
    registry.register(DocxReadTool())
    registry.register(XlsxCreateTool())
    registry.register(XlsxWriteTool())
    registry.register(XlsxReadTool())
    registry.register(PptxCreateTool())
    registry.register(PdfMergeTool())