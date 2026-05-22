"""
Office Operations via PowerShell + Windows COM
Zero external dependencies - works on Python 3.7 + Office 2010
"""
import os
import tempfile
import base64
from .base import Tool


def _run_powershell(script):
    """Run a PowerShell script and return output."""
    import subprocess
    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class WordToPdfTool(Tool):
    """Convert Word document to PDF via COM."""
    
    name = "office_word_to_pdf"
    description = "Convert Word document to PDF using Office COM"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .docx file path"},
        {"name": "output_path", "type": "string", "required": False, "description": "Output .pdf path (default: same name, .pdf)"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        output_path = kwargs.get("output_path", "")
        
        if not input_path:
            return {"success": False, "error": "Missing input_path"}
        
        if not os.path.exists(input_path):
            return {"success": False, "error": "File not found: " + input_path}
        
        if not output_path:
            output_path = os.path.splitext(input_path)[0] + ".pdf"
        
        # Escape paths for PowerShell
        input_path_ps = input_path.replace("'", "''")
        output_path_ps = output_path.replace("'", "''")
        
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open('{input_path_ps}', $false, $true)
    $doc.SaveAs('{output_path_ps}', 17)
    $doc.Close($false)
    $word.Quit()
    Write-Output 'SUCCESS'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $word.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Converted to PDF", "output": output_path}
        else:
            return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "input_path" not in params:
            return False, "Missing required parameter: input_path"
        return True, None


class ExcelToPdfTool(Tool):
    """Convert Excel workbook to PDF via COM."""
    
    name = "office_excel_to_pdf"
    description = "Convert Excel workbook to PDF using Office COM"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .xlsx file path"},
        {"name": "output_path", "type": "string", "required": False, "description": "Output .pdf path"},
        {"name": "sheet_index", "type": "int", "required": False, "description": "Sheet index to export (0=all, default=0)"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        output_path = kwargs.get("output_path", "")
        sheet_index = kwargs.get("sheet_index", 0)
        
        if not input_path:
            return {"success": False, "error": "Missing input_path"}
        
        if not os.path.exists(input_path):
            return {"success": False, "error": "File not found: " + input_path}
        
        if not output_path:
            output_path = os.path.splitext(input_path)[0] + ".pdf"
        
        input_path_ps = input_path.replace("'", "''")
        output_path_ps = output_path.replace("'", "''")
        
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $wb = $excel.Workbooks.Open('{input_path_ps}')
    
    if ({sheet_index} -gt 0) {{
        $wb.Sheets({sheet_index}).Select()
    }}
    
    $wb.ActiveSheet.ExportAsFixedFormat(0, '{output_path_ps}')
    $wb.Close($false)
    $excel.Quit()
    Write-Output 'SUCCESS'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $excel.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Converted to PDF", "output": output_path}
        else:
            return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "input_path" not in params:
            return False, "Missing required parameter: input_path"
        return True, None


class PptToPdfTool(Tool):
    """Convert PowerPoint presentation to PDF via COM."""
    
    name = "office_ppt_to_pdf"
    description = "Convert PowerPoint to PDF using Office COM"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .pptx file path"},
        {"name": "output_path", "type": "string", "required": False, "description": "Output .pdf path"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        output_path = kwargs.get("output_path", "")
        
        if not input_path:
            return {"success": False, "error": "Missing input_path"}
        
        if not os.path.exists(input_path):
            return {"success": False, "error": "File not found: " + input_path}
        
        if not output_path:
            output_path = os.path.splitext(input_path)[0] + ".pdf"
        
        input_path_ps = input_path.replace("'", "''")
        output_path_ps = output_path.replace("'", "''")
        
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $ppt = New-Object -ComObject PowerPoint.Application
    $ppt.Visible = 1
    $pres = $ppt.Presentations.Open('{input_path_ps}', $false, $false, $false)
    $pres.SaveAs('{output_path_ps}', 32)
    $pres.Close()
    $ppt.Quit()
    Write-Output 'SUCCESS'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $ppt.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Converted to PDF", "output": output_path}
        else:
            return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "input_path" not in params:
            return False, "Missing required parameter: input_path"
        return True, None


class WordNewDocTool(Tool):
    """Create a new Word document."""
    
    name = "office_word_new"
    description = "Create a new Word document"
    parameters = [
        {"name": "output_path", "type": "string", "required": True, "description": "Output .docx path"},
        {"name": "content", "type": "string", "required": False, "description": "Initial text content"}
    ]
    
    def execute(self, **kwargs):
        output_path = kwargs.get("output_path", "")
        content = kwargs.get("content", "")
        
        if not output_path:
            return {"success": False, "error": "Missing output_path"}
        
        output_path_ps = output_path.replace("'", "''")
        content_escaped = content.replace("'", "''").replace("\n", "`n")
        
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Add()
    if ('{content_escaped}') {{
        $doc.Content.Text = '{content_escaped}'
    }}
    $doc.SaveAs('{output_path_ps}')
    $doc.Close($false)
    $word.Quit()
    Write-Output 'SUCCESS'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $word.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Word document created", "path": output_path}
        else:
            return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "output_path" not in params:
            return False, "Missing required parameter: output_path"
        return True, None


class ExcelNewWorkbookTool(Tool):
    """Create a new Excel workbook."""
    
    name = "office_excel_new"
    description = "Create a new Excel workbook"
    parameters = [
        {"name": "output_path", "type": "string", "required": True, "description": "Output .xlsx path"},
        {"name": "sheets", "type": "list", "required": False, "description": "List of sheet names"}
    ]
    
    def execute(self, **kwargs):
        output_path = kwargs.get("output_path", "")
        sheets = kwargs.get("sheets", [])
        
        if not output_path:
            return {"success": False, "error": "Missing output_path"}
        
        output_path_ps = output_path.replace("'", "''")
        # Convert Python list to PowerShell array: ['A','B'] -> '"A"','"B"'
        if sheets:
            ps_array = ','.join("'{0}'".format(s.replace("'", "''")) for s in sheets)
        else:
            ps_array = ''
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $wb = $excel.Workbooks.Add()
    
    $sheetNames = @({ps_array})
    if ($sheetNames.Count -gt 0) {{
        $wb.Sheets[1].Name = $sheetNames[0]
        for ($i = 1; $i -lt $sheetNames.Count; $i++) {{
            $wb.Sheets.Add() | Out-Null
            $wb.Sheets[$wb.Sheets.Count].Name = $sheetNames[$i]
        }}
    }}
    
    $wb.SaveAs('{output_path_ps}')
    $wb.Close($false)
    $excel.Quit()
    Write-Output 'SUCCESS'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $excel.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Excel workbook created", "path": output_path}
        else:
            return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "output_path" not in params:
            return False, "Missing required parameter: output_path"
        return True, None


class PptNewPresentationTool(Tool):
    """Create a new PowerPoint presentation."""
    
    name = "office_ppt_new"
    description = "Create a new PowerPoint presentation"
    parameters = [
        {"name": "output_path", "type": "string", "required": True, "description": "Output .pptx path"},
        {"name": "title", "type": "string", "required": False, "description": "Title slide text"}
    ]
    
    def execute(self, **kwargs):
        output_path = kwargs.get("output_path", "")
        title = kwargs.get("title", "Presentation")
        
        if not output_path:
            return {"success": False, "error": "Missing output_path"}
        
        output_path_ps = output_path.replace("'", "''")
        title_escaped = title.replace("'", "''")
        
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $ppt = New-Object -ComObject PowerPoint.Application
    $ppt.Visible = 1
    $pres = $ppt.Presentations.Add()
    $slide = $pres.Slides.Add(1, 1)
    $slide.Shapes.Title.TextFrame.TextRange.Text = '{title_escaped}'
    $pres.SaveAs('{output_path_ps}')
    $pres.Close()
    $ppt.Quit()
    Write-Output 'SUCCESS'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $ppt.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "SUCCESS" in stdout:
            return {"success": True, "result": "PowerPoint presentation created", "path": output_path}
        else:
            return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "output_path" not in params:
            return False, "Missing required parameter: output_path"
        return True, None


class WordReadContentTool(Tool):
    """Read text content from a Word document."""
    
    name = "office_word_read"
    description = "Read text content from Word document"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .docx file path"},
        {"name": "max_chars", "type": "int", "required": False, "description": "Max characters to read (default=5000)"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        max_chars = kwargs.get("max_chars", 5000)
        
        if not input_path:
            return {"success": False, "error": "Missing input_path"}
        
        if not os.path.exists(input_path):
            return {"success": False, "error": "File not found: " + input_path}
        
        input_path_ps = input_path.replace("'", "''")
        
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Open('{input_path_ps}', $false, $true)
    $text = $doc.Content.Text
    $doc.Close($false)
    $word.Quit()
    Write-Output $text
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $word.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "ERROR" not in stdout:
            return {"success": True, "content": stdout[:max_chars], "length": len(stdout)}
        else:
            return {"success": False, "error": stdout}
    
    def validate(self, params):
        if "input_path" not in params:
            return False, "Missing required parameter: input_path"
        return True, None


class ExcelReadContentTool(Tool):
    """Read content from an Excel workbook."""
    
    name = "office_excel_read"
    description = "Read content from Excel workbook"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .xlsx file path"},
        {"name": "sheet_name", "type": "string", "required": False, "description": "Sheet name (default=first sheet)"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        sheet_name = kwargs.get("sheet_name", "")
        
        if not input_path:
            return {"success": False, "error": "Missing input_path"}
        
        if not os.path.exists(input_path):
            return {"success": False, "error": "File not found: " + input_path}
        
        input_path_ps = input_path.replace("'", "''")
        sheet_clause = f"$wb.Worksheets.Item('{sheet_name}').Select()" if sheet_name else ""
        
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $wb = $excel.Workbooks.Open('{input_path_ps}')
    {sheet_clause}
    $ws = $wb.ActiveSheet
    $used = $ws.UsedRange
    $rows = $used.Rows.Count
    $cols = $used.Columns.Count
    $data = @()
    for ($r = 1; $r -le [math]::Min($rows, 100); $r++) {{
        $rowData = @()
        for ($c = 1; $c -le [math]::Min($cols, 20); $c++) {{
            $val = $ws.Cells.Item($r, $c).Text
            $rowData += $val
        }}
        $data += ($rowData -join '`t')
    }}
    $wb.Close($false)
    $excel.Quit()
    $data -join '`n'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $excel.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "ERROR" not in stdout:
            lines = stdout.split('\n') if stdout else []
            return {"success": True, "rows": lines, "count": len(lines)}
        else:
            return {"success": False, "error": stdout}
    
    def validate(self, params):
        if "input_path" not in params:
            return False, "Missing required parameter: input_path"
        return True, None


class WordEditTool(Tool):
    """Edit text in an existing Word document."""
    
    name = "office_word_edit"
    description = "Replace text in Word document"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .docx file path"},
        {"name": "output_path", "type": "string", "required": False, "description": "Output path (default=overwrite input)"},
        {"name": "find", "type": "string", "required": True, "description": "Text to find"},
        {"name": "replace", "type": "string", "required": True, "description": "Replacement text"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        output_path = kwargs.get("output_path", input_path)
        find_text = kwargs.get("find", "")
        replace_text = kwargs.get("replace", "")
        
        if not input_path:
            return {"success": False, "error": "Missing input_path"}
        
        if not os.path.exists(input_path):
            return {"success": False, "error": "File not found: " + input_path}
        
        if not find_text:
            return {"success": False, "error": "Missing find parameter"}
        
        input_path_ps = input_path.replace("'", "''")
        output_path_ps = output_path.replace("'", "''")
        find_escaped = find_text.replace("'", "''")
        replace_escaped = replace_text.replace("'", "''")
        
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Open('{input_path_ps}')
    $find = $doc.Content.Find
    $find.ClearFormatting()
    $find.Text = '{find_escaped}'
    $find.Replacement.ClearFormatting()
    $find.Replacement.Text = '{replace_escaped}'
    $found = $find.Execute($false, $false, $false, $false, $false, $false, 1, $false, $false, 0)
    $count = 0
    while ($found) {{
        $count++
        $found = $find.Execute($false, $false, $false, $false, $false, $false, 1, $false, $false, 0)
    }}
    $doc.SaveAs('{output_path_ps}')
    $doc.Close($false)
    $word.Quit()
    Write-Output ('SUCCESS: ' + $count + ' replacements')
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $word.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "SUCCESS" in stdout:
            return {"success": True, "result": stdout}
        else:
            return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "input_path" not in params:
            return False, "Missing required parameter: input_path"
        if "find" not in params:
            return False, "Missing required parameter: find"
        return True, None


class ExcelWriteCellTool(Tool):
    """Write value to an Excel cell."""
    
    name = "office_excel_write"
    description = "Write value to Excel cell"
    parameters = [
        {"name": "input_path", "type": "string", "required": True, "description": "Input .xlsx file path"},
        {"name": "output_path", "type": "string", "required": False, "description": "Output path"},
        {"name": "cell", "type": "string", "required": True, "description": "Cell address (e.g. A1, B2)"},
        {"name": "value", "type": "string", "required": True, "description": "Value to write"},
        {"name": "sheet_name", "type": "string", "required": False, "description": "Sheet name"}
    ]
    
    def execute(self, **kwargs):
        input_path = kwargs.get("input_path", "")
        output_path = kwargs.get("output_path", input_path)
        cell = kwargs.get("cell", "")
        value = kwargs.get("value", "")
        sheet_name = kwargs.get("sheet_name", "")
        
        if not input_path or not cell:
            return {"success": False, "error": "Missing required parameters"}
        
        if not os.path.exists(input_path):
            return {"success": False, "error": "File not found: " + input_path}
        
        input_path_ps = input_path.replace("'", "''")
        output_path_ps = output_path.replace("'", "''")
        value_escaped = str(value).replace("'", "''")
        cell_escaped = cell.replace("'", "''")
        sheet_clause = f"$ws = $wb.Worksheets.Item('{sheet_name}')" if sheet_name else "$ws = $wb.ActiveSheet"
        
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $wb = $excel.Workbooks.Open('{input_path_ps}')
    {sheet_clause}
    $ws.Range('{cell_escaped}').Value = '{value_escaped}'
    $wb.SaveAs('{output_path_ps}')
    $wb.Close($false)
    $excel.Quit()
    Write-Output 'SUCCESS'
}} catch {{
    Write-Output ('ERROR: ' + $_.Exception.Message)
    try {{ $excel.Quit() }} catch {{}}
}}
"""
        stdout, stderr, rc = _run_powershell(script)
        
        if "SUCCESS" in stdout:
            return {"success": True, "result": "Written to " + cell, "path": output_path}
        else:
            return {"success": False, "error": stdout if "ERROR" in stdout else stderr}
    
    def validate(self, params):
        if "input_path" not in params:
            return False, "Missing required parameter: input_path"
        if "cell" not in params:
            return False, "Missing required parameter: cell"
        return True, None


def register_tools(registry):
    """Register all Office tools."""
    registry.register(WordToPdfTool())
    registry.register(ExcelToPdfTool())
    registry.register(PptToPdfTool())
    registry.register(WordNewDocTool())
    registry.register(ExcelNewWorkbookTool())
    registry.register(PptNewPresentationTool())
    registry.register(WordReadContentTool())
    registry.register(ExcelReadContentTool())
    registry.register(WordEditTool())
    registry.register(ExcelWriteCellTool())