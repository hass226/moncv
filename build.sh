#!/usr/bin/env bash
# build.sh - Script pour construire l'application
set -e  # Arrêter le script en cas d'erreur

echo "=== Mise à jour de pip ==="
python -m pip install --upgrade pip

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
