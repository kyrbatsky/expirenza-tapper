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
import urllib.request
import urllib.parse
from datetime import datetime

BASE_PATH = "/Users/pavel/Documents/Claude/Projects/Expz - rest navigate"
PORT = 7777

def get_github_token():
    """Читает GitHub токен из .git/config"""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=BASE_PATH, capture_output=True, text=True
        )
        url = result.stdout.strip()
        # https://username:TOKEN@github.com/...
        if "@" in url and ":" in url.split("@")[0]:
            token = url.split("//")[1].split(":")[1].split("@")[0]
            return token
    except:
        pass
    return None

def fetch_github_repos(token):
    """Получает список репозиториев с GitHub API"""
    try:
        req = urllib.request.Request(
            "https://api.github.com/user/repos?per_page=50&sort=updated",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "expirenza-deploy-server"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            repos = json.loads(resp.read())
            return [{"name": r["name"], "full_name": r["full_name"], "url": r["html_url"]} for r in repos]
    except Exception as e:
        return None


class DeployHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/deploy":
            self.handle_deploy()
        elif path == "/repos":
            self.handle_repos()
        elif path == "/status":
            self.handle_status()
        elif path == "/":
            self.handle_index()
        else:
            self.send_response(404)
            self.end_headers()

    def parse_params(self):
        params = {}
        if "?" in self.path:
            query = self.path.split("?", 1)[1]
            for p in query.split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = urllib.parse.unquote_plus(v)
        return params

    def handle_repos(self):
        token = get_github_token()
        if not token:
            self.send_json(200, {"status": "error", "message": "Токен не найден в .git/config"})
            return

        repos = fetch_github_repos(token)
        if repos is None:
            self.send_json(200, {"status": "error", "message": "Не удалось получить список репозиториев"})
            return

        self.send_json(200, {"status": "ok", "repos": repos})

    def handle_deploy(self):
        params = self.parse_params()
        msg = params.get("msg", "update")
        repo_name = params.get("repo", "")  # например "expirenza-tapper"

        # Определяем путь к репозиторию
        repo_path = BASE_PATH

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"{msg} ({timestamp})"

        try:
            # Если указан другой репозиторий — обновляем remote
            if repo_name:
                token = get_github_token()
                # Читаем текущего пользователя из remote url
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=repo_path, capture_output=True, text=True
                )
                current_url = result.stdout.strip()
                username = current_url.split("github.com/")[1].split("/")[0] if "github.com/" in current_url else "kyrbatsky"

                new_url = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
                subprocess.run(["git", "remote", "set-url", "origin", new_url],
                                cwd=repo_path, capture_output=True)

            # git add .
            subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, text=True)

            # Проверяем есть ли изменения
            status = subprocess.run(
                ["git", "status", "--short"],
                cwd=repo_path, capture_output=True, text=True
            )

            if not status.stdout.strip():
                self.send_json(200, {"status": "ok", "message": "Нет изменений для деплоя"})
                print(f"[{timestamp}] Нет изменений")
                return

            # git commit
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=repo_path, capture_output=True, text=True
            )

            # git push
            r3 = subprocess.run(
                ["git", "push"],
                cwd=repo_path, capture_output=True, text=True
            )

            if r3.returncode == 0:
                result = {
                    "status": "ok",
                    "message": f"✅ Задеплоено: {commit_msg}",
                    "repo": repo_name or "текущий репо"
                }
                print(f"[{timestamp}] ✅ {commit_msg}")
            else:
                result = {
                    "status": "error",
                    "message": "❌ Ошибка push",
                    "output": r3.stderr
                }
                print(f"[{timestamp}] ❌ {r3.stderr}")

        except Exception as e:
            result = {"status": "error", "message": str(e)}

        self.send_json(200, result)

    def handle_status(self):
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=BASE_PATH, capture_output=True, text=True
        )
        log = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd=BASE_PATH, capture_output=True, text=True
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
  select { padding: 10px; font-size: 16px; border-radius: 8px; width: 100%; margin: 10px 0; }
  #result { margin-top: 30px; padding: 16px; border-radius: 8px; font-size: 15px; }
  .ok { background: #e8f5e9; color: #2e7d32; }
  .error { background: #ffebee; color: #c62828; }
</style>
</head>
<body>
  <h2>🚀 Expirenza Deploy</h2>
  <select id="repo"><option value="">⏳ Загружаю репозитории...</option></select>
  <button onclick="deploy()">Deploy</button>
  <button onclick="checkStatus()" style="background:#888">Status</button>
  <div id="result"></div>
<script>
  async function loadRepos() {
    const r = await fetch('/repos').then(r => r.json());
    const sel = document.getElementById('repo');
    if (r.status === 'ok') {
      sel.innerHTML = r.repos.map(repo =>
        `<option value="${repo.name}">${repo.name}</option>`
      ).join('');
    } else {
      sel.innerHTML = '<option>Ошибка загрузки репо</option>';
    }
  }
  async function deploy() {
    const repo = document.getElementById('repo').value;
    document.getElementById('result').innerHTML = '⏳ Деплоим...';
    const r = await fetch(`/deploy?msg=update&repo=${repo}`).then(r => r.json());
    const el = document.getElementById('result');
    el.className = r.status === 'ok' ? 'ok' : 'error';
    el.innerHTML = r.message;
  }
  async function checkStatus() {
    const r = await fetch('/status').then(r => r.json());
    const el = document.getElementById('result');
    el.className = 'ok';
    el.innerHTML = '<b>Изменения:</b> ' + r.changes + '<br><b>Коммиты:</b><br>' + r.last_commits.replace(/\\n/g,'<br>');
  }
  loadRepos();
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
        pass

if __name__ == "__main__":
    print(f"🚀 Expirenza Deploy Server запущен на http://localhost:{PORT}")
    print(f"📁 База: {BASE_PATH}")
    print(f"   http://localhost:{PORT} — веб-интерфейс")
    print(f"   http://localhost:{PORT}/repos — список репозиториев")
    print(f"   http://localhost:{PORT}/deploy?msg=update&repo=repo-name — деплой")
    print(f"   Ctrl+C для остановки\n")
    server = HTTPServer(("localhost", PORT), DeployHandler)
    server.serve_forever()
