titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital elige la parcela del SIGPAC también **tocando el contorno en el mapa**, el cuaderno guiado dice de un vistazo cuánto falta y cuánto bloquea el envío, y la interfaz móvil está auditada vista por vista (10 vistas a 390 y 360, cero botones pequeños y cero centros tapados). La descarga del GeoPackage ya baja por trozos a disco (sin 638 MB en RAM). Quedan declarados la limpieza de la caché y la cola sin cobertura.
estado: en-curso
tarea: rematadas la ventana del SIGPAC (mapa tocable), el cuaderno guiado con resumen y la auditoría móvil sin solapamientos
nivel: 2
siguiente: limpieza de la caché del GeoPackage; cola sin cobertura; PAC de años anteriores y pantallas propias de PAC y gastos
bloqueado: PSD2 (nivel 3, sin coste publicado y sin gasto aprobado); y siguen pendientes de terceros las licencias (CIT, IGN) y los formatos del expediente y del Cuecyl antiguo
fecha: 2026-11-07

## Lo que se ha hecho en esta ronda

1. **Ventana del SIGPAC con los contornos en el mapa, y tocables**: cada recinto del SVG es un
   **botón** (`data-sigpac-dibujo-recinto`, `role`, `tabindex`, `aria-label`, `aria-pressed`), con
   **Enter y Espacio**, una **zona de toque invisible de 60 px** detrás del trazo (para el dedo) y el
   recinto elegido resaltado. Tocar el mapa y la lista quedan sincronizados y «Usar esta parcela» se
   habilita. Medido: el recinto más pequeño es **90×54 px a 390** y **82×49 px a 360**, y se acierta.
   No se ha tocado la búsqueda, la caché de contornos ni la aplicación del contorno a una tierra.
2. **Cuaderno guiado completo**: resumen **«Faltan N cosas · K bloquean el envío»**, cuenta por
   sección («3 cosas» / «1 cosa») y botón **«Empezar por lo primero»** que va a lo que bloquea y, si
   no hay, al primer destino disponible. La N sale del servidor (`faltan`), no se inventa. Se
   mantienen los «Arreglar» de cada fila.
3. **Auditoría móvil de verdad**: a 390×844 y 360×640, **10 vistas** comprobadas con
   `elementFromPoint`: **0 px de desborde**, **0 botones de menos de 44 px**, **0 centros tapados**;
   la barra inferior no tapa lo que se alcanza desplazando (hueco de 96 px comprobado); la ventana del
   SIGPAC sigue a pantalla completa con scroll interno y el mapa se alcanza sin que lo tape nada.
   A 1024/1440, lateral y rejillas como estaban.
4. **La descarga del GeoPackage ya no carga el ZIP en RAM**: `stream_http` baja por trozos a un
   temporal (sha256 al vuelo) y solo entonces se renombra; el `fetch` inyectable sigue sirviendo para
   los tests sin red. Con eso se cierra el pendiente de los **638 MB en RAM**.
5. **Limpieza**: el único servidor es el uvicorn temporal de las verificaciones, apagado al terminar;
   no queda ningún proceso de CueDigital escuchando.

## La última pasada, sobre este mismo HEAD

    Python       5915 recogidas · 5913 superadas, 2 omitidas, 0 fallos
    JavaScript   1305 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, móvil 390/360, ficha, apuntar (4 pestañas guardando),
    calendario, filtros, facturas, cuaderno con resumen, productos, ventana del SIGPAC con recintos
    tocables y contornos reales de Salamanca                                  0 fallos
    auditoría móvil (10 vistas × 2 anchos)             0 desbordes, 0 botones <44, 0 tapados
    capturas                                            19 en docs/capturas-nuevo/

## Lo que sigue abierto

- **Limpieza de la caché**: conviven ZIP (600 MB) y `.gpkg` (1.070 MB) por provincia; falta política
  de limpieza y decidir si se borra el ZIP tras extraer.
- **Cola sin cobertura** del apunte y **cosecha comercializada** en la app nueva.
- **PAC de años anteriores** y recintos por campaña de la Junta; pantallas propias de PAC y gastos.
- **PSD2**: dos presupuestos y decisión de gasto de David; sin código hasta contrato.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
