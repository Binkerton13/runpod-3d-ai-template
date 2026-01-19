#!/usr/bin/env python3
"""
Lightweight file browser with upload and editing capabilities.
Runs on port 8080 by default.
"""
import os
import mimetypes
from pathlib import Path
from flask import Flask, render_template_string, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB max upload
BASE_DIR = os.environ.get('WORKSPACE', '/workspace')

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
        input[type="text"], input[type="file"], textarea {
            background: #3c3c3c;
            color: #d4d4d4;
            border: 1px solid #555;
            padding: 8px;
            border-radius: 4px;
            font-size: 14px;
        }
        .file-list {
            background: #252526;
            border-radius: 4px;
            overflow: hidden;
        }
        .file-item {
            padding: 12px 15px;
            border-bottom: 1px solid #3c3c3c;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .file-item:hover { background: #2d2d30; }
        .file-item:last-child { border-bottom: none; }
        .file-name {
            display: flex;
            align-items: center;
            flex: 1;
        }
        .file-icon {
            margin-right: 10px;
            font-size: 20px;
        }
        .file-actions {
            display: flex;
            gap: 10px;
        }
        .file-actions a, .file-actions button {
            padding: 4px 12px;
            font-size: 12px;
            text-decoration: none;
            color: white;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
        }
        .modal-content {
            background: #252526;
            margin: 50px auto;
            padding: 20px;
            max-width: 900px;
            border-radius: 4px;
            max-height: 80vh;
            overflow: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .close {
            font-size: 28px;
            cursor: pointer;
            color: #d4d4d4;
        }
        .close:hover { color: #4fc3f7; }
        textarea {
            width: 100%;
            min-height: 400px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            margin-bottom: 10px;
        }
        .upload-area {
            border: 2px dashed #555;
            padding: 30px;
            text-align: center;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .upload-area.dragover { border-color: #4fc3f7; background: #2d2d30; }
        .alert {
            padding: 12px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .alert-success { background: #1e5631; color: #a5d6a7; }
        .alert-error { background: #5a1d1d; color: #f48fb1; }
        .file-size { color: #858585; font-size: 12px; margin-left: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📁 File Browser</h1>
        
        {% if message %}
        <div class="alert alert-{{ message_type }}">{{ message }}</div>
        {% endif %}
        
        <div class="breadcrumb">
            <a href="/">🏠 workspace</a>
            {% for i, part in enumerate(path_parts) %}
                <span>/</span>
                <a href="/browse/{{ '/'.join(path_parts[:i+1]) }}">{{ part }}</a>
            {% endfor %}
        </div>
        
        <div class="toolbar">
            <button onclick="showUploadModal()">⬆️ Upload Files</button>
            <button onclick="showNewFolderModal()">📁 New Folder</button>
            <button onclick="showNewFileModal()">📄 New File</button>
        </div>
        
        <div class="file-list">
            {% if current_path != '/' %}
            <div class="file-item">
                <div class="file-name">
                    <span class="file-icon">⬆️</span>
                    <a href="/browse/{{ parent_path }}" style="color: #4fc3f7; text-decoration: none;">.. (parent directory)</a>
                </div>
            </div>
            {% endif %}
            
            {% for item in items %}
            <div class="file-item">
                <div class="file-name">
                    <span class="file-icon">{{ '📁' if item.is_dir else '📄' }}</span>
                    {% if item.is_dir %}
                        <a href="/browse/{{ item.url_path }}" style="color: #d4d4d4; text-decoration: none;">{{ item.name }}</a>
                    {% else %}
                        <span>{{ item.name }}</span>
                        <span class="file-size">{{ item.size }}</span>
                    {% endif %}
                </div>
                <div class="file-actions">
                    {% if not item.is_dir %}
                        <button onclick="editFile('{{ item.url_path }}', '{{ item.name }}')">✏️ Edit</button>
                        <a href="/download/{{ item.url_path }}" class="btn">⬇️ Download</a>
                    {% endif %}
                    <button onclick="renameItem('{{ item.url_path }}', '{{ item.name }}', {{ 'true' if item.is_dir else 'false' }})">📝 Rename</button>
                    <button onclick="deleteItem('{{ item.url_path }}', {{ 'true' if item.is_dir else 'false' }})">🗑️ Delete</button>
                </div>
            </div>
            {% endfor %}
            
            {% if not items %}
            <div class="file-item" style="justify-content: center; color: #858585;">
                <em>Empty directory</em>
            </div>
            {% endif %}
        </div>
    </div>

    <!-- Upload Modal -->
    <div id="uploadModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Upload Files</h2>
                <span class="close" onclick="closeModal('uploadModal')">&times;</span>
            </div>
            <form action="/upload" method="post" enctype="multipart/form-data" id="uploadForm">
                <input type="hidden" name="current_path" value="{{ current_path }}">
                <div class="upload-area" id="dropArea">
                    <p>Drag and drop files here or click to select</p>
                    <input type="file" name="files" multiple id="fileInput" style="display: none;">
                    <button type="button" onclick="document.getElementById('fileInput').click()">Select Files</button>
                </div>
                <div id="fileList"></div>
                <button type="submit">Upload</button>
            </form>
        </div>
    </div>

    <!-- New Folder Modal -->
    <div id="newFolderModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Create New Folder</h2>
                <span class="close" onclick="closeModal('newFolderModal')">&times;</span>
            </div>
            <form action="/mkdir" method="post">
                <input type="hidden" name="current_path" value="{{ current_path }}">
                <input type="text" name="folder_name" placeholder="Folder name" required style="width: 100%; margin-bottom: 10px;">
                <button type="submit">Create</button>
            </form>
        </div>
    </div>

    <!-- New File Modal -->
    <div id="newFileModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Create New File</h2>
                <span class="close" onclick="closeModal('newFileModal')">&times;</span>
            </div>
            <form action="/create_file" method="post">
                <input type="hidden" name="current_path" value="{{ current_path }}">
                <input type="text" name="file_name" placeholder="File name" required style="width: 100%; margin-bottom: 10px;">
                <button type="submit">Create</button>
            </form>
        </div>
    </div>

    <!-- Edit Modal -->
    <div id="editModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Edit: <span id="editFileName"></span></h2>
                <span class="close" onclick="closeModal('editModal')">&times;</span>
            </div>
            <form action="/save" method="post">
                <input type="hidden" name="file_path" id="editFilePath">
                <textarea name="content" id="editContent"></textarea>
                <button type="submit">💾 Save</button>
                <button type="button" onclick="closeModal('editModal')">Cancel</button>
            </form>
        </div>
    </div>

    <script>
        function showUploadModal() {
            document.getElementById('uploadModal').style.display = 'block';
        }
        function showNewFolderModal() {
            document.getElementById('newFolderModal').style.display = 'block';
        }
        function showNewFileModal() {
            document.getElementById('newFileModal').style.display = 'block';
        }
        function closeModal(id) {
            document.getElementById(id).style.display = 'none';
        }
        
        // Drag and drop
        const dropArea = document.getElementById('dropArea');
        const fileInput = document.getElementById('fileInput');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
        });
        
        dropArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            fileInput.files = files;
            updateFileList();
        }
        
        fileInput.addEventListener('change', updateFileList);
        
        function updateFileList() {
            const fileList = document.getElementById('fileList');
            const files = fileInput.files;
            if (files.length > 0) {
                fileList.innerHTML = '<strong>Selected files:</strong><ul>' + 
                    Array.from(files).map(f => `<li>${f.name} (${formatSize(f.size)})</li>`).join('') + 
                    '</ul>';
            }
        }
        
        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
            if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
            return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
        }
        
        function editFile(path, name) {
            document.getElementById('editFileName').textContent = name;
            document.getElementById('editFilePath').value = path;
            
            fetch('/read/' + path)
                .then(r => r.text())
                .then(content => {
                    document.getElementById('editContent').value = content;
                    document.getElementById('editModal').style.display = 'block';
                })
                .catch(err => alert('Error loading file: ' + err));
        }
        
        function deleteItem(path, isDir) {
            const type = isDir ? 'folder' : 'file';
            if (confirm(`Delete this ${type}?`)) {
                fetch('/delete/' + path, { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            location.reload();
                        } else {
                            alert('Error: ' + data.error);
                        }
                    })
                    .catch(err => alert('Error: ' + err));
            }
        }
        
        function renameItem(path, currentName, isDir) {
            const newName = prompt(`Rename ${isDir ? 'folder' : 'file'}:`, currentName);
            if (newName && newName !== currentName) {
                fetch('/rename', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: path, new_name: newName})
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(err => alert('Error: ' + err));
            }
        }
        
        // Close modal on outside click
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
            }
        }
    </script>
</body>
</html>
'''

def format_size(size):
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def get_safe_path(path):
    """Ensure path is within BASE_DIR."""
    if path.startswith('/'):
        path = path[1:]
    full_path = os.path.join(BASE_DIR, path)
    full_path = os.path.normpath(full_path)
    if not full_path.startswith(BASE_DIR):
        raise ValueError("Invalid path")
    return full_path

@app.route('/')
def index():
    return browse('')

@app.route('/browse/', defaults={'path': ''})
@app.route('/browse/<path:path>')
def browse(path):
    try:
        dir_path = get_safe_path(path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        items = []
        for item in sorted(os.listdir(dir_path)):
            item_path = os.path.join(dir_path, item)
            url_path = os.path.join(path, item).replace('\\', '/')
            
            is_dir = os.path.isdir(item_path)
            size = ''
            if not is_dir:
                try:
                    size = format_size(os.path.getsize(item_path))
                except:
                    size = 'N/A'
            
            items.append({
                'name': item,
                'is_dir': is_dir,
                'url_path': url_path,
                'size': size
            })
        
        path_parts = [p for p in path.split('/') if p]
        parent_path = '/'.join(path_parts[:-1]) if path_parts else ''
        
        return render_template_string(HTML_TEMPLATE,
            items=items,
            current_path='/' + path if path else '/',
            path_parts=path_parts,
            parent_path=parent_path,
            enumerate=enumerate,
            message=request.args.get('message'),
            message_type=request.args.get('message_type', 'success')
        )
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/upload', methods=['POST'])
def upload():
    try:
        current_path = request.form.get('current_path', '/').lstrip('/')
        dir_path = get_safe_path(current_path)
        
        files = request.files.getlist('files')
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(dir_path, filename))
        
        return redirect(f'/browse/{current_path}?message=Files uploaded successfully&message_type=success')
    except Exception as e:
        return redirect(f'/browse/{current_path}?message={str(e)}&message_type=error')

@app.route('/mkdir', methods=['POST'])
def mkdir():
    try:
        current_path = request.form.get('current_path', '/').lstrip('/')
        folder_name = secure_filename(request.form.get('folder_name'))
        dir_path = get_safe_path(os.path.join(current_path, folder_name))
        os.makedirs(dir_path, exist_ok=True)
        return redirect(f'/browse/{current_path}?message=Folder created successfully&message_type=success')
    except Exception as e:
        return redirect(f'/browse/{current_path}?message={str(e)}&message_type=error')

@app.route('/create_file', methods=['POST'])
def create_file():
    try:
        current_path = request.form.get('current_path', '/').lstrip('/')
        file_name = secure_filename(request.form.get('file_name'))
        file_path = get_safe_path(os.path.join(current_path, file_name))
        Path(file_path).touch()
        return redirect(f'/browse/{current_path}?message=File created successfully&message_type=success')
    except Exception as e:
        return redirect(f'/browse/{current_path}?message={str(e)}&message_type=error')

@app.route('/read/<path:path>')
def read_file(path):
    try:
        file_path = get_safe_path(path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return str(e), 500

@app.route('/save', methods=['POST'])
def save_file():
    try:
        file_path = get_safe_path(request.form.get('file_path'))
        content = request.form.get('content', '')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        parent_dir = os.path.dirname(request.form.get('file_path')).replace('\\', '/')
        return redirect(f'/browse/{parent_dir}?message=File saved successfully&message_type=success')
    except Exception as e:
        return redirect(f'/browse/?message={str(e)}&message_type=error')

@app.route('/download/<path:path>')
def download_file(path):
    try:
        file_path = get_safe_path(path)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return str(e), 500

@app.route('/delete/<path:path>', methods=['POST'])
def delete_item(path):
    try:
        item_path = get_safe_path(path)
        if os.path.isdir(item_path):
            import shutil
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/rename', methods=['POST'])
def rename_item():
    try:
        data = request.get_json()
        old_path = get_safe_path(data.get('path'))
        new_name = secure_filename(data.get('new_name'))
        
        # Get parent directory and construct new path
        parent_dir = os.path.dirname(old_path)
        new_path = os.path.join(parent_dir, new_name)
        
        # Ensure new path is safe
        new_path = os.path.normpath(new_path)
        if not new_path.startswith(os.path.normpath(BASE_DIR)):
            return jsonify({'success': False, 'error': 'Invalid path'})
        
        # Rename
        os.rename(old_path, new_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
if __name__ == '__main__':
    port = int(os.environ.get('FILE_BROWSER_PORT', 8080))
    print(f"Starting file browser on port {port}")
    print(f"Base directory: {BASE_DIR}")
    app.run(host='0.0.0.0', port=port, debug=False)
