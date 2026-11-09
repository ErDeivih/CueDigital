# syntax=docker/dockerfile:1
#
# Imagen de producción de CUE Digital (el cuaderno de campo).
#
# DECISIONES, Y POR QUÉ
#
# 1. **La base es la misma versión de Python que el entorno con el que se prueba**
#    (`..\.venv\Scripts\python.exe --version` → 3.12.10). Probar con una y desplegar
#    con otra es la forma más tonta de que aparezca un fallo solo en el servidor.
#
# 2. **Se instalan `requirements.txt` Y `requirements-produccion.txt`.** El primero
#    trae lo que usa la aplicación (incluidos `httpx`, `openpyxl` y `pdfplumber`, que
#    se importan en tiempo de ejecución aunque su comentario diga otra cosa); el
#    segundo, el driver de PostgreSQL (`psycopg`), que es lo único que falta para
#    producción. Ver el porqué en `backend/requirements-produccion.txt`.
#
# 3. **La aplicación necesita `data/` al lado de `backend/`.** No es un capricho: el
#    código resuelve `Path(__file__).resolve().parents[2]` y de ahí cuelga
#    `data/` (municipios del INE, zonas vulnerables, catálogos del SIGPAC, tablas de
#    nitratos, el descriptor del IUWS y el idioma español del OCR). Los adjuntos del
#    agricultor NO van dentro de la imagen: viven en un volumen (`CUEDIGITAL_ADJUNTOS`).
#
# 4. **Tesseract se instala aparte y es opcional para el programa.** El lector de
#    letras es un programa externo (ver `backend/app/ocr.py`); sin él, las facturas se
#    guardan como justificante y los datos se escriben a mano. Se incluye para que el
#    servidor haga lo mismo que la máquina de desarrollo. Si sobra espacio, se puede
#    quitar la línea de `apt-get` y la imagen encoge; el programa seguirá arrancando y
#    dirá que no puede leer la foto.
#
# 5. **No se ejecuta como root.** El usuario `cuedigital` (uid 10001) es el dueño de
#    `/datos`. La carpeta del servidor que se monta ahí tiene que ser suya (ver
#    `deploy/LEEME.md`): si no, el primer documento subido falla con un error de
#    permisos que no dice nada útil.
#
# 6. **Una sola instancia.** `crear_tablas()` se ejecuta al arrancar (`app/main.py`,
#    `ciclo_de_vida`) y hace cambios en el esquema. Dos contenedores de la aplicación
#    arrancando a la vez podrían pisarse. Con una instancia no hay problema; si algún
#    día se escala, las migraciones tienen que salir a un paso aparte (está en
#    `docs/DESPLIEGUE.md`).
#
# LO QUE NO SE HA HECHO AQUÍ: construir la imagen. En la máquina donde se escribió esto
# hay Docker 27.4, pero no se ha lanzado `docker build` (descarga de paquetes, tiempo y
# espacio). Está dicho también en `docs/DESPLIEGUE.md`.

FROM python:3.12-slim-bookworm

# Tesseract: el lector de letras de las facturas. `--no-install-recommends` para no
# arrastrar medio escritorio; los idiomas NO se instalan aquí: el proyecto trae el
# español en `data/ocr/tessdata` (2,2 MB) y lo usa con TESSDATA_PREFIX sin tocar la
# instalación del sistema (ver `backend/app/ocr.py`).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Europe/Madrid \
    CUEDIGITAL_ADJUNTOS=/datos/adjuntos \
    CUEDIGITAL_SIGPAC_CACHE=/datos/sigpac_cache

WORKDIR /app

# Las dependencias primero: así un cambio en el código no vuelve a instalarlas.
COPY backend/requirements.txt backend/requirements-produccion.txt ./backend/
RUN python -m pip install --upgrade pip \
    && python -m pip install \
        -r backend/requirements.txt \
        -r backend/requirements-produccion.txt

# El código y los datos oficiales que lee el programa. Se copian por rutas concretas
# (no `COPY . .`) para no meter en la imagen los tests, los guiones ni la documentación.
COPY data ./data
COPY backend/app ./backend/app
COPY backend/web ./backend/web

# El usuario sin privilegios y las dos carpetas de datos.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin cuedigital \
    && mkdir -p /datos/adjuntos /datos/sigpac_cache \
    && chown -R cuedigital:cuedigital /datos

USER cuedigital

# `app.main:app` se importa desde `backend/`, igual que en desarrollo.
WORKDIR /app/backend

EXPOSE 8000

# La comprobación de vida del propio contenedor. Usa la biblioteca estándar para no
# depender de `curl`. OJO: `/health` dice que el programa atiende, pero NO consulta la
# base de datos (ver `docs/DESPLIEGUE.md`, apartado «Qué falta hoy»): que esto pase no
# demuestra que PostgreSQL esté bien.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# `--proxy-headers` para que el programa sepa que la petición viene de Caddy.
# `--no-server-header` para no anunciar el servidor. Una sola instancia: ver la
# decisión 6 de arriba.
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*", \
     "--no-server-header"]
