He creado la pantalla móvil **«Añadir una factura»** para **CUE Digital**, adaptada punto por punto a los requisitos del agricultor de Castilla y León para su uso de pie en el campo:

### Decisiones de diseño y cumplimiento de reglas:
1. **Tipografía y tamaño accesible:**
   - Tipografía base de **18 px** (`system-ui`), con peso y contrastes diseñados para leerse bajo la luz solar directa sin reflejos confusos.
   - Botón superior de accesibilidad **«A+ Letra»** que amplía el texto a 21 px y los botones a 72 px.
2. **Dimensiones ergonómicas para una sola mano:**
   - Botones con una altura mínima de **64 px**, esquinas redondeadas y bordes perimetrales de 3 px de alto contraste (sin sombras ni degradados, tal como exige la guía de CUE Digital).
3. **Identificación y continuidad:**
   - Título idéntico al acceso previo: **«AÑADIR UNA FACTURA»** y subtítulo aclaratorio: *«Aquí guardas las facturas de lo que compras»*.
4. **Zona de selección táctil visible de un vistazo:**
   - Rótulo claro: *«La factura: una foto o el fichero del proveedor»*.
   - Hueco ancho táctil con iconos SVG limpios (cámara para foto directa y subida de fichero/PDF) y explicación concisa.
   - Pista formativa lateral: *«Hazle la foto al papel entero, con luz y sin torcerlo. Si tienes el fichero, súbelo: se lee mejor y no hay que adivinar nada.»*
5. **Garantía y tranquilidad sin jerga informática:**
   - Bloque de confianza destacado: *«Trato claro: el programa solo intenta leer el papel. Nada se guarda en el cuaderno hasta que tú lo mires en pantalla y digas si está bien.»*
   - Avisos en castellano directo para situaciones de campo:
     - Sin cobertura: *«Para leer la factura hace falta conexión. El fichero lo tienes en tu móvil: prueba cuando tengas cobertura o escríbela a mano ahora.»*
     - Error de lectura: *«No se ha podido leer la factura. Prueba otra vez o escríbela a mano.»*
6. **Los tres caminos independientes y accesibles:**
   - **«LEER LA FACTURA»**: el botón de acción principal en verde oscuro contrastado (`#2f6b40` / `#0d2b18`), que al pulsarse pasa al estado inactivo diciendo *«Leyendo la factura…»*.
   - **«ESCRIBIRLA A MANO»**: siempre visible como alternativa directa sin esconder nada.
   - **«VOLVER»**: botón neutral para regresar al listado.
7. **Sin menús flotantes ni barras de pestañas inferiores**, manteniendo la navegación vertical de una sola columna.