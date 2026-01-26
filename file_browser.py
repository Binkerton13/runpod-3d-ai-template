#!/usr/bin/env python3
"""
Lightweight file browser with upload, download, delete, and text editing.
Runs on port 8080 by default.
"""

import os
import mimetypes
from pathlib import Path
from flask import (
    Flask, render_template_string, request,
    send_file, jsonify, redirect, url_for
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB max upload
BASE_DIR = os.environ.get('WORKSPACE', '/workspace')


# ---------------------------------------------------------------------
# HTML TEMPLATE
# ---------------------------------------------------------------------
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>File Browser</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #4fc3f7; margin-bottom: 20px; }
        .breadcrumb {
            background: #2d2d30;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .breadcrumb a { color: #4fc3f7; text-decoration: none; }
        .breadcrumb a:hover { text-decoration: underline; }
        .breadcrumb span { margin: 0 5px; color: #858585; }
        .toolbar {
            background: #2d2d30;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        button, .btn {
            background: #0e639c;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        button:hover, .btn:hover { background: #1177bb; }
        table {
            width: 100%;
            border-collapse: collapse;
            background: #252526;
            border-radius: 4px;
            overflow: hidden;
        }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #333;
        }
        th { background: #333; color: #4fc3f7; text-align: left; }
        tr:hover { background: #2d2d30; }
        a { color: #4fc3f7; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .delete-btn {
            background: #c62828;
            padding: 6px 12px;
            border-radius: 4px;
            color: white;
        }
        .delete-btn:hover { background: #e53935; }
        textarea {
            width: 100%;
            height: 400px;
            background: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #555;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>File Browser</h1>

    <div class="breadcrumb">
        {% for part, link in breadcrumb %}
            <a href="{{ link }}">{{ part }}</a>
            {% if not loop.last %}<span>/</span>{% endif %}
        {% endfor %}
    </div>

    <div class="toolbar">
        <form action="{{ url_for('upload', path=current_path) }}" method="post" enctype="multipart/form-data">
            <input type="file" name="file">
            <button type="submit">Upload</button>
        </form>
        <a class="btn" href="{{ url_for('edit_file', path=current_path) }}">New File</a>
    </div>

    <table>
        <tr>
            <th>Name</th>
            <th>Size</th>
            <th>Actions</th>
        </tr>
        {% for item in items %}
        <tr>
            <td>
                {% if item.is_dir %}
                    <a href="{{ url_for('browse', path=item.rel_path) }}">{{ item.name }}/</a>
                {% else %}
                    <a href="{{ url_for('download', path=item.rel_path) }}">{{ item.name }}</a>
                {% endif %}
            </td>
            <td>{{ item.size }}</td>
            <td>
                {% if not item.is_dir %}
                    <a class="btn" href="{{ url_for('edit_file', path=item.rel_path) }}">Edit</a>
                {% endif %}
                <a class="delete-btn" href="{{ url_for('delete', path=item.rel_path) }}">Delete</a>
            </td>
        </tr>
        {% endfor %}
    </table>
</div>
</body>
</html>
'''


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def safe_path(path: str) -> Path:
    """Ensure paths stay inside BASE_DIR."""
    full = Path(BASE_DIR, path).resolve()
    if not str(full).startswith(str(Path(BASE_DIR).resolve())):
        raise PermissionError("Invalid path")
    return full


def format_size(path: Path) -> str:
    if path.is_dir():
        return "-"
    size = path.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def browse(path):
    full = safe_path(path)
    if not full.exists():
        return "Not found", 404

    items = []
    for entry in sorted(full.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        items.append({
            "name": entry.name,
            "rel_path": str(Path(path, entry.name)),
            "is_dir": entry.is_dir(),
            "size": format_size(entry)
        })

    breadcrumb = []
    parts = Path(path).parts
    for i in range(len(parts) + 1):
        sub = Path(*parts[:i])
        breadcrumb.append((sub.name if sub.name else "root", "/" + str(sub)))

    return render_template_string(
        HTML_TEMPLATE,
        items=items,
        breadcrumb=breadcrumb,
        current_path=path
    )


@app.route("/download/<path:path>")
def download(path):
    full = safe_path(path)
    if not full.exists():
        return "Not found", 404
    return send_file(full, as_attachment=True)


@app.route("/delete/<path:path>")
def delete(path):
    full = safe_path(path)
    if full.is_dir():
        for root, dirs, files in os.walk(full, topdown=False):
            for f in files:
                os.remove(Path(root, f))
            for d in dirs:
                os.rmdir(Path(root, d))
        os.rmdir(full)
    else:
        os.remove(full)
    return redirect(url_for("browse", path=str(Path(path).parent)))


@app.route("/upload/<path:path>", methods=["POST"])
def upload(path):
    full = safe_path(path)
    file = request.files.get("file")
    if not file:
        return redirect(url_for("browse", path=path))

    filename = secure_filename(file.filename)
    file.save(str(full / filename))
    return redirect(url_for("browse", path=path))


@app.route("/edit/<path:path>", methods=["GET", "POST"])
def edit_file(path):
    full = safe_path(path)

    if request.method == "POST":
        content = request.form.get("content", "")
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return redirect(url_for("browse", path=str(full.parent.relative_to(BASE_DIR))))

    existing = ""
    if full.exists() and full.is_file():
        existing = full.read_text(encoding="utf-8")

    return f"""
    <html><body style="background:#1e1e1e;color:#d4d4d4;padding:20px;">
    <h2>Editing: {path}</h2>
    <form method="post">
        <textarea name="content">{existing}</textarea><br><br>
        <button type="submit">Save</button>
    </form>
    </body></html>
    """


# ---------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("FILE_BROWSER_PORT", 8080))
    app.run(host="0.0.0.0", port=port)
