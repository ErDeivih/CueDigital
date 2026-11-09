#!/usr/bin/env bash
# Copia de seguridad de CUE Digital: la base de datos y los ficheros del agricultor.
#
# POR QUÉ ASÍ
#
# · La base se saca con `pg_dump --format=custom`: un fichero comprimido que se
#   restaura con `pg_restore` y que se puede comprobar con `pg_restore --list` SIN
#   restaurarlo. Una copia que no se ha comprobado no se sabe si sirve.
# · Los adjuntos son ficheros en una carpeta del servidor, así que se copian con `tar`.
#   La caché del SIGPAC NO se copia: son gigas que se pueden volver a bajar del FEGA.
# · Si hay `rclone` y `COPIA_REMOTA`, la copia SALE de la máquina. Una copia que vive
#   en el mismo disco que los datos no protege de lo que más pasa: que el disco o el
#   servidor se rompa.
#
# CÓMO SE USA
#
#     ./deploy/copia.sh
#
# y en el cron del servidor, una vez al día de madrugada:
#
#     15 3 * * * /srv/cuedigital/CueDigital/deploy/copia.sh >> /var/log/cuedigital-copia.log 2>&1
#
# NO SE HA PODIDO PROBAR EN ESTA MÁQUINA (no hay servidor). Revísalo antes de confiar.
#
# Lo que lee: `deploy/.env` (con `source`, así que sin espacios raros en los valores).

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENTORNO="$RAIZ/deploy/.env"

if [ ! -f "$ENTORNO" ]; then
    echo "FALLO: no existe $ENTORNO. Sin la configuración no se puede copiar nada." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENTORNO"
set +a

: "${CARPETA_DATOS:?falta CARPETA_DATOS}"
: "${POSTGRES_USER:?falta POSTGRES_USER}"
: "${POSTGRES_DB:?falta POSTGRES_DB}"

DESTINO="${DESTINO_COPIAS:-/srv/cuedigital/copias}"
DIAS="${DIAS_DE_COPIAS:-14}"
MARCA="$(date +%Y%m%d-%H%M%S)"
CARPETA="$DESTINO/$MARCA"
COMPOSE=(docker compose -f "$RAIZ/deploy/docker-compose.yml")

mkdir -p "$CARPETA"

echo "[1/3] Base de datos → $CARPETA/base.dump"
"${COMPOSE[@]}" exec -T db \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > "$CARPETA/base.dump"

# Que el volcado se pueda LEER, no solo que exista.
if ! "${COMPOSE[@]}" exec -T db pg_restore --list < "$CARPETA/base.dump" > /dev/null; then
    echo "FALLO: el volcado de la base no se puede leer. No se borra ninguna copia." >&2
    exit 1
fi

echo "[2/3] Adjuntos → $CARPETA/adjuntos.tar.gz"
tar -czf "$CARPETA/adjuntos.tar.gz" -C "$CARPETA_DATOS/adjuntos" .
tar -tzf "$CARPETA/adjuntos.tar.gz" > /dev/null

echo "[3/3] Copia fuera de la máquina"
if [ -n "${COPIA_REMOTA:-}" ] && command -v rclone > /dev/null 2>&1; then
    rclone copy "$CARPETA" "$COPIA_REMOTA" --immutable
    echo "      copiada a $COPIA_REMOTA"
else
    echo "      AVISO: sin COPIA_REMOTA o sin rclone, la copia se queda EN LA MISMA MÁQUINA."
    echo "      Eso no protege de que se rompa el servidor."
fi

# Rotación: solo se borran las carpetas locales con nombre de fecha.
find "$DESTINO" -mindepth 1 -maxdepth 1 -type d -name '20??????-??????' \
    -mtime +"$DIAS" -exec rm -rf -- {} +

echo "Hecho: $CARPETA"
