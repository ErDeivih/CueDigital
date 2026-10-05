He diseñado la pantalla de escritorio (1440×900) **«Mis facturas»** para el módulo de Gestión de Despacho de **CUE Digital CyL**, optimizada específicamente para el trabajo ágil con teclado y ratón sin perder la sencillez ni el rigor normativo agrario:

### Decisiones de diseño y arquitectura de información:
1. **Armazón de Despacho (Desktop Shell):**
   - **Barra superior corporativa:** Muestra la explotación activa (*Finca Las Suertes y El Prado 187,42 ha*), campaña 2026, estado de sincronización con SIEX/REGEPA al día, titular y el botón de acción rápida `+ AÑADIR UNA FACTURA`.
   - **Navegación lateral de despacho:** Módulo **«Facturas y Albaranes»** seleccionado como activo, manteniendo visible todo el mapa del cuaderno para el técnico/agricultor.
   - **Barra de estado inferior:** Diagnóstico del sistema local y atajos de teclado (`Ctrl+F`, `N` para nueva factura, firma digital activa). Sin barra de pestañas móvil.

2. **Panel de control y métricas de campaña:**
   - Resumen superior compacto con KPIs directos: número de facturas activas, desglose de base imponible e IVA, importe total acumulado y **alerta de inspección** preventiva (`1 pendiente: Falta el papel`).

3. **Tabla de gestión de facturas:**
   - **Columnas ordenables:** *Fecha*, *Quién te lo vendió* (con NIF y desglose del producto), *Nº de factura*, *Base*, *IVA*, *Total* (con importes tabulares alineados a la derecha en `€` y dos decimales), *El papel* y *Acciones*.
   - **Tratamiento estricto de datos desconocidos:** Tal como establece la norma de diseño, los importes no desglosados no se falsean con ceros, sino que se indican con raya (`—`).
   - **Control visual documental («El papel»):** Las facturas con justificante cuentan con indicador claro (`Con el papel subido`), mientras que las pendientes destacan con **etiqueta en ámbar `Falta el papel`**, prioritario para cualquier inspección de campo de la Junta o justificación PAC.
   - **Acciones compactas (32–40 px):** Botón contextual directo (*«Subir papel»* o *«Ver papel»*), *«Editar»* y *«Borrar»* (en rojo de peligro sobrio).

4. **Aviso del asistente de lectura:**
   - Recuadro explicativo al pie confirmando que el lector automático de facturas opera en español y siempre requerirá confirmación previa del titular antes de alterar cualquier asiento del almacén o del cuaderno.