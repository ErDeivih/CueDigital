He diseñado la pantalla móvil **«Lo que he entendido»** para **CUE Digital**, adaptada al milímetro a las necesidades de un agricultor de Castilla y León que la utiliza de pie en la tierra, al sol, con una mano y sin cobertura:

### Decisiones de diseño clave implementadas:
1. **Tipografía y visibilidad al sol:**
   - Letra base de **18 px a 26 px** con tipografía del sistema (`system-ui`), asegurando legibilidad inmediata sin forzar la vista bajo el sol.
   - Contraste plano de alto impacto (fondos limpios, sin degradados ni sombras que se emborronen con el polvo o el brillo solar).
   - Acceso directo superior a **«A+ Letra»** para agrandar el tamaño del texto con un solo toque.

2. **Estructura en dos partes (pregunta y lo entendido):**
   - Preguntas clásicas de campo: *«¿Qué has hecho?»*, *«¿Dónde?»*, *«¿Cuándo?»*, *«¿Qué producto has echado?»* y *«¿Cuánto por hectárea?»*.
   - Cada dato extraído va acompañado de su frase explicativa clara (*«Fungicida de hoja. Tienes 32 kilos guardados en el almacén»*, dosis legal autorizada, etc.).

3. **Sin pérdida de información («Esto lo he oído pero no sé dónde ponerlo»):**
   - Sección dedicada para fragmentos que la voz captó (como *«...con el tractor nuevo»*), evitando que el agricultor sienta que el programa ha descartado parte de lo dicho.

4. **Preguntas pendientes claras («Para poder apuntarlo me falta esto:»):**
   - Tarjeta en color ámbar de aviso (`#ffe9a8` con borde `#8a6a00`) que solo pide lo estrictamente exigido por la Junta (litros de la cuba y aplicador con carné), con campos táctiles de más de 64 px de altura e `inputmode="decimal"` para activar el teclado numérico.

5. **Manejo de silencios y fallos de voz:**
   - Desplegable explicativo que muestra con total franqueza el mensaje en caso de ruido o viento: *«No he entendido nada de lo que has dicho. Prueba a decírmelo de otra forma, o rellénalo a mano: se tarda un minuto.»*

6. **Interacción y botones inferiores:**
   - Botón principal **«ESTÁ BIEN, APUNTARLO»** en verde de 68 px de alto, diseñado para pulsarse sin fallar con una sola mano o guante.
   - Botón secundario **«CORREGIRLO A MANO»** en blanco con borde verde oscuro para normalizar la corrección sin penalizar la experiencia.
   - Total ausencia de pestañas inferiores, menús flotantes o jerga técnica. Iconos vectoriales SVG limpios.