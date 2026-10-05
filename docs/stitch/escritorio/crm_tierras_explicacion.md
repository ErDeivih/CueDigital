He diseñado la pantalla de escritorio **«Tierras y mapa» (1440 × 900)** para el modo despacho del CRM agrícola de Castilla y León (**CUE Digital CyL**), respetando estrictamente todas las directrices de diseño y negocio establecidas:

### Decisiones de diseño y cumplimiento de reglas:
1. **Estilo visual y fidelidad al sistema de diseño:**
   - **Cero sombras, degradados ni animaciones:** la interfaz se estructura con bordes sólidos y contrastados (2 a 3 px) sobre fondos planos, optimizada para alta legibilidad en pantalla con ratón y teclado.
   - **Iconografía 100% vectorial (SVG):** sin emojis en ningún componente ni alerta.
   - **Paleta y tipografía del proyecto:** Verde principal (`#1f4a2c`), verde oscuro de bordes (`#0d2b18`), ámbar para avisos (`#ffe9a8`), rojo para incidencias y blanco puro para las superficies de trabajo.

2. **Navegación y cabecera de despacho:**
   - Barra superior completa con indicación de **Finca activa (187,42 ha)**, selector de campaña activa **2026**, estado de sincronización **SIEX / REGEPA al día**, modo local SQLite activo y firma digital FNMT.
   - Pestaña **«Tierras y mapa»** activa con indicador numérico de las 64 parcelas.

3. **Franja visible de filtros interactivos:**
   - Buscador completo (*«Buscar por nombre, referencia SIGPAC o municipio»* con búsqueda activa *"Villalar"*).
   - Desplegables de tamaño compacto (32–36 px): cultivo, municipio, régimen (secano/regadío), titularidad y campaña.
   - Casillas destacadas de acceso directo: *«Solo las que no tienen cultivo declarado (10)»* y *«Solo las que no tienen forma (3)»*.
   - Franja de **píldoras de filtros activos con botón de borrado individual («×»)** y enlace directo a **«QUITAR TODOS LOS FILTROS»**.
   - A la derecha: botón desplegable **«EXPORTAR (14 filtradas)»** y botón principal **«+ AÑADIR UNA TIERRA»**.

4. **Tabla y mapa sincronizados:**
   - **Tabla parcelaria a la izquierda (7/12 de ancho):**
     - Columnas explícitas con ordenación: *Nombre / Parcela*, *Municipio*, *Área gestionada* (alineada a la derecha con dos decimales y `ha`), *Cultivo actual*, *Último trabajo*, *Pendientes* y *Estado de la forma*.
     - Acciones compactas a la derecha de cada fila: **«Abrir»**, **«Planif.»** y **«Labor»** (la fila completa no actúa como botón).
     - Datos veraces y rigurosos sin inventar: campos sin información muestran «—» o «Pendiente» (ej. albarán de semilla con coste pendiente, 10 tierras sin cultivo).
     - Fila seleccionada (*El Prado*, 4,90 ha) con borde verde grueso, checkbox activo e indicador de foco.
     - En pantallas menores a 1180 px o 1024 px, la disposición se apila automáticamente para que **la columna de acciones nunca se oculte**.
   - **Visor cartográfico a la derecha (5/12 de ancho):**
     - Conmutador de vista *«Tabla / Los dos / Mapa solo»*.
     - Capas encendibles con leyenda y fuentes: *Tierras gestión*, *Cultivos*, *Avisos / ITEAF*, *Nitratos / Agua* y *Ortofoto PNOA*.
     - Esquema parcelario con ortofoto gráfica de secano castellano, caminos rurales, lindes y el polígono de *El Prado* destacado con el borde de foco amarillo (`#ffd24a`) y tarjeta flotante con datos de inspección oficial.

5. **Gestión de tierras sin geometría:**
   - Las 3 parcelas sin dibujo (*El Sotillo Húmedo*, *Finca El Cascajal* y *Majada del Valle*) se muestran en una sección destacada con aviso formal y llamada a la acción para dibujarlas o delimitarlas directamente en el visor.

6. **Muestrario de estados del sistema:**
   - Se incluye en el bloque inferior el muestrario completo de los 5 estados adicionales de la interfaz: **1. Estado Vacío**, **2. Sin resultados por filtro**, **3. Cargando datos SIGPAC**, **4. Error de servicio** y **5. Conflicto / Solape de superficie en REGEPA**.

7. **Pie de estado de despacho:**
   - Atajos de teclado para agilizar la labor de oficina (`[Ctrl+F]`, `[N]`, `[Espacio]`, `[Esc]`), latencia, resolución nativa (1440 × 900) y certificación digital.