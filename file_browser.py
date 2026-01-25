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
...existing code...
