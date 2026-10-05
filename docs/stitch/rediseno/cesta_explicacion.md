He diseñado la pantalla móvil **«Lo que tengo en el almacén»** respetando punto por punto los requisitos de uso en el campo bajo el sol para Castilla y León y las directrices de CUE Digital:

### Decisiones de diseño aplicadas:
1. **Legibilidad al sol y una sola mano**:
   - Tipografía base de **18 px o superior** (`system-ui`), con el botón **«A+ Letra»** siempre disponible en la cabecera fija de 64 px.
   - **Sin sombras, degradados ni transparencias**: separación nítida mediante bordes sólidos de 3 px y fondos de contraste alto (verde `#1f4a2c`, blanco `#ffffff` y ámbar `#ffe9a8`).
   - Iconografía 100 % vectorial dibujada con **SVG** (sin emojis ni fuentes de iconos externas que requieran descarga o cobertura).

2. **Jerarquía del libro de movimientos**:
   - **Encabezado y propósito**: «*Aquí ves cuánto producto compraste, cuánto llevas echado y cuánto te queda. Sirve para dos cosas: saber si te llega para tratar la parcela, y tener el libro de entradas y salidas que se mira en una inspección.*».
   - **Contador con concordancia exacta**: «*Tienes 3 productos apuntados.*» destacado con viñeta verde.
   - **Tarjetas de producto**:
     - Nombre comercial y materia activa sin jerga.
     - Filas ordenadas: **«Compraste»**, **«Llevas echado»** (con el apunte de intervenciones).
     - **«Te queda en el almacén» es el número más grande y visible** de la tarjeta (tamaño destacado de más de 2 rem en negrita fuerte), permitiendo comprobar de un vistazo el remanente.

3. **Gestión de incidencias sin números ficticios**:
   - Cuando falta un dato se muestra un **guion (—)**, nunca un cero, explicando al lado la causa exacta:
     - Falta de compra: «*No has apuntado cuánto compraste, así que no se puede saber cuánto te queda. Apúntalo en la ficha del producto y aquí saldrán las cuentas.*» con su botón de acción directo.
     - Unidades discordantes: «*Lo compraste en litros y lo echas en kilos. Son cosas distintas y no se pueden restar: un litro y un kilo no son lo mismo.*».
   - Mensaje para cuando no haya productos: «*Todavía no has apuntado ningún producto. Cuando apuntes uno, aquí verás lo que te queda.*».

4. **Navegación y cierre**:
   - Frase final con las palabras directas del agricultor: «*Si un día te preguntan cuánto producto has comprado y cuánto has echado, esto es la respuesta. Y si te queda poco, lo ves antes de quedarte sin él en mitad del tratamiento.*».
   - Botones táctiles grandes (≥64 px de alto) con texto y explicación: **«MIS PRODUCTOS»** y **«VOLVER»**, prescindiendo de barras de pestañas y menús ocultos.