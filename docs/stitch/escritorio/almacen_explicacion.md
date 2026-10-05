He diseñado la aplicación web de gestión para escritorio en resolución 1440×900: **«El almacén - CUE Gestión Despacho»** (El almacén - CUE Gestión Despacho (1440x900)), adaptada específicamente para el trabajo de despacho del agricultor con teclado y ratón.

### Decisiones de diseño y cumplimiento de requisitos:
1. **Armazón ERP de despacho**:
   - Barra superior fija en verde oscuro oficial (`#1f4a2c`) con identificador de la explotación («Finca Las Suertes y El Prado · 42 ha»), selector de campaña activa («2026») y acciones rápidas («Imprimir Informe Oficial» y «+ Nueva Factura o Albarán»).
   - Menú lateral izquierdo con todos los módulos de la explotación, destacando **«El Almacén»** como módulo activo con insignia en amarillo señalizador.
   - Sin barra de pestañas inferior (prohibida expresamente para escritorio).

2. **Tarjetas de números clave**:
   - **Producto comprado**: `1.240,00 L/kg` (en 4 facturas).
   - **Producto echado**: `860,50 L/kg` (en 6 tratamientos en campo).
   - **Te queda en la nave**: `379,50 L/kg` (con estado de stock activo suficiente).
   - **Gasto del año**: `2.410,80 €` (IVA desglosado).

3. **Tabla de Existencias y Cuadraturas**:
   - Columnas ordenables: *Producto*, *Nº de registro*, *Comprado*, *Echado*, *Te queda*, *Gasto*, *Estado* y *Acciones*.
   - Botonería compacta de 28-32 px de alto para uso ágil de ratón.
   - Alineación numérica estricta a la derecha con fuentes monoespaciadas y unidades exactas.
   - **Tratamiento de descuadres reales**: En *Glifosato 36% SL*, el stock negativo (`-4,70 L`) se muestra en fondo rojo claro con el aviso textual obligatorio: *«Has echado más de lo que has comprado»*. En *Aminoácidos con Boro*, al diferir las unidades entre compra (litros) y aplicación (kilos), se indica de forma explícita *«No se puede comparar»* evitando ceros ficticios.

4. **Panel lateral derecho del producto seleccionado**:
   - Muestra la ficha técnica de *Tebuconazol 25% WG*, su número de registro oficial (24.156), lote de etiqueta, dosis legal máxima y el **plazo de seguridad obligatorio** (35 días para cosecha).
   - Registro cronológico detallado de entradas y salidas renglón por renglón con fecha, procedencia de factura o parcela tratada, y cantidad.

5. **Tabla de facturas vinculadas del año**:
   - Desglose con fecha, proveedor, número de factura, base imponible, cuota de IVA, total y estado del papel digitalizado (PDF o foto pendiente). Para facturas con datos incompletos se representan con guion («—») sin inventar cifras.