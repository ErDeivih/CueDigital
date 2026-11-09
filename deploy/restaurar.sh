#!/usr/bin/env bash
# ENSAYO DE RESTAURACIÓN de CUE Digital, sobre un destino NUEVO.
#
# POR QUÉ ASÍ (es la regla que ya sigue el proyecto con SQLite)
#
# Una copia no se prueba copiándola: se prueba USÁNDOLA. Y nunca se restaura encima de
# la base de verdad, porque un ensayo que escribe sobre los datos buenos no prueba
# nada y puede estropearlos. Por eso esto:
#
#   1. crea una base de datos NUEVA en el mismo PostgreSQL (no toca la de producción),
#   2. restaura ahí el volcado,
#   3. descomprime los adjuntos en una carpeta NUEVA,
#   4. cuenta lo que hay, y
#   5. dice cómo levantar una SEGUNDA instancia de la aplicación contra esa copia, en
#      un puerto local, para entrar y abrir un documento de verdad.
#
# En el proyecto hay un guion equivalente para SQLite
# (`backend/scripts/verificar_la_copia_y_la_restauracion.py`), que además comprueba
# que se puede abrir un papel guardado. Esta es la misma idea, con PostgreSQL.
#
# USO
#
#     ./deploy/restaurar.sh /srv/cuedigital/copias/20261110-031501
#     ./deploy/restaurar.sh /srv/cuedigital/copias/20261110-031501 cuedigital_ensayo_1
#
# NO SE HA PODIDO PROBAR EN ESTA MÁQUINA (no hay servidor).

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "uso: $0 <carpeta-de-la-copia> [nombre-de-la-base-nueva]" >&2
    exit 2
fi

COPIA="$(cd "$1" && pwd)"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENTORNO="$RAIZ/deploy/.env"
NUEVA="${2:-cuedigital_ensayo_$(date +%Y%m%d%H%M%S)}"

if [ ! -f "$COPIA/base.dump" ] || [ ! -f "$COPIA/adjuntos.tar.gz" ]; then
    echo "FALLO: en $COPIA no están base.dump y adjuntos.tar.gz." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENTORNO"
set +a

: "${CARPETA_DATOS:?falta CARPETA_DATOS}"
: "${POSTGRES_USER:?falta POSTGRES_USER}"
: "${POSTGRES_DB:?falta POSTGRES_DB}"
: "${CUEDIGITAL_DATABASE_URL:?falta CUEDIGITAL_DATABASE_URL}"
: "${CUEDIGITAL_SECRETO:?falta CUEDIGITAL_SECRETO}"

if [ "$NUEVA" = "$POSTGRES_DB" ]; then
    echo "FALLO: el nombre de la base nueva no puede ser el de producción ($POSTGRES_DB)." >&2
    echo "Este guion NO restaura encima de los datos buenos, a propósito." >&2
    exit 1
fi

COMPOSE=(docker compose -f "$RAIZ/deploy/docker-compose.yml")
ENSAYO="$CARPETA_DATOS/ensayos/$NUEVA"

echo "[1/4] Creando la base NUEVA «$NUEVA» (la de producción no se toca)"
"${COMPOSE[@]}" exec -T db \
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$NUEVA\";"

echo "[2/4] Restaurando la base"
"${COMPOSE[@]}" exec -T db \
    pg_restore -U "$POSTGRES_USER" -d "$NUEVA" --no-owner --no-privileges < "$COPIA/base.dump"

echo "[3/4] Adjuntos → $ENSAYO/adjuntos"
mkdir -p "$ENSAYO/adjuntos"
tar -xzf "$COPIA/adjuntos.tar.gz" -C "$ENSAYO/adjuntos"

echo "[4/4] Comprobando que hay datos"
"${COMPOSE[@]}" exec -T db psql -U "$POSTGRES_USER" -d "$NUEVA" -c \
    "SELECT (SELECT count(*) FROM explotaciones) AS fincas,
            (SELECT count(*) FROM usuarios) AS cuentas,
            (SELECT count(*) FROM documentos_anexos) AS papeles;"

URL_NUEVA="${CUEDIGITAL_DATABASE_URL%/*}/$NUEVA"

cat <<FIN

La copia está restaurada en un destino NUEVO:
  base de datos: $NUEVA
  adjuntos:      $ENSAYO/adjuntos

Para ABRIRLA y usarla de verdad (entrar, ver una finca y descargar un papel), levanta
una segunda instancia en este mismo servidor, escuchando solo en 127.0.0.1:8001:

  docker run --rm --network cuedigital_default \\
    -e CUEDIGITAL_DATABASE_URL="$URL_NUEVA" \\
    -e CUEDIGITAL_SECRETO="$CUEDIGITAL_SECRETO" \\
    -e CUEDIGITAL_ADJUNTOS=/datos/adjuntos \\
    -v "$ENSAYO/adjuntos:/datos/adjuntos:ro" \\
    -p 127.0.0.1:8001:8000 \\
    cuedigital-app

Y desde otra terminal:

  curl -fsS http://127.0.0.1:8001/health
  # entra con una cuenta que exista en la copia y descarga un documento

Cuando termines:  Ctrl+C, y borra el ensayo si ya no hace falta:
  docker compose -f deploy/docker-compose.yml exec -T db \\
      psql -U $POSTGRES_USER -d postgres -c "DROP DATABASE \\"$NUEVA\\";"
  rm -rf "$ENSAYO"
FIN
