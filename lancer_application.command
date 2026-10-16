#!/bin/bash
# Double-cliquez sur ce fichier pour lancer l'application Rush 4 dans votre navigateur.
# Pour l'arrêter : fermez la fenêtre du Terminal (ou appuyez sur Ctrl+C).

cd "$(dirname "$0")" || exit 1

if ! python3 -c "import streamlit, pandas, numpy" >/dev/null 2>&1; then
    echo "Installation des bibliothèques nécessaires (une seule fois)…"
    if ! python3 -m pip install --user streamlit pandas numpy; then
        echo "L'installation a échoué."
        read -r -p "Appuyez sur Entrée pour fermer."
        exit 1
    fi
fi

# Premier port libre à partir de 8501
PORT=8501
while lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do
    PORT=$((PORT + 1))
done

echo "Lancement de l'application…"
# --server.address localhost : l'application n'est visible que sur cet ordinateur, pas sur le réseau
python3 -m streamlit run notebook_Instagram_perso.py --server.headless true --server.address localhost --server.port "$PORT" \
    --browser.gatherUsageStats false &
SERVEUR=$!
trap 'kill "$SERVEUR" 2>/dev/null' EXIT

for _ in $(seq 1 60); do
    curl -s "http://localhost:$PORT/_stcore/health" | grep -q ok && break
    sleep 1
done

open "http://localhost:$PORT"
echo ""
echo "Application ouverte sur http://localhost:$PORT"
echo "Fermez cette fenêtre (ou Ctrl+C) pour l'arrêter."
wait "$SERVEUR"
