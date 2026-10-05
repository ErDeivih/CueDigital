He diseñado la pantalla móvil **«Los análisis»** para CUE Digital adaptada estrictamente a las condiciones reales de trabajo de un agricultor de Castilla y León (al sol, con una mano, de pie en la parcela y sin cobertura):

### Decisiones de diseño y cumplimiento de reglas:
1. **Legibilidad al sol y contraste:**
   - Tipografía base de 18 px (`system-ui` para evitar descargas sin cobertura), con títulos en negrita contundente (1,35–1,45 rem) y datos numéricos grandes (1,55 rem).
   - Sin sombras, sin degradados y sin transparencias: toda la jerarquía se resuelve mediante **bordes sólidos de 2 a 4 px** y fondos planos de alto contraste (> 7:1).
   - Iconografía 100 % en **SVG geométrico limpio**, sin recurrir a emojis.

2. **Estructura e información requerida:**
   - **Cabecera fija superior:** con botón accesible `A+ Letra` y salida clara. Sin menús desplegables ni barras de pestañas inferiores.
   - **Explicación inicial textual:** *«Aquí se guardan los análisis que has mandado hacer: de la tierra, del agua, de la planta o de la cosecha. Con los números de la tierra se abona mejor, y el papel del laboratorio no se pierde.»*
   - **Contador y vigencia de un vistazo:** Indicador destacado (`2 análisis guardados`) y distintivos visuales contrastados para diferenciar los boletines recientes (*«De este año (2026)»*) frente a los antiguos (*«Hace 2 años (2024)»*).
   - **Fichas detalladas completas:** Con los 5 campos requeridos (*De dónde salió*, *Muestra cogida el*, *Resultado el*, *Laboratorio* y *Nº de boletín*).
   - **Sección de números de boletín vs aviso:** Muestra los valores clave con su magnitud y unidad (materia orgánica, pH, fósforo, etc.), y en el caso sin datos copiados incluye el aviso reglamentario: *«Sin números apuntados: solo está guardado el boletín.»*
   - **Gestión del papel/PDF:** Casos resueltos con *«Ya tienes el boletín guardado»* + botón `DESCARGAR EL BOLETÍN` o aviso ámbar con botón `SUBIR EL PAPEL DEL LABORATORIO` (con acceso a cámara/foto).
   - **Línea normativa oficial:** Incluida íntegramente al pie antes de las acciones.

3. **Ergonomía táctil para el campo:**
   - Botón principal **`APUNTAR UN ANÁLISIS`** con altura superior a 96 px y ancho completo para evitar cualquier fallo incluso con guantes.
   - Botones de acción secundaria y de retorno con más de 64 px de altura mínima y separación de seguridad.