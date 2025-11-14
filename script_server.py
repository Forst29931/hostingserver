from flask import Flask, send_file, abort, render_template_string, request, jsonify, session, redirect, url_for
import os
from pathlib import Path
import json
from functools import wraps
import secrets
import re
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Random secret key for sessions
BASE_DIR = "lua_scripts"  # Main folder containing all your script folders
CONFIG_FILE = "server_config.json"
ANALYTICS_FILE = "analytics.json"

# Natural sorting function for proper numeric ordering
def natural_sort_key(text):
    """
    Sort strings with numbers naturally (VPS1, VPS2, VPS10 instead of VPS1, VPS10, VPS2)
    """
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

# Load or create analytics data
def load_analytics():
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'r') as f:
            return json.load(f)
    return {"total_loads": 0, "scripts": {}, "history": []}

def save_analytics(data):
    with open(ANALYTICS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def track_script_load(folder, filename, ip_address=None):
    analytics = load_analytics()
    
    # Update total loads
    analytics["total_loads"] += 1
    
    # Create script key
    script_key = f"{folder}/{filename}"
    
    # Initialize script data if not exists
    if script_key not in analytics["scripts"]:
        analytics["scripts"][script_key] = {
            "total_loads": 0,
            "first_load": datetime.now().isoformat(),
            "last_load": datetime.now().isoformat(),
            "unique_ips": []
        }
    
    # Update script stats
    analytics["scripts"][script_key]["total_loads"] += 1
    analytics["scripts"][script_key]["last_load"] = datetime.now().isoformat()
    
    # Track unique IPs (store only last 100 to avoid bloat)
    if ip_address and ip_address not in analytics["scripts"][script_key]["unique_ips"]:
        analytics["scripts"][script_key]["unique_ips"].append(ip_address)
        if len(analytics["scripts"][script_key]["unique_ips"]) > 100:
            analytics["scripts"][script_key]["unique_ips"].pop(0)
    
    # Add to history (keep last 1000 events)
    analytics["history"].append({
        "timestamp": datetime.now().isoformat(),
        "script": script_key,
        "ip": ip_address
    })
    if len(analytics["history"]) > 1000:
        analytics["history"] = analytics["history"][-1000:]
    
    save_analytics(analytics)
    return analytics

# Default credentials (you should change these!)
DEFAULT_CONFIG = {
    "username": "admin",
    "password": "changeme123"  # CHANGE THIS!
}

# Create base directory if it doesn't exist
os.makedirs(BASE_DIR, exist_ok=True)

# Load or create config
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        CONFIG = json.load(f)
else:
    CONFIG = DEFAULT_CONFIG
    with open(CONFIG_FILE, 'w') as f:
        json.dump(CONFIG, f, indent=2)
    print(f"⚠️  Created config file. Default password: {DEFAULT_CONFIG['password']}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# HTML template for login page
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Script Server</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1e1e1e;
            color: #fff;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-box {
            background: #2d2d2d;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            width: 300px;
        }
        h1 {
            color: #4CAF50;
            text-align: center;
            margin-bottom: 30px;
        }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            background: #1a1a1a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 5px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #4CAF50;
            color: #000;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            margin-top: 10px;
        }
        button:hover {
            background: #45a049;
        }
        .error {
            color: #f44336;
            text-align: center;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🔒 Script Server</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required autofocus>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

# HTML template for the web editor
EDITOR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Roblox Script Server Manager</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #1e1e1e;
            color: #fff;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        h1 { color: #4CAF50; margin: 0; }
        .logout-btn {
            padding: 8px 15px;
            background: #f44336;
            color: #fff;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .folder-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 20px 0;
        }
        .folder-btn {
            padding: 10px 20px;
            background: #2d2d2d;
            border: 2px solid #4CAF50;
            color: #4CAF50;
            cursor: pointer;
            border-radius: 5px;
            font-size: 14px;
        }
        .folder-btn:hover {
            background: #4CAF50;
            color: #000;
        }
        .folder-btn.active {
            background: #4CAF50;
            color: #000;
        }
        .mass-edit-bar {
            background: #2d2d2d;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border: 2px solid #FF9800;
        }
        .mass-edit-bar h3 {
            margin: 0 0 10px 0;
            color: #FF9800;
        }
        .mass-edit-controls {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        .scripts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .script-card {
            background: #2d2d2d;
            border: 1px solid #444;
            border-radius: 5px;
            padding: 15px;
            position: relative;
        }
        .script-card.selected {
            border: 2px solid #FF9800;
            background: #3d3d2d;
        }
        .script-card h3 {
            margin: 0 0 10px 0;
            color: #4CAF50;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .select-checkbox {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .script-url {
            background: #1a1a1a;
            padding: 8px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 12px;
            margin: 10px 0;
            word-break: break-all;
        }
        .loadstring-box {
            background: #1a1a1a;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            border: 2px solid #2196F3;
        }
        .loadstring-box textarea {
            background: #0a0a0a;
            color: #4CAF50;
            font-family: 'Courier New', monospace;
            cursor: text;
        }
        .loadstring-box textarea:focus {
            outline: none;
            border-color: #4CAF50;
        }
        textarea {
            width: 100%;
            height: 200px;
            background: #1a1a1a;
            color: #fff;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            resize: vertical;
        }
        .btn {
            padding: 8px 15px;
            margin: 5px 5px 0 0;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
        .btn-save {
            background: #4CAF50;
            color: #000;
        }
        .btn-copy {
            background: #2196F3;
            color: #fff;
        }
        .btn-new {
            background: #FF9800;
            color: #000;
            padding: 10px 20px;
            font-size: 14px;
        }
        .btn-mass-save {
            background: #4CAF50;
            color: #000;
            padding: 10px 20px;
            font-size: 14px;
        }
        .btn-delete {
            background: #f44336;
            color: #fff;
        }
        .actions {
            margin: 20px 0;
        }
        input[type="text"] {
            padding: 8px;
            background: #2d2d2d;
            border: 1px solid #444;
            color: #fff;
            border-radius: 3px;
            margin-right: 10px;
        }
        .success { color: #4CAF50; margin-top: 5px; font-size: 12px; }
        .error { color: #f44336; margin-top: 5px; font-size: 12px; }
        .mass-editor {
            display: none;
            background: #2d2d2d;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            border: 2px solid #FF9800;
        }
        .mass-editor.active {
            display: block;
        }
        .mass-editor h3 {
            color: #FF9800;
            margin-top: 0;
        }
        .mass-editor textarea {
            height: 400px;
        }
        .selected-count {
            color: #FF9800;
            font-weight: bold;
        }
        .mass-create-panel {
            display: none;
            background: #2d2d2d;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            border: 2px solid #2196F3;
        }
        .mass-create-panel.active {
            display: block;
        }
        .mass-create-panel h3 {
            color: #2196F3;
            margin-top: 0;
        }
        .mass-create-panel label {
            display: block;
            margin-bottom: 5px;
            color: #aaa;
            font-size: 12px;
        }
        .analytics-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            overflow-y: auto;
        }
        .analytics-modal.active {
            display: block;
        }
        .analytics-content {
            background: #1e1e1e;
            max-width: 1200px;
            margin: 50px auto;
            padding: 30px;
            border-radius: 10px;
            border: 2px solid #4CAF50;
        }
        .analytics-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        .analytics-header h2 {
            color: #4CAF50;
            margin: 0;
        }
        .close-analytics {
            background: #f44336;
            color: #fff;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
        }
        .analytics-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: #2d2d2d;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 2px solid #444;
        }
        .stat-value {
            font-size: 36px;
            font-weight: bold;
            color: #4CAF50;
        }
        .stat-label {
            color: #aaa;
            margin-top: 10px;
        }
        .analytics-table {
            width: 100%;
            margin: 20px 0;
            background: #2d2d2d;
            border-radius: 8px;
            overflow: hidden;
        }
        .analytics-table th {
            background: #3d3d3d;
            padding: 15px;
            text-align: left;
            color: #4CAF50;
        }
        .analytics-table td {
            padding: 12px 15px;
            border-top: 1px solid #444;
        }
        .analytics-section {
            margin: 30px 0;
        }
        .analytics-section h3 {
            color: #4CAF50;
            margin-bottom: 15px;
        }
        .script-stat-badge {
            display: inline-block;
            background: #3d3d3d;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-left: 5px;
            color: #4CAF50;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Roblox Script Server Manager</h1>
            <div>
                <button class="btn btn-new" onclick="showAnalytics()" style="margin-right: 10px;">📊 Analytics</button>
                <a href="/logout" class="logout-btn">Logout</a>
            </div>
        </div>
        
        <div class="actions">
            <input type="text" id="newFolderName" placeholder="New folder name...">
            <button class="btn btn-new" onclick="createFolder()">Create Folder</button>
            
            <input type="text" id="newScriptName" placeholder="New script name (e.g., loader.lua)">
            <button class="btn btn-new" onclick="createScript()">Create Script</button>
            
            <button class="btn btn-new" onclick="toggleMassCreate()">📦 Mass Create Scripts</button>
        </div>

        <div class="mass-create-panel" id="massCreatePanel">
            <h3>📦 Mass Create Scripts</h3>
            <p>Create multiple scripts at once with sequential numbering</p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                <div>
                    <label>Prefix:</label>
                    <input type="text" id="massPrefix" placeholder="e.g., VPS" style="width: 100%;">
                </div>
                <div>
                    <label>Extension:</label>
                    <select id="massExtension" style="width: 100%; padding: 8px; background: #2d2d2d; border: 1px solid #444; color: #fff; border-radius: 3px;">
                        <option>.lua</option>
                        <option>.txt</option>
                    </select>
                </div>
                <div>
                    <label>Start Number:</label>
                    <input type="number" id="massStart" placeholder="e.g., 1" value="1" style="width: 100%;">
                </div>
                <div>
                    <label>End Number:</label>
                    <input type="number" id="massEnd" placeholder="e.g., 10" value="10" style="width: 100%;">
                </div>
            </div>
            <div style="margin: 10px 0;">
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                    <input type="checkbox" id="massZeroPad" checked style="width: 18px; height: 18px;">
                    <span>Add zero-padding (VPS01, VPS02... instead of VPS1, VPS2...)</span>
                </label>
            </div>
            <div style="background: #1a1a1a; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>Preview:</strong> <span id="massPreview">VPS1.lua, VPS2.lua, VPS3.lua...</span>
            </div>
            <button class="btn btn-mass-save" onclick="executeMassCreate()">Create Scripts</button>
            <button class="btn btn-new" onclick="toggleMassCreate()">Cancel</button>
            <div id="massCreateStatus"></div>
        </div>

        <div class="mass-edit-bar">
            <h3>📝 Mass Edit</h3>
            <div class="mass-edit-controls">
                <button class="btn btn-new" onclick="selectAll()">Select All</button>
                <button class="btn btn-new" onclick="deselectAll()">Deselect All</button>
                <button class="btn btn-mass-save" onclick="toggleMassEditor()">Edit Selected (<span id="selectedCount">0</span>)</button>
                <button class="btn btn-delete" onclick="deleteSelected()">Delete Selected</button>
            </div>
        </div>

        <div class="mass-editor" id="massEditor">
            <h3>Mass Editing <span class="selected-count" id="editingCount">0</span> Scripts</h3>
            <p>This content will be saved to all selected scripts:</p>
            <textarea id="massEditContent"></textarea>
            <button class="btn btn-mass-save" onclick="saveMassEdit()">Save to All Selected</button>
            <button class="btn btn-new" onclick="toggleMassEditor()">Cancel</button>
            <div id="massEditStatus"></div>
        </div>

        <h2>Folders:</h2>
        <div class="folder-list" id="folderList"></div>

        <h2>Scripts:</h2>
        <div class="scripts-grid" id="scriptsGrid"></div>

        <!-- Analytics Modal -->
        <div class="analytics-modal" id="analyticsModal">
            <div class="analytics-content">
                <div class="analytics-header">
                    <h2>📊 Script Analytics</h2>
                    <button class="close-analytics" onclick="closeAnalytics()">Close</button>
                </div>

                <div class="analytics-stats" id="analyticsStats"></div>

                <div class="analytics-section">
                    <h3>🔥 Top 10 Most Loaded Scripts</h3>
                    <table class="analytics-table">
                        <thead>
                            <tr>
                                <th>Script</th>
                                <th>Total Loads</th>
                                <th>Unique IPs</th>
                            </tr>
                        </thead>
                        <tbody id="topScriptsTable"></tbody>
                    </table>
                </div>

                <div class="analytics-section">
                    <h3>📈 Recent Activity (Last 50)</h3>
                    <table class="analytics-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Script</th>
                                <th>IP Address</th>
                            </tr>
                        </thead>
                        <tbody id="recentActivityTable"></tbody>
                    </table>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <button class="btn btn-delete" onclick="resetAnalytics()">Reset All Analytics</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentFolder = '';
        let serverUrl = window.location.origin;
        let selectedScripts = new Set();

        async function loadFolders() {
            const response = await fetch('/api/folders');
            const folders = await response.json();
            const folderList = document.getElementById('folderList');
            
            folderList.innerHTML = folders.map(folder => 
                `<button class="folder-btn" onclick="loadScripts('${folder}')">${folder}</button>`
            ).join('');
            
            if (folders.length > 0 && !currentFolder) {
                loadScripts(folders[0]);
            }
        }

        async function loadScripts(folder) {
            currentFolder = folder;
            selectedScripts.clear();
            updateSelectedCount();
            
            document.querySelectorAll('.folder-btn').forEach(btn => {
                btn.classList.toggle('active', btn.textContent === folder);
            });

            const response = await fetch(`/api/scripts/${folder}`);
            const scripts = await response.json();
            
            // Get analytics for all scripts
            const analyticsPromises = scripts.map(script => 
                fetch(`/api/analytics/script/${folder}/${script.name}`).then(r => r.json())
            );
            const analyticsData = await Promise.all(analyticsPromises);
            
            const grid = document.getElementById('scriptsGrid');
            
            grid.innerHTML = scripts.map((script, index) => {
                const analytics = analyticsData[index];
                const loadCount = analytics.total_loads || 0;
                const uniqueIPs = analytics.unique_ips || 0;
                const lastIP = analytics.last_ip || 'No loads yet';
                
                const scriptUrl = `${serverUrl}/scripts/${folder}/${script.name}`;
                const loadstringCode = `loadstring(game:HttpGet("${scriptUrl}"))()`;
                
                return `
                <div class="script-card" id="card-${script.name}" onclick="toggleSelect('${script.name}', event)">
                    <h3>
                        <input type="checkbox" class="select-checkbox" id="check-${script.name}" onclick="toggleSelect('${script.name}', event)">
                        ${script.name}
                        <span class="script-stat-badge" title="Total loads">📊 ${loadCount}</span>
                        ${uniqueIPs > 0 ? `<span class="script-stat-badge" title="Unique IPs">👥 ${uniqueIPs}</span>` : ''}
                    </h3>
                    ${lastIP !== 'No loads yet' ? `<div style="font-size: 11px; color: #aaa; margin: 5px 0;">🌐 Last IP: ${lastIP}</div>` : ''}
                    <div class="loadstring-box" onclick="event.stopPropagation()">
                        <div style="font-size: 11px; color: #aaa; margin-bottom: 5px;">Loadstring Code:</div>
                        <textarea readonly onclick="this.select()" style="height: 60px; font-size: 11px; cursor: text;">${loadstringCode}</textarea>
                        <button class="btn btn-copy" onclick="copyLoadstring('${loadstringCode}', event)" style="margin-top: 5px;">📋 Copy Loadstring</button>
                    </div>
                    <div class="script-url">${scriptUrl}</div>
                    <textarea id="editor-${script.name}">${script.content}</textarea>
                    <button class="btn btn-save" onclick="saveScript('${script.name}', event)">Save</button>
                    <button class="btn btn-copy" onclick="copyUrl('${folder}', '${script.name}', event)">Copy URL</button>
                    <button class="btn btn-new" onclick="showScriptAnalytics('${folder}', '${script.name}', event)">📊 Stats</button>
                    <button class="btn btn-delete" onclick="deleteScript('${script.name}', event)">Delete</button>
                    <div id="status-${script.name}"></div>
                </div>
            `}).join('');
        }

        function toggleSelect(scriptName, event) {
            event.stopPropagation();
            
            const card = document.getElementById(`card-${scriptName}`);
            const checkbox = document.getElementById(`check-${scriptName}`);
            
            if (selectedScripts.has(scriptName)) {
                selectedScripts.delete(scriptName);
                card.classList.remove('selected');
                checkbox.checked = false;
            } else {
                selectedScripts.add(scriptName);
                card.classList.add('selected');
                checkbox.checked = true;
            }
            
            updateSelectedCount();
        }

        function selectAll() {
            document.querySelectorAll('.script-card').forEach(card => {
                const scriptName = card.id.replace('card-', '');
                selectedScripts.add(scriptName);
                card.classList.add('selected');
                document.getElementById(`check-${scriptName}`).checked = true;
            });
            updateSelectedCount();
        }

        function deselectAll() {
            selectedScripts.clear();
            document.querySelectorAll('.script-card').forEach(card => {
                card.classList.remove('selected');
                const scriptName = card.id.replace('card-', '');
                document.getElementById(`check-${scriptName}`).checked = false;
            });
            updateSelectedCount();
        }

        function updateSelectedCount() {
            document.getElementById('selectedCount').textContent = selectedScripts.size;
            document.getElementById('editingCount').textContent = selectedScripts.size;
        }

        function toggleMassEditor() {
            const editor = document.getElementById('massEditor');
            editor.classList.toggle('active');
            
            if (editor.classList.contains('active') && selectedScripts.size > 0) {
                // Load content from first selected script
                const firstScript = Array.from(selectedScripts)[0];
                const content = document.getElementById(`editor-${firstScript}`).value;
                document.getElementById('massEditContent').value = content;
            }
        }

        async function saveMassEdit() {
            if (selectedScripts.size === 0) return;
            
            const content = document.getElementById('massEditContent').value;
            const status = document.getElementById('massEditStatus');
            status.innerHTML = '<span style="color: #FF9800;">Saving...</span>';
            
            let saved = 0;
            for (const scriptName of selectedScripts) {
                const response = await fetch(`/api/save/${currentFolder}/${scriptName}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content})
                });
                
                if (response.ok) {
                    document.getElementById(`editor-${scriptName}`).value = content;
                    saved++;
                }
            }
            
            status.innerHTML = `<span class="success">✓ Saved ${saved}/${selectedScripts.size} scripts!</span>`;
            setTimeout(() => {
                status.innerHTML = '';
                toggleMassEditor();
            }, 2000);
        }

        async function deleteSelected() {
            if (selectedScripts.size === 0) return;
            if (!confirm(`Delete ${selectedScripts.size} selected scripts?`)) return;
            
            for (const scriptName of selectedScripts) {
                await fetch(`/api/delete/${currentFolder}/${scriptName}`, {method: 'DELETE'});
            }
            
            selectedScripts.clear();
            loadScripts(currentFolder);
        }

        async function saveScript(scriptName, event) {
            event.stopPropagation();
            const content = document.getElementById(`editor-${scriptName}`).value;
            const response = await fetch(`/api/save/${currentFolder}/${scriptName}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content})
            });
            
            const status = document.getElementById(`status-${scriptName}`);
            if (response.ok) {
                status.innerHTML = '<span class="success">✓ Saved!</span>';
                setTimeout(() => status.innerHTML = '', 2000);
            } else {
                status.innerHTML = '<span class="error">✗ Error saving</span>';
            }
        }

        async function deleteScript(scriptName, event) {
            event.stopPropagation();
            if (!confirm(`Delete ${scriptName}?`)) return;
            
            const response = await fetch(`/api/delete/${currentFolder}/${scriptName}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                loadScripts(currentFolder);
            }
        }

        function copyUrl(folder, script, event) {
            event.stopPropagation();
            const url = `${serverUrl}/scripts/${folder}/${script}`;
            navigator.clipboard.writeText(url);
            alert('URL copied to clipboard!');
        }

        function copyLoadstring(code, event) {
            event.stopPropagation();
            navigator.clipboard.writeText(code);
            alert('Loadstring copied to clipboard!');
        }

        async function createFolder() {
            const name = document.getElementById('newFolderName').value.trim();
            if (!name) return alert('Enter folder name');
            
            const response = await fetch('/api/create-folder', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            });
            
            if (response.ok) {
                document.getElementById('newFolderName').value = '';
                loadFolders();
            }
        }

        async function createScript() {
            if (!currentFolder) return alert('Select a folder first');
            const name = document.getElementById('newScriptName').value.trim();
            if (!name) return alert('Enter script name');
            if (!name.endsWith('.lua')) return alert('Script must end with .lua');
            
            const response = await fetch(`/api/create-script/${currentFolder}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            });
            
            if (response.ok) {
                document.getElementById('newScriptName').value = '';
                loadScripts(currentFolder);
            }
        }

        // Load folders on page load
        loadFolders();

        // Mass create functions
        function toggleMassCreate() {
            const panel = document.getElementById('massCreatePanel');
            panel.classList.toggle('active');
            if (panel.classList.contains('active')) {
                updateMassPreview();
            }
        }

        function updateMassPreview() {
            const prefix = document.getElementById('massPrefix').value || 'VPS';
            const start = parseInt(document.getElementById('massStart').value) || 1;
            const end = parseInt(document.getElementById('massEnd').value) || 10;
            const ext = document.getElementById('massExtension').value;
            const zeroPad = document.getElementById('massZeroPad').checked;
            
            if (end - start > 100) {
                document.getElementById('massPreview').textContent = 'Too many files! Max 100 at once.';
                return;
            }
            
            const padding = zeroPad ? String(end).length : 0;
            
            const examples = [];
            for (let i = start; i <= Math.min(start + 2, end); i++) {
                const num = zeroPad ? String(i).padStart(padding, '0') : String(i);
                examples.push(`${prefix}${num}${ext}`);
            }
            if (end > start + 2) {
                examples.push('...');
                const num = zeroPad ? String(end).padStart(padding, '0') : String(end);
                examples.push(`${prefix}${num}${ext}`);
            }
            
            document.getElementById('massPreview').textContent = examples.join(', ');
        }

        // Update preview when inputs change
        document.addEventListener('DOMContentLoaded', function() {
            ['massPrefix', 'massStart', 'massEnd', 'massExtension', 'massZeroPad'].forEach(id => {
                const elem = document.getElementById(id);
                if (elem) {
                    elem.addEventListener('input', updateMassPreview);
                    elem.addEventListener('change', updateMassPreview);
                }
            });
        });

        async function executeMassCreate() {
            if (!currentFolder) return alert('Select a folder first');
            
            const prefix = document.getElementById('massPrefix').value.trim();
            const start = parseInt(document.getElementById('massStart').value);
            const end = parseInt(document.getElementById('massEnd').value);
            const ext = document.getElementById('massExtension').value;
            const zeroPad = document.getElementById('massZeroPad').checked;
            
            if (!prefix) return alert('Enter a prefix');
            if (isNaN(start) || isNaN(end)) return alert('Enter valid numbers');
            if (end < start) return alert('End number must be >= start number');
            if (end - start > 100) return alert('Too many files! Max 100 at once');
            
            const status = document.getElementById('massCreateStatus');
            status.innerHTML = '<span style="color: #FF9800;">Creating scripts...</span>';
            
            const response = await fetch(`/api/mass-create/${currentFolder}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    prefix: prefix,
                    start: start,
                    end: end,
                    extension: ext,
                    zero_pad: zeroPad
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                status.innerHTML = `<span class="success">✓ Created ${result.created} scripts!</span>`;
                setTimeout(() => {
                    toggleMassCreate();
                    loadScripts(currentFolder);
                    status.innerHTML = '';
                }, 1500);
            } else {
                status.innerHTML = `<span class="error">✗ Error: ${result.error || 'Failed'}</span>`;
            }
        }

        // Analytics functions
        async function showAnalytics() {
            document.getElementById('analyticsModal').classList.add('active');
            await loadAnalytics();
        }

        function closeAnalytics() {
            document.getElementById('analyticsModal').classList.remove('active');
        }

        async function loadAnalytics() {
            const response = await fetch('/api/analytics/overview');
            const data = await response.json();
            
            // Update stats cards
            document.getElementById('analyticsStats').innerHTML = `
                <div class="stat-card">
                    <div class="stat-value">${data.total_loads.toLocaleString()}</div>
                    <div class="stat-label">Total Script Loads</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.total_scripts}</div>
                    <div class="stat-label">Scripts Tracked</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.top_scripts.length > 0 ? data.top_scripts[0].loads : 0}</div>
                    <div class="stat-label">Most Popular Script</div>
                </div>
            `;
            
            // Update top scripts table
            document.getElementById('topScriptsTable').innerHTML = data.top_scripts.map(s => `
                <tr>
                    <td><strong>${s.script}</strong></td>
                    <td>${s.loads.toLocaleString()}</td>
                    <td>${s.unique_ips}</td>
                </tr>
            `).join('') || '<tr><td colspan="3" style="text-align: center; color: #aaa;">No data yet</td></tr>';
            
            // Update recent activity table
            document.getElementById('recentActivityTable').innerHTML = data.recent_activity.map(a => {
                const date = new Date(a.timestamp);
                const timeStr = date.toLocaleTimeString() + ' - ' + date.toLocaleDateString();
                return `
                    <tr>
                        <td>${timeStr}</td>
                        <td>${a.script}</td>
                        <td>${a.ip || 'N/A'}</td>
                    </tr>
                `;
            }).join('') || '<tr><td colspan="3" style="text-align: center; color: #aaa;">No activity yet</td></tr>';
        }

        async function resetAnalytics() {
            if (!confirm('Are you sure you want to reset ALL analytics data? This cannot be undone!')) return;
            
            const response = await fetch('/api/analytics/reset', { method: 'POST' });
            if (response.ok) {
                alert('Analytics reset successfully!');
                loadAnalytics();
            }
        }

        async function showScriptAnalytics(folder, script, event) {
            if (event) event.stopPropagation();
            
            const response = await fetch(`/api/analytics/script/${folder}/${script}`);
            const data = await response.json();
            
            const firstLoad = data.first_load ? new Date(data.first_load).toLocaleString() : 'Never';
            const lastLoad = data.last_load ? new Date(data.last_load).toLocaleString() : 'Never';
            
            alert(`📊 Analytics for ${script}\n\n` +
                  `Total Loads: ${data.total_loads}\n` +
                  `Unique IPs: ${data.unique_ips}\n` +
                  `First Load: ${firstLoad}\n` +
                  `Last Load: ${lastLoad}`);
        }
    </script>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == CONFIG['username'] and password == CONFIG['password']:
            session['logged_in'] = True
            return redirect(url_for('editor'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Invalid credentials")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Logout"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def editor():
    """Web-based editor interface"""
    return render_template_string(EDITOR_TEMPLATE)

@app.route('/scripts/<folder>/<filename>')
def serve_script(folder, filename):
    """Serve Lua scripts for loadstring"""
    if not filename.endswith('.lua'):
        abort(403)
    
    filepath = os.path.join(BASE_DIR, folder, filename)
    if os.path.exists(filepath):
        # Track analytics (get IP from request)
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        track_script_load(folder, filename, ip_address)
        
        return send_file(filepath, mimetype='text/plain')
    abort(404)

@app.route('/api/folders')
@login_required
def get_folders():
    """Get list of all folders"""
    folders = [f for f in os.listdir(BASE_DIR) 
               if os.path.isdir(os.path.join(BASE_DIR, f))]
    folders.sort(key=natural_sort_key)
    return jsonify(folders)

@app.route('/api/scripts/<folder>')
@login_required
def get_scripts(folder):
    """Get all scripts in a folder"""
    folder_path = os.path.join(BASE_DIR, folder)
    if not os.path.exists(folder_path):
        return jsonify([])
    
    # Get all lua files and sort them naturally
    filenames = [f for f in os.listdir(folder_path) if f.endswith('.lua')]
    filenames.sort(key=natural_sort_key)
    
    scripts = []
    for filename in filenames:
        filepath = os.path.join(folder_path, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            scripts.append({
                'name': filename,
                'content': f.read()
            })
    return jsonify(scripts)

@app.route('/api/save/<folder>/<filename>', methods=['POST'])
@login_required
def save_script(folder, filename):
    """Save a script"""
    if not filename.endswith('.lua'):
        abort(403)
    
    content = request.json.get('content', '')
    folder_path = os.path.join(BASE_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)
    
    filepath = os.path.join(folder_path, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return jsonify({'success': True})

@app.route('/api/delete/<folder>/<filename>', methods=['DELETE'])
@login_required
def delete_script(folder, filename):
    """Delete a script"""
    if not filename.endswith('.lua'):
        abort(403)
    
    filepath = os.path.join(BASE_DIR, folder, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True})
    abort(404)

@app.route('/api/create-folder', methods=['POST'])
@login_required
def create_folder():
    """Create a new folder"""
    name = request.json.get('name', '').strip()
    if not name:
        abort(400)
    
    folder_path = os.path.join(BASE_DIR, name)
    os.makedirs(folder_path, exist_ok=True)
    return jsonify({'success': True})

@app.route('/api/create-script/<folder>', methods=['POST'])
@login_required
def create_script(folder):
    """Create a new script"""
    name = request.json.get('name', '').strip()
    if not name or not name.endswith('.lua'):
        abort(400)
    
    folder_path = os.path.join(BASE_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)
    
    filepath = os.path.join(folder_path, name)
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('-- New script\nprint("Hello from script server!")\n')
    
    return jsonify({'success': True})

@app.route('/api/mass-create/<folder>', methods=['POST'])
@login_required
def mass_create_scripts(folder):
    """Mass create multiple scripts with numbering"""
    try:
        data = request.json
        prefix = data.get('prefix', '').strip()
        start = int(data.get('start', 1))
        end = int(data.get('end', 10))
        extension = data.get('extension', '.lua')
        zero_pad = data.get('zero_pad', True)
        
        if not prefix:
            return jsonify({'error': 'Prefix required'}), 400
        if end < start:
            return jsonify({'error': 'End must be >= start'}), 400
        if end - start > 100:
            return jsonify({'error': 'Max 100 scripts at once'}), 400
        
        folder_path = os.path.join(BASE_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # Calculate padding length
        padding = len(str(end)) if zero_pad else 0
        
        created = 0
        for i in range(start, end + 1):
            # Format number with zero-padding if enabled
            num_str = str(i).zfill(padding) if zero_pad else str(i)
            filename = f"{prefix}{num_str}{extension}"
            filepath = os.path.join(folder_path, filename)
            
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f'-- {filename}\n-- Created by mass create\nprint("Script {i}")\n')
                created += 1
        
        return jsonify({'success': True, 'created': created})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/overview')
@login_required
def analytics_overview():
    """Get overall analytics"""
    analytics = load_analytics()
    
    # Calculate some stats
    total_scripts = len(analytics["scripts"])
    total_loads = analytics["total_loads"]
    
    # Get top 10 most loaded scripts
    top_scripts = sorted(
        analytics["scripts"].items(),
        key=lambda x: x[1]["total_loads"],
        reverse=True
    )[:10]
    
    # Recent activity (last 50)
    recent = analytics["history"][-50:]
    recent.reverse()
    
    return jsonify({
        "total_scripts": total_scripts,
        "total_loads": total_loads,
        "top_scripts": [{"script": k, "loads": v["total_loads"], "unique_ips": len(v.get("unique_ips", []))} for k, v in top_scripts],
        "recent_activity": recent
    })

@app.route('/api/analytics/script/<folder>/<filename>')
@login_required
def analytics_script(folder, filename):
    """Get analytics for specific script"""
    analytics = load_analytics()
    script_key = f"{folder}/{filename}"
    
    if script_key in analytics["scripts"]:
        data = analytics["scripts"][script_key]
        
        # Get recent loads for this script
        recent = [h for h in analytics["history"] if h["script"] == script_key][-20:]
        recent.reverse()
        
        # Get last IP from recent history
        last_ip = recent[0]["ip"] if recent and recent[0].get("ip") else None
        
        return jsonify({
            "script": script_key,
            "total_loads": data["total_loads"],
            "unique_ips": len(data.get("unique_ips", [])),
            "first_load": data.get("first_load"),
            "last_load": data.get("last_load"),
            "last_ip": last_ip,
            "recent_loads": recent
        })
    
    return jsonify({
        "script": script_key,
        "total_loads": 0,
        "unique_ips": 0,
        "last_ip": None,
        "recent_loads": []
    })

@app.route('/api/analytics/reset', methods=['POST'])
@login_required
def analytics_reset():
    """Reset all analytics"""
    save_analytics({"total_loads": 0, "scripts": {}, "history": []})
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Use PORT from environment or 5000
    print("=" * 60)
    print("🚀 ROBLOX SCRIPT SERVER STARTED!")
    print("=" * 60)
    print(f"📁 Scripts directory: {os.path.abspath(BASE_DIR)}")
    print(f"🌐 Web Editor: http://localhost:{port}")
    print(f"🔒 Login required!")
    print(f"   Username: {CONFIG['username']}")
    print(f"   Password: {CONFIG['password']}")
    print(f"   ⚠️  Change password in: {CONFIG_FILE}")
    print(f"📝 Script URL format: http://localhost:{port}/scripts/FOLDER/SCRIPT.lua")
    print("   (Scripts are accessible without login)")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
