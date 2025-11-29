#!/usr/bin/env bash
# build.sh - Script pour construire l'application
set -e  # Arrêter le script en cas d'erreur

echo "=== Installation des dépendances système ==="
# Installer les dépendances système nécessaires pour psycopg2
# Note: Ces commandes nécessitent les droits sudo, mais sont commentées car elles peuvent ne pas être nécessaires sur Render
# sudo apt-get update
# sudo apt-get install -y python3-dev libpq-dev

# Mettre à jour pip en premier, en ignorant les erreurs de version
echo "=== Mise à jour de pip ==="
python -m pip install --upgrade pip || echo "Échec de la mise à jour de pip, continuation avec la version actuelle"

echo "\n=== Installation des dépendances ==="
# Désactiver temporairement le vérificateur de hachage pour éviter les problèmes avec les dépendances existantes
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_PYTHON_VERSION_WARNING=1

# Installer les dépendances avec --no-cache-dir pour éviter les problèmes de cache
pip install --no-cache-dir -r requirements.txt

# Vérifier la version de pip installée
echo "\n=== Vérification des versions installées ==="
pip --version
python --version

# Vérifier les versions des paquets problématiques
echo "\n=== Versions des dépendances critiques ==="
pip show cryptography pyOpenSSL Django

echo "\n=== Collecte des fichiers statiques ==="
python manage.py collectstatic --noinput

echo "\n=== Application des migrations ==="
python manage.py migrate

echo "\n=== Construction terminée avec succès ==="
