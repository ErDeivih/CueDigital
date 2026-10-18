#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
node --version
printf '%s\n' 'Entorno preparado. Consulta DESARROLLO_EN_LA_NUBE.md.'
