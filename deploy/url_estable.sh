#!/bin/bash
# **URL estable para CueDigital sin comprar nada** (10/11/2026).
#
# EL PROBLEMA QUE RESUELVE
# ========================
#
# El túnel de Cloudflare que se usa para enseñar la aplicación es un *quick tunnel*: no necesita
# cuenta, pero **cambia de dirección cada vez que se recrea el contenedor**. Para tener una
# dirección que no cambie hay tres caminos (el «por qué» está en docs/DESPLIEGUE.md §10):
#
#   1. **Tailscale Funnel** (este guion): gratis, sin cuentas nuevas, y el servidor ya está en la
#      red de Tailscale. Da `https://<nodo>.<tu-red>.ts.net`. **Falta un clic de David** para
#      habilitar Funnel en su red: Tailscale no deja abrirlo sin que lo apruebe el dueño.
#   2. Un **dominio propio** apuntando a la IP pública, con Caddy delante (el `deploy/Caddyfile`
#      ya está escrito). Cuesta el dominio (unos 10 €/año) y hay que abrir 80/443 en el router.
#   3. Un **túnel con nombre de Cloudflare** (`deploy/cloudflared/config.yml`): deja de ser
#      efímero, pero necesita un token con permisos (el del 09/11 no los tiene) y un dominio.
#
# CÓMO SE USA
#
#   bash url_estable.sh            # con el puerto por defecto (8090)
#   bash url_estable.sh 8090
#
# Si Funnel no está habilitado, el guion **no se queda esperando**: saca el enlace exacto que hay
# que abrir una vez y sale con código 2. (Sin `timeout`, `tailscale funnel` se queda colgado
# esperando la aprobación: pasó el 10/11/2026.)
set -uo pipefail

PUERTO="${1:-8090}"
ESPERA="${2:-20}"

if ! command -v tailscale >/dev/null 2>&1; then
  echo "No hay Tailscale en esta máquina. Usa el dominio propio o el túnel con nombre (§10 de docs/DESPLIEGUE.md)."
  exit 1
fi

NODO="$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["ID"])' 2>/dev/null || true)"
SUFIJO="$(tailscale dns status 2>/dev/null | grep -oE 'suffix = [a-z0-9.]+' | head -1 | cut -d' ' -f3 || true)"
NOMBRE="$(hostname)"

echo "Publicando el puerto ${PUERTO} de ${NOMBRE} con Tailscale Funnel…"
salida="$(timeout "${ESPERA}" tailscale funnel --bg "${PUERTO}" 2>&1)"
codigo=$?
echo "${salida}" | head -6

if echo "${salida}" | grep -qi "not enabled" || [ "${codigo}" -eq 124 ] || [ "${codigo}" -ne 0 ]; then
  echo
  echo "**Falta un clic de David.** Tailscale no deja abrir Funnel sin habilitarlo en la red, y eso"
  echo "solo lo puede aprobar el dueño de la cuenta. Abre este enlace UNA vez:"
  echo
  if [ -n "${NODO}" ]; then
    echo "    https://login.tailscale.com/f/funnel?node=${NODO}"
  else
    echo "    https://login.tailscale.com/admin/acls  (o el panel de Tailscale: Funnel → Enable)"
  fi
  echo
  echo "Y después vuelve a lanzar:  bash url_estable.sh ${PUERTO}"
  echo
  if [ -n "${SUFIJO}" ]; then
    echo "La dirección estable será:  https://${NOMBRE}.${SUFIJO}/"
  fi
  exit 2
fi

echo
echo "Funnel en marcha. Estado:"
tailscale funnel status || true
echo
if [ -n "${SUFIJO}" ]; then
  echo "Dirección estable:  https://${NOMBRE}.${SUFIJO}/"
  echo "Comprobación:      python deploy/comprobar_publica.py https://${NOMBRE}.${SUFIJO}"
fi
