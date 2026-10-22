#!/bin/bash
set -e

echo "🔍 1. Starte Pytest-Testsuite..."
uv run pytest

echo "📝 2. Aktualisiere Git-Staging..."
git add .

if git diff-index --quiet HEAD --; then
    echo "✨ Keine Änderungen zum Committen vorhanden."
else
    echo "💬 3. Welchen Commit-Titel möchtest du vergeben?"
    read -p "Commit-Nachricht: " commit_msg

    if [ -z "$commit_msg" ]; then
        commit_msg="wip: automatisierter Sync vom Mac mini"
    fi

    git commit -m "$commit_msg"
fi

echo "🚀 4. Lade Änderungen auf GitHub hoch (Push)..."
git push origin main

echo "✨ Fertig! Alles sicher auf GitHub gespeichert."
