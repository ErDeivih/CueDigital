He diseñado la pantalla móvil **«Traer mis tierras del cuaderno de la Junta»** para **CUE Digital**, adaptada con rigor a las directrices de `DESIGN.md` y a las necesidades específicas de un agricultor de 50 a 70 años en el campo:

### Decisiones de diseño y cumplimiento de reglas:
1. **Ergonomía de campo al sol y a una mano:**
   - Tipografía base de **18 px** (ampliable a 21 px con el botón de cabecera `A+ Letra`).
   - Botón principal de **104 px de alto** (`btn-principal`) y botones de interacción de **64 px de alto mínimo**.
   - Sin degradados, sin transparencias ni sombras (separación nítida con bordes de 3 px de alto contraste: `#1f4a2c`, `#0d2b18`, `#8a6a00`).
   - Todos los iconos son vectoriales SVG limpios y reconocibles (sin emojis).

2. **Estructura en 3 fases claras sin pestañas ni menús:**
   - **Indicador de 3 pasos continuo** arriba con indicador de fase explícito (`PASO 1 DE 3`, `PASO 2 DE 3`, `PASO 3 DE 3`), manteniendo siempre visible el botón `VOLVER` en la barra fija superior de 64 px.
   - **Paso 1 (Elegir fichero):** Con los tres pasos explicados de forma directa («Entra en la aplicación de la Junta con tu certificado...»), zona amplia de selección de archivo y el botón principal **«TRAER MIS TIERRAS»**, que al pulsarse pasa a estado deshabilitado con el texto **«Abriendo el cuaderno…»** antes de mostrar el resumen.
   - **Paso 2 (Resumen previo: «Esto es lo que trae tu cuaderno»):** Aviso claro de que **leer el fichero no apunta nada**. Contiene exactamente los 8 campos solicitados (*Campaña, Titular, Tierras apuntadas en el papel, Tierras distintas, Hectáreas que declaras, Pueblos, Lo que tienes sembrado* y *Tierras en zona de nitratos* destacado en ámbar), el listado previo de parcelas y los dos botones de decisión: **«SÍ, SON MIS TIERRAS»** (principal de 104 px) y **«NO, VOLVER»** (claro).
   - **Paso 3 (Resultado: «Tus tierras ya están apuntadas»):** Cada cuenta en su renglón con insignia numérica (*Tierras nuevas: 51*, *Tierras que ya tenías y les he puesto lo que siembras: 3*, *Tierras que ya estaban apuntadas: 2*), sin mostrar cuentas a cero. Bloque con los datos del titular auto-rellenados, sección de advertencia constructiva **«Cosas que conviene que mires»** (nitratos y barbecho), la nota tranquilizadora de que se puede subir cuantas veces se quiera sin duplicar tierras, y los botones finales **«VER MIS TIERRAS»** y **«VOLVER»**.

3. **Sin barra de navegación inferior ni elementos ocultos:**
   - Pantalla limpia en una sola columna centrada (máximo 44 rem), orientada a resolver el trámite de una vez sin distracciones.
   - Incluye un conmutador interactivo inferior para que puedas revisar de inmediato cómo luce cada una de las 3 fases.