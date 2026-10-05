He diseñado la pantalla de escritorio (1440×900) para **«El Cuaderno: apuntes de campaña»** en **CUE Gestión Despacho** (El cuaderno: apuntes de campaña - CUE Gestión Despacho (1440x900)), el corazón del programa de gestión para el agricultor cuando está en la oficina con teclado y ratón:

### Decisiones de diseño e implementación:
1. **Armazón ERP y Navegación de Despacho**:
   - Cabecera fija institucional con el selector de finca («Finca Las Suertes y El Prado · 42 ha»), campaña activa («2026»), titular oficial (Manuel Ruiz Gómez, NIF y estado cualificado), botón de «Imprimir Informe Oficial» y acceso directo «+ Nuevo Apunte».
   - Menú lateral izquierdo con todos los módulos de explotación, destacando **«El Cuaderno»** como módulo activo con contador oficial (24 apuntes).
   - Sin barra de pestañas móvil inferior; sustituida por barra de estado del sistema (resolución 1440×900, sincronización local y enlace oficial con SIEX / Junta de Castilla y León).

2. **Franja de Herramientas y Filtros Compactos (32–38 px para ratón)**:
   - Campo de búsqueda en tiempo real sobre productos, parcelas o registros.
   - Desplegable de clase («Todas las clases», «Producto», «Abono», «Trabajo», «Cosecha»).
   - Selectores de fecha «Desde» y «Hasta» para acotar momentos de campaña.
   - Selector específico de parcela/tierra.
   - Casilla de verificación «Sólo firmados» y botón rápido para limpiar filtros.
   - Acciones principales de cabecera: **«+ APUNTAR»** en verde sólido y **«SACAR EN PAPEL»**.

3. **Tabla General de Apuntes por Meses y Estados Normativos**:
   - Columnas ordenables con indicadores visuales SVG: *Fecha*, *Clase*, *Qué (Producto o Trabajo)*, *Tierra*, *Hectáreas* (alineadas a la derecha con su unidad), *Cultivo*, *Firmado* y *Acciones*.
   - Filas agrupadas por mes con franja sutil divisoria (*«Mayo de 2026 · 4 apuntes»*, *«Abril de 2026 · 8 apuntes»*, *«Marzo de 2026 · 12 apuntes»*).
   - Diferenciación de estado normativo:
     - **Apuntes pendientes**: botón «Borrar» habilitado en rojo.
     - **Apuntes firmados electrónicamente**: llevan su sello verde de firmado y el botón de borrado sustituido por **«Anular»** (deshabilitando la destrucción directa del apunte para cumplir con la trazabilidad del Real Decreto 1054/2022).
   - Pie de tabla con datos consolidados: *«24 apuntes registrados en campaña | 62,40 ha tratadas | 22 firmados · 2 pendientes»* y controles de paginación numérica.

4. **Panel Lateral de Detalle (360 px)**:
   - Muestra el apunte seleccionado con su producto en tipografía destacada (*Glifosato 36 SL*).
   - Alerta oficial de plazo de seguridad (*«Hasta aquí no puedes coger la cosecha: 26/05/2026 (14 días de espera)»*).
   - Ficha técnica completa de inspección: referencia SIGPAC, hectáreas tratadas, dosis por hectárea, caldo de agua, aplicador y carné, máquina y número de registro oficial.
   - Bloque de **cuadratura con el almacén** (comprado vs gastado con alerta de desfase si faltan facturas por registrar).
   - Botón destacado de **«CORREGIR ESTE APUNTE»**, «Volver a su sitio» y «Borrar».

5. **Fidelidad al Sistema de Diseño CUE Digital**:
   - Iconografía 100% SVG vectorial (cero emojis).
   - Cero sombras, degradados ni transparencias; estructura delimitada mediante bordes y contraste funcional.
   - Tipografía legible y jerarquizada adaptada a la densidad de datos en monitor de escritorio.