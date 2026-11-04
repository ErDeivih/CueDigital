# Especificación — CueDigital

Estado: **borrador**. Documento de coordinación; el proyecto ya tiene sus documentos en `docs/`.

## Decisión de coordinación (2026-11-04)

**¿Qué corpus y qué proveedor para D08?**

- No se decide a ciegas: el agente **propone dos opciones concretas** con coste, licencia y límite de uso, y elige **la más barata que cumpla**.
- El corpus debe poder **citarse** (documento, página) y su licencia no puede impedir el uso en producción.
- Si las dos opciones tienen coste relevante, para y pregunta: es nivel 3.

## Decisión tomada (2026-11-04)

La regla anterior se ha aplicado y **está decidido**. Las dos opciones de cada decisión, medidas con
coste, licencia y límite de uso (URL y fecha en cada cifra), están en
[`docs/D08_CORPUS_Y_PROVEEDOR.md`](docs/D08_CORPUS_Y_PROVEEDOR.md):

| decisión | se elige (0 €) | la alternativa, para comparar |
|---|---|---|
| **Corpus** | facturas reales del titular y sus proveedores, **con permiso escrito**; se cita cada una por emisor, número y página | corpus públicos FATURA + CORD (CC BY 4.0), que **no miden** el NIF ni el IVA español |
| **Proveedor de OCR** | **Tesseract local** (ya construido, Apache 2.0) | Azure AI Document Intelligence: 1,50 USD/1.000 páginas |
| **Meteo y satélite** | **AEMET OpenData + Copernicus Data Space Ecosystem**, con atribución | Sentinel Hub plan Basic: **999 €/año + IVA** |

**Lo que sigue bloqueado, y de quién depende**: el **material del corpus** —30 facturas (10 en PDF,
10 escaneadas, 10 fotografiadas) con **permiso escrito del emisor** y los 7 valores de patrón de cada
una—. Es una aportación de David, **no un gasto**. Sin eso no se mide el OCR y **D08 no se cierra**;
lo que sí se puede hacer mientras tanto son las tareas D08-1 y D08-2 del `BACKLOG.md`. La decisión y su
motivo están en `DECISIONES.md`.

## Reglas

- No tocar `.env` ni las fixtures de firma.
- Autorización en el servidor, con matriz de roles escrita.
- Pruebas de flujo, no de detalle: ver `F:\EspacioCodigo\_flujo-dsh\DOCTRINA-CALIDAD.md`.
