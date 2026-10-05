He creado la pantalla móvil **«Esto es lo que he leído - Factura»** para CUE Digital adaptada estrictamente a las especificaciones ergonómicas y visuales del proyecto:

### Decisiones de diseño implementadas:
1. **Ergonomía de campo (al sol y con una mano):**
   - Tipografía base en 18 px (`system-ui`), con botón «A+ Letra» en la cabecera fija para aumentar a 21 px.
   - Huecos y campos táctiles de mínimo **64 px de alto**, con márgenes holgados para operar con el pulgar o con guantes.
   - Teclados numéricos directos (`inputmode="decimal"`) en importes, bases e IVAs.
   - Ausencia total de sombras, desenfoques, degradados o pestañas; separación por bordes sólidos contrastados de 3 px.

2. **Origen de la lectura y compromiso de franqueza:**
   - Cabecera con distintivo «Leída de: Una foto (repasa las palabras con tilde)».
   - Mensaje de franqueza en el encabezado: *«Míralo y corrige lo que esté mal. Lo que se guarda es lo que tú digas, no lo que yo haya entendido.»*.

3. **Bloque de avisos previos:**
   - Alerta destacada en ámbar (`#ffe9a8` con borde `#8a6a00`): *«Esta misma factura ya la has subido (nº F-2026/0418). Si la guardas otra vez, la contarás dos veces.»*.

4. **Campos de factura con explicación adyacente:**
   - Cada dato cuenta con su etiqueta clara y su pista explicativa sin jerga: *«¿Quién te lo ha vendido?»*, *«Su NIF»*, *«¿Qué número tiene la factura?»*, *«¿De qué día es?»*, *«Base imponible»*, *«Tipo de IVA (%)»*, *«Cuota de IVA»* y *«Total de la factura»*.

5. **Fichas de compras y detección de descuadres:**
   - Cada concepto en una ficha individual con *«Qué es»*, *«Cuánto»*, *«En qué se mide»*, *«A cómo»* y *«Cuánto suma»*.
   - Selector radio táctil de destino en almacén: *«Sí: es Tebuconazol 25% WG»*, *«No es de la cesta (una reparación, unas botas…)»* y *«No lo tengo apuntado: créalo con estos datos»*.
   - En la ficha 2 se muestra el aviso explícito de descuadre: *«La cuenta no cuadra: mira la cantidad, el precio y el importe»*, con el desglose numérico claro.

6. **Acción de guardado único y sin pestañas inferiores:**
   - Botón principal de **72 px de altura**: «SÍ, GUARDAR ESTA FACTURA». Al pulsarse, se desactiva y pasa a mostrar «Guardando la factura…».
   - Botón claro «VOLVER» y pie informativo de funcionamiento sin cobertura. Iconografía 100% SVG.