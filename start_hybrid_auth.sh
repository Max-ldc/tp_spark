#!/bin/bash
# Script de démarrage complet du système d'authentification hybride

echo "🔐 CESI Temperature API - Authentification Hybride"
echo "=================================================="
echo ""

# Vérifier si les certificats existent
if [ ! -d "certs/ca" ]; then
    echo "📋 Génération des certificats..."
    python src/jobs/generate_certificates.py
    if [ $? -ne 0 ]; then
        echo "❌ Erreur lors de la génération des certificats"
        exit 1
    fi
fi

echo ""
echo "✅ Certificats vérifiés"
echo "   └─ certs/ contient CA, serveur, et clients"

echo ""
echo "🚀 Démarrage de l'API..."
python src/api/main.py
