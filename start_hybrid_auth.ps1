# Script de démarrage complet du système d'authentification hybride (PowerShell)

Write-Host "🔐 CESI Temperature API - Authentification Hybride" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si les certificats existent
if (-not (Test-Path "certs/ca")) {
    Write-Host "📋 Génération des certificats..." -ForegroundColor Yellow
    & python src/jobs/generate_certificates.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur lors de la génération des certificats" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "✅ Certificats vérifiés" -ForegroundColor Green
Write-Host "   └─ certs/ contient CA, serveur, et clients" -ForegroundColor Green

Write-Host ""
Write-Host "🚀 Démarrage de l'API..." -ForegroundColor Cyan
Write-Host "📝 Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

& python src/api/main.py
