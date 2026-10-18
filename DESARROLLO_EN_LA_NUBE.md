# CUE Digital en GitHub y en un entorno de desarrollo en la nube

Repositorio privado preparado el 18/10/2026. No incluye la base real del agricultor,
sus adjuntos, certificados privados, claves ni el entorno virtual local.

## Por dónde empezar

1. Leer `AGENTS.md`, `CONTEXTO_PARA_EL_CHAT.md` y los contratos de `docs/`.
2. Consultar `contexto_agentes/REVISION_PAC_2026-10-18.md` y la cola de continuidad.
3. Comprobar rama, último commit y estado: este repositorio distingue código revisado
   de una instantánea del trabajo PAC pendiente.

Conectar este repositorio privado al chat es un paso de la cuenta del usuario; crear
el repositorio no concede automáticamente acceso a una conversación. Un chat con
lectura de GitHub tampoco tiene necesariamente un entorno donde ejecutar la aplicación.

## Ramas iniciales

- `main`: revisión eec9e55 y documentación/configuración de desarrollo en la nube.
  El recorrido de roles pasó 53 comprobaciones sobre eec9e55. Las pruebas nuevas de
  escenarios y fotos también pasaron, pero existen los límites PAC del informe.
- `trabajo/pac-en-curso-2026-10-18`: copia de los cambios locales no commiteados en el
  momento de preparar GitHub. Es trabajo en curso, no una entrega certificada.
- `estabilizacion-2026-10-18`: historial de estabilización local conservado.
- `principal`: referencia histórica original. No usar su nombre para deducir cuál es
  la versión más nueva; la rama predeterminada de GitHub es `main`.

La copia de publicación se preparó fuera del checkout donde trabajaba DeepSeek.
No se cambiaron ni descartaron sus archivos locales.

## Preparación en Linux

Requisitos: Python 3.12 y Node.js 24. No hay compilación npm del frontend.

```bash
bash .codex/setup.sh
```

El script instala las dependencias de `backend/requirements.txt` en `.venv`.
No necesita claves de proveedores, credenciales agrícolas ni una base de producción.
La primera instalación necesita acceso a PyPI.

## Pruebas

```bash
cd backend
../.venv/bin/python -m pytest tests
node --test "tests_js/*.test.js"
```

pytest configura su propia base y adjuntos temporales desde `tests/conftest.py`.
No sobrescribir esa configuración para apuntar a una base real.

GitHub Actions ejecuta ambas suites una vez por cambio en `main` o pull request.
No confundir esos checks con el recorrido de Chrome, pruebas de PostgreSQL o una
validación normativa: esos alcances se verifican por separado.

## Arranque para una vista previa de desarrollo

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Usar la vista previa privada del entorno. Se parte sin cuentas ni datos agrícolas;
dar de alta una cuenta de prueba. El acceso del preview debe seguir siendo privado.
No es un despliegue de producción. Sin un secreto persistente, las sesiones pueden
invalidarse al reiniciar; no copiar secretos de David para evitarlo.

En Windows usar `..\.venv\Scripts\python.exe` desde backend. La instalación local de
David vive en otra carpeta y no depende del entorno de este repositorio.

## Límites del entorno remoto

- AutoFirma y certificados personales son integraciones del equipo del usuario.
- Los guiones `navegador_cdp.py` usan el navegador de la instalación local; no asumir
  que funcionen en un contenedor Linux sin adaptar/verificar ese entorno.
- PostgreSQL necesita su motor y driver; SQLite es la vía local y de tests habitual.
- OCR, meteo/satélite, Stitch e IUWS pueden necesitar programas, servicios o accesos
  externos. Sus ausencias no impiden revisar el código o ejecutar las suites básicas.
- No subir `cuedigital.db`, `/datos`, adjuntos, `.env`, certificados privados ni claves.
  Los datos oficiales de `data/` y las fixtures ficticias de tests sí pertenecen al código.

## Continuidad de agentes

Los documentos de `contexto_agentes/` vienen del perfil local de CUE Digital. Sus rutas
Windows son contexto histórico: en la nube usar estas copias y las rutas del checkout.
No seguir las colas de RadioPV o facylf de otros proyectos.

Antes de editar, actualizar el diagnóstico contra el código de la rama elegida.
No confundir una instantánea pendiente con una reparación verificada. No resetear
trabajo ajeno ni subir datos de producción para reproducir fallos.
