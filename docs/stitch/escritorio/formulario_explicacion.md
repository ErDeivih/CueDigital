He diseñado la pantalla de despacho en resolución 1440×900 para **«Apuntar lo que he echado»** (Apuntar lo que he echado - CUE Gestión Despacho (1440x900)), adaptada a la operativa ágil con teclado y ratón sin perder los principios de claridad y rigor técnico del CUE Digital de Castilla y León.

### Decisiones de diseño implementadas:

1. **Armazón ERP y continuidad de escritorio**:
   - Barra superior fija con acceso a la finca activa (*Finca Las Suertes y El Prado*), selector de campaña 2026, titular cualificado y estado de conexión local/SIEX.
   - Navegación lateral estructurada con todos los módulos de explotación, manteniendo **«El Cuaderno»** activo con su contador correspondiente.
   - Barra de estado inferior técnica con atajos de teclado (`[Ctrl+S]` para Guardar, `[Esc]` para Cancelar) y sincronización con REGEPA.

2. **Formulario en dos columnas (Panel central)**:
   - **Columna izquierda (Entrada directa de datos)**:
     - *¿Dónde lo has echado?*: Lista de tierras de la finca con buscador en cabecera y selección visual directa con radio y estado de la parcela (*El Prado* seleccionada).
     - *¿Qué has echado?*: Selector de productos del almacén con visualización inmediata del número de registro oficial (*18.940 / ES-00421*), materia activa y stock disponible.
     - *¿Cuánto por hectárea?*: Campo numérico con unidad `L/ha` y validación de dosis legal autorizada.
     - *¿Cuándo?*: Selector de fecha con atajos directos de un clic.
   - **Columna derecha (Datos derivados y trazabilidad oficial)**:
     - *¿Cuántas hectáreas has tratado?*: Autocompletado de la superficie total (*4,90 ha*), editable para orillas o tratamientos parciales.
     - *¿Por qué lo has echado?*: Motivo o plaga registrada.
     - *¿Quién lo aplica y qué máquina?*: Selector de aplicador homologado con carné cualificado y máquina registrada en el ROMA con ITEAF en vigor, junto con el volumen de caldo calculado.
     - *Gestión Integrada de Plagas (GIP)*: Medidas preventivas previas marcadas según normativa.

3. **Panel lateral derecho de resumen en vivo**:
   - Resumen instantáneo de los totales del tratamiento (*9,80 L de gasto total*).
   - **Cálculo reglamentario del plazo de seguridad**: Tarjeta destacada en ámbar de alto contraste con la fecha límite exacta (*«Hasta aquí no puedes cosechar: 26/05/2026 - 14 días de espera»*).
   - **Cuadratura en tiempo real con el almacén**: Control automático de entradas frente a salidas (*10,00 L disponibles - 9,80 L gastados = 0,20 L restantes*) que previene descuadres antes de fijar el apunte oficial.

4. **Fidelidad al sistema de diseño CUE Digital**:
   - Cero sombras ni degradados; contraste garantizado mediante bordes estructurales limpios.
   - Tipografía accesible sin adornos e iconografía SVG técnica para cada función.