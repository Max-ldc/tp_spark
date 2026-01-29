#!/usr/bin/env python3
"""
Utilitaire CLI pour tester l'authentification hybride.
Usage: python auth_cli.py [command] [options]
"""
import sys
import subprocess
import json
from pathlib import Path

def run_command(cmd, description=""):
    """Exécute une commande et affiche le résultat."""
    if description:
        print(f"\n📋 {description}")
        print("-" * 70)
    
    print(f"$ {cmd}\n")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            try:
                data = json.loads(result.stdout)
                print(json.dumps(data, indent=2))
            except:
                print(result.stdout)
        
        if result.stderr and result.returncode != 0:
            print(f"❌ Erreur: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def main():
    """CLI principal."""
    if len(sys.argv) < 2:
        print("""
🔐 CLI d'Authentification Hybride - CESI Temperature API
=========================================================

Commandes disponibles:

  generate            Générer les certificats
  test                Lancer la suite de tests
  server              Démarrer l'API
  token               Générer un JWT
  health              Vérifier la santé de l'API
  help                Afficher cette aide

Exemples:
  python auth_cli.py generate
  python auth_cli.py test
  python auth_cli.py server
  python auth_cli.py token --key admin-key-004
  python auth_cli.py health --key admin-key-004
""")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "generate":
        print("🔐 Génération des certificats...")
        run_command("python src/jobs/generate_certificates.py")
    
    elif cmd == "test":
        print("🧪 Lancement des tests d'authentification...")
        run_command("python src/jobs/test_hybrid_auth.py")
    
    elif cmd == "server":
        print("🚀 Démarrage de l'API...")
        run_command("python src/api/main.py")
    
    elif cmd == "token":
        api_key = "admin-key-004"  # Default
        
        # Chercher --key option
        for i, arg in enumerate(sys.argv):
            if arg == "--key" and i + 1 < len(sys.argv):
                api_key = sys.argv[i + 1]
        
        run_command(
            f'curl -s -X POST "http://localhost:8000/auth/token?api_key={api_key}" | python -m json.tool',
            f"Génération de JWT avec la clé: {api_key}"
        )
    
    elif cmd == "health":
        api_key = "admin-key-004"  # Default
        
        for i, arg in enumerate(sys.argv):
            if arg == "--key" and i + 1 < len(sys.argv):
                api_key = sys.argv[i + 1]
        
        run_command(
            f'curl -s -H "X-API-Key: {api_key}" http://localhost:8000/health | python -m json.tool',
            "Vérification de la santé de l'API"
        )
    
    elif cmd == "help":
        main()  # Réafficher l'aide
    
    else:
        print(f"❌ Commande inconnue: {cmd}")
        print("\nPour voir l'aide: python auth_cli.py help")


if __name__ == "__main__":
    main()
