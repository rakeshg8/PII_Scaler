import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.background import BackgroundTasks

# Import custom modules
from src.docx_io import read_docx, save_docx
from src.redactor import Redactor

app = FastAPI(title="PII Redactor API")

# Simple HTML page with upload form
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>PII Redaction Tool</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            color: #333;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        h2 { color: #1a73e8; text-align: center; }
        .form-group { margin: 20px 0; }
        input[type="file"] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button {
            width: 100%;
            background: #1a73e8;
            color: white;
            border: none;
            padding: 12px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover { background: #1557b0; }
        .error { color: #d93025; background: #fce8e6; padding: 10px; border-radius: 4px; margin: 15px 0; border: 1px solid #fad2cf; }
    </style>
</head>
<body>
    <h2>PII Redactor Tool</h2>
    <p>Upload a Word Document (.docx) to redact and replace PII with realistic Indian alternatives.</p>
    <form action="/redact" method="post" enctype="multipart/form-data">
        <div class="form-group">
            <input type="file" name="file" accept=".docx" required>
        </div>
        <button type="submit">Upload and Redact</button>
    </form>
    <div style="margin-top: 20px; font-size: 13px; color: #666; text-align: center; line-height: 1.4;">
        Note: Hosted on Render's free tier — if idle for 15+ minutes, the first request may take up to ~50s to respond while the instance spins up.
    </div>
</body>
</html>
"""

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Redaction Error</title>
    <meta charset="utf-8">
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; }
        h2 { color: #d93025; }
        a { display: inline-block; margin-top: 20px; text-decoration: none; color: #1a73e8; font-weight: bold; }
    </style>
</head>
<body>
    <h2>Redaction Processing Failed</h2>
    <p>{error_msg}</p>
    <a href="/">Back to Upload</a>
</body>
</html>
"""

def clean_temp_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE

@app.post("/redact")
async def redact_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        return HTMLResponse(
            content=ERROR_TEMPLATE.format(error_msg="Invalid file format. Please upload a Microsoft Word document (.docx)."),
            status_code=400
        )
    
    # Write uploaded file to temp file
    fd, input_temp_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    output_temp_path = input_temp_path.replace(".docx", "_redacted.docx")
    
    background_tasks.add_task(clean_temp_file, input_temp_path)
    background_tasks.add_task(clean_temp_file, output_temp_path)
    
    try:
        with open(input_temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Parse document
        try:
            doc = read_docx(input_temp_path)
        except Exception:
            return HTMLResponse(
                content=ERROR_TEMPLATE.format(error_msg="Could not read document. Ensure it is a valid, uncorrupted .docx file."),
                status_code=400
            )
            
        # Run redactor
        redactor = Redactor()
        redactor.redact_document(doc)
        
        # Save output
        save_docx(doc, output_temp_path)
        
        return FileResponse(
            path=output_temp_path,
            filename=file.filename.replace(".docx", "_redacted.docx"),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except Exception as e:
        return HTMLResponse(
            content=ERROR_TEMPLATE.format(error_msg=f"Redaction failed: {str(e)}"),
            status_code=500
        )
