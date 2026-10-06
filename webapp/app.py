#!/usr/bin/env python3
"""
Simple web app that reads secrets from OpenBao at startup.
Proves zero hardcoded credentials.
"""
import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://openbao.openbao.svc.cluster.local:8200")
VAULT_ROLE = os.environ.get("VAULT_ROLE", "myapp-role")

def get_k8s_token():
    with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
        return f.read().strip()

def authenticate_openbao(jwt):
    url = f"{VAULT_ADDR}/v1/auth/kubernetes/login"
    data = json.dumps({"jwt": jwt, "role": VAULT_ROLE}).encode()
    req = urllib.request.Request(url, data=data,
          headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["auth"]["client_token"]

def fetch_secret(token, path):
    url = f"{VAULT_ADDR}/v1/{path}"
    req = urllib.request.Request(url, headers={"X-Vault-Token": token})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["data"]["data"]

# Fetch secrets at startup
print("Fetching secrets from OpenBao...")
try:
    jwt = get_k8s_token()
    token = authenticate_openbao(jwt)
    secrets = fetch_secret(token, "secret/data/myapp/config")
    print(f"Secrets loaded: db_host={secrets.get('db_host')}")
except Exception as e:
    secrets = {"error": str(e)}
    print(f"Failed to fetch secrets: {e}")

class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = f"""
<!DOCTYPE html>
<html>
<head>
  <title>MyApp — Secured by OpenBao</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #1a1a2e;
            color: #eee; display: flex; justify-content: center;
            align-items: center; height: 100vh; margin: 0; }}
    .card {{ background: #16213e; padding: 40px; border-radius: 12px;
             max-width: 600px; width: 100%; box-shadow: 0 4px 20px #0f3460; }}
    h1 {{ color: #00d4aa; }}
    .badge {{ background: #00d4aa; color: #000; padding: 4px 12px;
              border-radius: 20px; font-size: 0.8em; font-weight: bold; }}
    .row {{ margin: 15px 0; padding: 12px; background: #0f3460;
            border-radius: 8px; display: flex; justify-content: space-between; }}
    .label {{ color: #aaa; }}
    .value {{ color: #00d4aa; font-weight: bold; }}
    .hidden {{ color: #f39c12; }}
    .footer {{ margin-top: 20px; font-size: 0.8em; color: #666;
               text-align: center; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>🔐 MyApp Dashboard</h1>
    <p><span class="badge">LIVE</span> Secrets fetched from OpenBao at runtime</p>
    <hr style="border-color:#0f3460; margin: 20px 0;">

    <div class="row">
      <span class="label">Database Host</span>
      <span class="value">{secrets.get('db_host', 'N/A')}</span>
    </div>
    <div class="row">
      <span class="label">Database Port</span>
      <span class="value">{secrets.get('db_port', 'N/A')}</span>
    </div>
    <div class="row">
      <span class="label">Database Password</span>
      <span class="hidden">●●●●●●●●●● (fetched, safely hidden)</span>
    </div>
    <div class="row">
      <span class="label">API Key</span>
      <span class="hidden">●●●●●●●●●● (fetched, safely hidden)</span>
    </div>

    <div class="footer">
      ✅ Zero hardcoded secrets &nbsp;|&nbsp;
      🔒 Deployed by ArgoCD &nbsp;|&nbsp;
      🏛️ Secured by OpenBao v2.7.0
    </div>
  </div>
</body>
</html>"""
        self.wfile.write(html.encode())
    def log_message(self, *args):
        pass  # Suppress access logs

print("Starting web server on port 8080...")
HTTPServer(("0.0.0.0", 8080), AppHandler).serve_forever()
