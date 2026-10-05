He diseñado e integrado la pantalla de escritorio **«Tierras» (1440×900)** para el entorno de despacho de CUE Digital (Castilla y León).

### Estructura y decisiones de diseño:
1. **Menú lateral izquierdo fijo (240 px)**: 
   - Cabecera con el ámbito de la explotación (*Castilla y León · Secano y Riego*).
   - Todos los módulos con icono SVG y rotulación clara: *Panel*, *Cuaderno*, *Tierras* (activo con fondo distintivo verde oscuro, indicador ámbar y barra de resalte a la izquierda), *Almacén*, *Análisis*, *Ventas*, *Plan de abono*, *Documentos*, *Facturas*, *Productos y máquinas*, *Años del cuaderno* y *Mis datos*.
   - Estado de sincronización en local al pie del menú.

2. **Barra superior a lo ancho (64 px)**:
   - Marca *CUE Digital* con etiqueta *DESPACHO*.
   - Selector contextual de la explotación (*Finca Las Suertes y El Prado · 187,42 ha*).
   - Campaña activa *2026* con fechas oficiales.
   - Datos del usuario titular (*David Pérez Velasco · NIF 12345678Z*) y el botón principal verde sólido **«APUNTAR»**.

3. **Franja de herramientas y tabla densa para ratón y teclado**:
   - Acciones superiores compactas (34 px): **«AÑADIR UNA TIERRA»**, **«SACAR EN EXCEL»** e **«IMPRIMIR»**.
   - Buscador en vivo (*Buscar entre tus tierras...*), selector por pueblo (*Villalar, Tordesillas, Castronuño*), filtro por cultivo y casilla destacada **«Sólo las que les falta decir qué tienen»**.
   - Columnas con cabecera pegada fija al hacer scroll (*Nº*, *Nombre*, *Referencia SIGPAC*, *Pueblo*, *Hectáreas* con 2 decimales y alineadas a la derecha, *Qué tiene este año*, *Sistema* y *Acciones*).
   - Estado de cultivo: muestra el cultivo y su variedad, y en caso de faltar (filas 2 y 6) despliega el aviso en ámbar con el botón **«DECIRLO»**.
   - Acciones por fila: botones compactos «Editar» y «Borrar» (en color de peligro discreto).
   - Pie con resumen oficial (*64 tierras · 187,42 ha*) y selector de páginas.

4. **Panel lateral derecho de detalle (340 px)**:
   - Ficha de la tierra seleccionada (*El Prado · 4,90 ha · Villalar de los Comuneros*).
   - **Dibujo de la parcela**: polígono SVG limpio del recinto con norte magnético y orientación clara sin sobrecargar con cartografía pesada.
   - Cultivo declarado en campaña (*Cebada cervecera · Cerveza Planet*).
   - Sus **3 últimos apuntes** con fecha, tipo de tratamiento/abono y dosis aplicada.
   - Botón directo **«VER LA TIERRA ENTERA»**.