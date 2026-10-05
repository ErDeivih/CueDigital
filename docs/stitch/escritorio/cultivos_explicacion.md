He diseñado la pantalla de escritorio para despacho (1440x900) del módulo **«Qué hay sembrado: cultivos de campaña por parcela»** (Qué hay sembrado - CUE Gestión Despacho (1440x900)), siguiendo fielmente las especificaciones de ergonomía para ratón y teclado, sin sombras ni degradados, con iconos vectoriales SVG y alineada con el contrato visual y las pantallas de gestión ya existentes:

### Decisiones de diseño implementadas:
1. **Armazón de Despacho (1440x900)**:
   - **Barra superior**: Identificador de *CUE Digital CyL Despacho*, selectores de finca activa (*Finca Las Suertes y El Prado, 187,42 ha*), campaña 2026, estado de sincronización oficial *SIEX / REGEPA al día* y acceso a nuevo apunte o asignación.
   - **Menú lateral de módulos**: Módulo **«Qué hay sembrado»** destacado en estado activo con fondo verde oscuro de contraste, junto al resto de módulos (Cuaderno, Tierras, Almacén, Análisis, Plan de abono, etc.).
   - **Barra de estado inferior**: Datos de conexión local/nube, normativa RD 1054/2022 y atajos de teclado para agilizar la jornada de oficina.

2. **Aviso superior de pendientes**:
   - Bloque en tono ámbar de alta visibilidad: *«A 10 parcelas les falta decir qué tienen este año»*, explicando la repercusión directa en las inspecciones y validaciones PAC, junto con el botón de filtrado rápido *«Ver solo las 10 que faltan»*.

3. **Tabla densa de 64 tierras (optimizada para ratón)**:
   - **Cabecera fija (sticky)** con ordenación por columnas.
   - **Columnas**:
     - *Tierra / Parcela*: Nombre tradicional, término municipal y régimen (Secano/Regadío).
     - *Ref. SIGPAC*: Código catastral canónico.
     - *Hectáreas*: Alineadas a la derecha con dos decimales y unidad `ha` (ej. `12,30 ha`).
     - *Este año hay (2026)*: Cultivo y variedad declarada en negrita nítida; o aviso en rojo/ámbar *«Sin cultivo asignado»* para las pendientes.
     - *Alerta de rotación*: Indicador visible *«Repite lo del año pasado (consume suelo)»* cuando coincide con el cultivo anterior, para prevenir problemas agronómicos o de condicionalidad reforzada.
     - *Otros años (histórico)*: Detalle de las dos últimas campañas en tipografía compacta (ej. `2025: Girasol · 2024: Cebada cervecera`).
     - *Estado*: Etiquetas nítidas *«Al día»* (verde) o *«Falta rellenar»* (ámbar).
     - *Acciones*: Botones compactos (32–36 px) dedicados: **«DECIRLO»** destacado en las pendientes y **«CAMBIARLO»** en las ya cumplimentadas.

4. **Pie de tabla y pedagogía para el agricultor**:
   - Contador de balance: *«64 parcelas en campaña 2026 (54 al día, 10 faltan)»*.
   - Bloque explicativo inferior con los 3 motivos prácticos de cumplimentar el cultivo (ahorro al apuntar tratamientos, control de rotaciones/ecorregímenes y validación automática de fechas).
   - Ausencia total de barras móviles inferiores o elementos táctiles sobredimensionados innecesarios.