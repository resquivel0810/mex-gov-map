#!/usr/bin/env bash
# El mapa no funciona abriendo index.html con doble clic (file://).
# Los navegadores bloquean fetch() por seguridad; hace falta HTTP local.
cd "$(dirname "$0")"
PORT="${1:-8080}"
echo "Mapa en http://localhost:${PORT}"
echo "Ctrl+C para detener"
exec python3 -m http.server "$PORT"
