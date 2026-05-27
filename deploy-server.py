#!/usr/bin/env python3
"""
Expirenza Deploy Server
Запусти один раз: python3 deploy-server.py
Потом Claude сам будет деплоить через браузер.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import os
import json
from datetime import datetime

REPO_PATH = "/Users/pavel/Documents/Claude/Projects/Expz - rest navigate"
PORT = 7777

class DeployHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/deploy" or self.path.startswith("/deploy?"):
            self.handle_deploy()
        elif self.path == "/status":
            self.handle_status()
        elif self.path == "/":
            self.handle_index()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "http://localhost:7777")
        self.end_headers()

    def handle_deploy(self):
        # Получаем сообщение коммита из параметра ?msg=...
        msg = "deploy"
        if "?" in self.path:
            params = self.path.split("?", 1)[1]
            for p in params.split("&"):
                if p.startswith("msg="):
                    msg = p[4:].replace("+", " ").replace("%20", " ")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"{msg} ({timestamp})"

        try:
            # git add .
            r1 = subprocess.run(
                ["git", "add", "."],
                cwd=REPO_PATH, capture_output=True, text=True
            )

            # git status --short — проверяем есть ли что коммитить
            status = subprocess.run(
                ["git", "status", "--short"],
                cwd=REPO_PATH, capture_output=True, text=True
            )

            if not status.stdout.strip():
                result = {"status": "ok", "message": "Нет изменений для деплоя"}
                self.send_json(200, result)
                print(f"[{timestamp}] Нет изменений")
                return

            # git commit
            r2 = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=REPO_PATH, capture_output=True, text=True
            )

            # git push
            r3 = subprocess.run(
                ["git", "push"],
                cwd=REPO_PATH, capture_output=True, text=True
            )

            if r3.returncode == 0:
                result = {
                    "status": "ok",
                    "message": f"✅ Задеплоено: {commit_msg}",
                    "output": r3.stdout
                }
                print(f"[{timestamp}] ✅ Деплой: {commit_msg}")
            else:
                result = {
                    "status": "error",
                    "message": "❌ Ошибка push",
                    "output": r3.stderr
                }
                print(f"[{timestamp}] ❌ Ошибка: {r3.stderr}")

        except Exception as e:
            result = {"status": "error", "message": str(e)}

        self.send_json(200, result)

    def handle_status(self):
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=REPO_PATH, capture_output=True, text=True
        )
        log = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd=REPO_PATH, capture_output=True, text=True
        )
        result = {
            "status": "ok",
            "changes": status.stdout.strip() or "Нет изменений",
            "last_commits": log.stdout.strip()
        }
        self.send_json(200, result)

    def handle_index(self):
        html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Expirenza Deploy</title>
<style>
  body { font-family: sans-serif; max-width: 500px; margin: 80px auto; text-align: center; }
  button { background: #6638DD; color: white; border: none; padding: 16px 40px;
           font-size: 18px; border-radius: 12px; cursor: pointer; margin: 10px; }
  button:hover { background: #5229c4; }
  #result { margin-top: 30px; padding: 16px; border-radius: 8px; font-size: 15px; }
  .ok { background: #e8f5e9; color: #2e7d32; }
  .error { background: #ffebee; color: #c62828; }
</style>
</head>
<body>
  <h2>🚀 Expirenza Deploy</h2>
  <button onclick="deploy()">Deploy</button>
  <button onclick="status()" style="background:#888">Status</button>
  <div id="result"></div>
<script>
  async function deploy() {
    document.getElementById('result').innerHTML = '⏳ Деплоим...';
    const r = await fetch('/deploy?msg=update').then(r => r.json());
    const el = document.getElementById('result');
    el.className = r.status === 'ok' ? 'ok' : 'error';
    el.innerHTML = r.message + (r.output ? '<br><small>' + r.output + '</small>' : '');
  }
  async function status() {
    const r = await fetch('/status').then(r => r.json());
    const el = document.getElementById('result');
    el.className = 'ok';
    el.innerHTML = '<b>Изменения:</b> ' + r.changes + '<br><b>Коммиты:</b><br>' + r.last_commits.replace(/\\n/g,'<br>');
  }
</script>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # отключаем стандартные логи

if __name__ == "__main__":
    print(f"🚀 Expirenza Deploy Server запущен на http://localhost:{PORT}")
    print(f"📁 Репо: {REPO_PATH}")
    print(f"   Открой http://localhost:{PORT} в браузере")
    print(f"   Или скажи Claude задеплоить — он сам вызовет /deploy")
    print(f"   Ctrl+C для остановки\n")
    server = HTTPServer(("localhost", PORT), DeployHandler)
    server.serve_forever()
