#!/usr/bin/env bash
cd "$(dirname "$0")"
PORT="${1:-8080}"
echo "Mapa temporal en http://localhost:${PORT}"
echo "Ctrl+C para detener"
exec python3 -m http.server "$PORT"
