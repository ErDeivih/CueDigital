He diseñado la pantalla móvil de **«Dímelo con la voz»** para **CUE Digital**, adaptada al diseño de campo de Castilla y León y respetando todas tus directrices:

### Decisiones de diseño aplicadas:
1. **Ergonomía de campo y legibilidad al sol:**
   - Tipografía base a **18 px** (con botón `A+ Letra` en cabecera para subir a 22 px sin descolocar la pantalla).
   - Paleta de alto contraste sin sombras, sin transparencias ni degradados, con bordes gruesos de **3 px** (`#0d2b18` y `#a9b6a8`) para separar planos visiblemente a plena luz solar.
   - Botón principal de hablar con **104 px de altura** y botones de acción de **más de 64 px**, fáciles de pulsar con una sola mano o guantes.

2. **Explicación clara del trato:**
   - Tarjeta inicial con mensaje tranquilizador: *«Cuéntame lo que has hecho con tus palabras»*.
   - Garantía en recuadro ámbar: *«Trato claro: Lo que la máquina no entienda se queda en blanco. Nada se apunta en tu cuaderno sin que tú lo veas primero en pantalla»*.

3. **El botón interactivo de hablar:**
   - **Icono dibujado en SVG puro** (sin emojis ni fuentes externas).
   - Estado inicial: **«HABLAR»** con subtítulo *«Toca aquí y cuéntamelo con tus palabras»*.
   - Estado de escucha activo: se transforma en **«PARAR»** (con icono de detener) y mensaje explicativo: *«Te escucho… di lo que has hecho y pulsa PARAR»*.

4. **Lectura, edición manual y contingencias:**
   - Área editable destacada: **«Escribe lo que has hecho»** con subtítulo aclaratorio para retocar con el dedo o escribir con teclado.
   - Ejemplo real en bloque secundario: *«Por ejemplo: hoy he echado dos litros en el prado, había pulgón»* (con botón para copiarlo directamente).
   - Mensajes específicos para navegador sin soporte (*«Este navegador no sabe escuchar. Escribe lo que has hecho y lo entiendo igual»*) y cuando no hay audio detectado (*«No he oído nada. Prueba otra vez, o escríbelo»*).

5. **Navegación limpia:**
   - **Sin pestañas inferiores ni menús hamburguesa escondidos**.
   - Botones al pie: **«ENTENDERLO»** como acción principal para procesar y **«VOLVER»** para salir sin guardar cambios.
   - Barra auxiliar de simulación para verificar los 4 estados (*Escuchando*, *No ha oído*, *Sin soporte*, *Normal*).