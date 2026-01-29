"""
Serveur HTTP simple pour le frontend.
Lance ce serveur pour éviter les problèmes CORS avec file://.

Usage:
    python serve_frontend.py

Le frontend sera disponible sur http://localhost:5500
"""

import http.server
import socketserver
import os

PORT = 5500
DIRECTORY = "frontend"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        # Ajouter les headers CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key')
        super().end_headers()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"🌐 Serveur frontend démarré sur http://localhost:{PORT}")
        print(f"📁 Répertoire: {os.path.abspath(DIRECTORY)}")
        print(f"\n✨ Ouvrez http://localhost:{PORT}/login.html dans votre navigateur")
        print(f"\nAppuyez sur Ctrl+C pour arrêter le serveur\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Serveur arrêté")
