titulo: CueDigital — documentacion de control
estado: en-curso
tarea: D08 decidido (las tres decisiones a coste 0) y la propuesta escrita y verificada
nivel: 2
siguiente: D08-1, el instrumento del OCR listo para un corpus real
bloqueado: el corpus — 30 facturas con permiso escrito y 210 valores de patron (David; no es dinero)
fecha: 2026-11-04

## Lo que se ha hecho en esta sesion

1. **D08, decidido**: corpus = facturas reales del titular y sus proveedores **con permiso escrito**
   (0 €); proveedor de OCR = **Tesseract local** (0 €, ya construido); meteo y satélite = **AEMET
   OpenData + Copernicus Data Space Ecosystem** (0 €, con atribución). Las **dos opciones de cada
   decisión**, con coste, licencia y límite medidos (URL oficial y fecha 04/11/2026), están en
   `docs/D08_CORPUS_Y_PROVEEDOR.md`; el motivo de nivel 2 está en `DECISIONES.md`; la regla aplicada,
   en `ESPECIFICACION.md`.
2. **Por que no se para a preguntar**: la regla de David solo manda parar cuando **las dos** opciones
   tienen coste relevante. Aquí la más barata que cumple cuesta **0 € en las tres decisiones** (las
   alternativas de referencia son 999 €/año + IVA, 1,50 USD/1.000 páginas y un corpus público que no
   puede medir el NIF). No se ha contratado nada ni se ha pagado nada.
3. **Lo que bloquea D08, ahora con nombre**: **el corpus** —30 facturas (10 en PDF del proveedor, 10
   escaneadas, 10 fotografías) con **permiso escrito del emisor** y **210 valores de patrón** (7 por
   factura)—. Es una aportación de David, **no un gasto**. Sin eso, el OCR no se mide y **D08 no se
   cierra**; el documento deja el modelo de permiso y el número de facturas por formato.
4. **Verificación independiente**: un revisor aparte comprobó las 20 afirmaciones del documento contra
   las páginas oficiales: **13 confirmadas, 5 matizadas, 0 falsas**. Los matices ya están corregidos
   (el cupo de Copernicus se planifica con **10.000 PU/mes**, no con los 30.000 de un PDF aparte;
   Sentinel-2 tiene **cuatro** bandas a 10 m; el umbral del PDF son **40 caracteres sin espacios**; la
   nota legal de Sentinel no usa la palabra «comercial»; la URL del DPA de Microsoft dio 403 y su
   texto no se cita).
5. **Nota de coordinación, importante**: el guion de arranque de esta sesión cita **«los documentos
   50–57»** y **`docs/DEBT.md`**. **Ninguno de los dos existe en este repositorio**: se ha buscado en
   `docs/`, `backend/docs/`, el historial de git y las ramas `flujo/*`. Los documentos de D08 que sí
   existen son `backend/docs/PENDIENTE_D08.md` y `backend/docs/ESTADO.md`, y la deuda vive en
   `BACKLOG.md` («Deuda anotada, no priorizada»). No se ha inventado su contenido.

## La última pasada, sobre este mismo HEAD

    Python       5649 superadas, 2 omitidas, 0 fallos  (5651 recogidas) · 20:56
    JavaScript   1228 superadas, 0 fallos
    (la suite de Python tarda 21 minutos, no los 30 segundos que dice `AGENTS.md`: se anota sin tocarlo)

Nota de andamio: `pytest -q` en pytest 9.1.1 **no imprime la línea de resumen**; el desglose de arriba
se ha medido con la invocación normal (`pytest`), que es la que documenta `AGENTS.md`.

## Lo que sigue abierto

- **D08 no está cerrado**: falta el corpus (material de David). Mientras tanto, las tareas 12 y 13 del
  `BACKLOG.md`: **D08-1** (el instrumento del OCR listo para un corpus real) y **D08-2** (meteo y
  satélite con el ejemplo guardado y sin clave).
- **D01-A** (aceptación con dos pestañas reales), **D07** (ciclo de vida de las raíces de React) y la
  **intermitencia de la suite de Python**, en el `BACKLOG.md` con su criterio de aceptación.
- Límites duros respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama, y **no se ha usado GitHub Actions**. Push: al final de esta sesión, en
  `integracion/cloud-estabilizacion-2026-10-21`.
