He diseñado la pantalla de escritorio (1440×900) **«Productos y máquinas»** de **CUE Digital Despacho**, adaptada a las necesidades del agricultor trabajando sentado con teclado y ratón:

### Decisiones de diseño implementadas:
1. **Armazón oficial de escritorio (1440×900)**:
   - **Barra superior fijada**: con el identificador de la explotación (`Las Suertes y El Prado`), la campaña activa 2026, el estado oficial `SIEX / REGEPA: AL DÍA`, titular acreditado y los accesos rápidos a «+ NUEVA FICHA» y «Sincronizar SIEX».
   - **Menú lateral de módulos**: con el ítem **«Productos y máquinas»** activo en verde oscuro institucional con su contador de fichas (29), manteniendo la navegación coherente con los módulos existentes del ERP (Tierras, Cuaderno, Almacén, Análisis, Facturas...).
   - **Pie de estado continuo**: con atajos de teclado (`[Ctrl+F]`, `[N]`, `[F5]`, `[Esc]`), estado de conectividad local SQLite y sincronización con los servidores de la Junta de Castilla y León. Sin barras de pestañas móviles abajo.

2. **Organización por bloques y catálogos maestros**:
   - Cabecera de módulo con resumen de fichas en regla (29 activas repartidas en 6 catálogos) y acciones de descarga oficial en PDF y Excel.
   - Pestañas horizontales de navegación rápida entre los 6 tipos de fichas:
     1. **Productos fitosanitarios** (8 fichas): *Producto*, *Nº de registro MAPA*, *Materia activa / Formulación*, *Dosis máxima* (alineada a la derecha con unidad) y *Días de espera* oficiales.
     2. **Abonos y enmiendas** (5 fichas): *Abono*, *Riqueza N*, *Riqueza P*, *Riqueza K*, *Tipo y Destino agronómico*.
     3. **Quién aplica (Personal)** (3 fichas): *Nombre*, *NIF*, *Carné de aplicador* (básico/cualificado y fecha de vigencia), *Teléfono*.
     4. **Quién asesora (Técnicos)** (2 fichas): *Asesor / Entidad*, *ROPO / NIF*, *Especialidad técnica*.
     5. **Máquinas y equipos** (6 fichas): *Máquina*, *Tipo*, *Nº de serie / Matrícula / ROMA*, *Inspección ITEAF*.
     6. **Naves e instalaciones** (4 fichas): *Nave*, *Tipo de instalación*, *Superficie* (en m² a la derecha), *Ubicación*.

3. **Criterios de ergonomía de despacho y fidelidad técnica**:
   - Botones compactos (32–36 px de alto) en cada fila con acciones específicas independientes («Editar» y «Borrar»), sin hacer que toda la fila sea clicable.
   - Cada bloque incorpora en su cabecera fija su propio botón primario de alta («+ AÑADIR PRODUCTO», «+ AÑADIR ABONO», etc.).
   - Datos numéricos rigurosamente alineados a la derecha con su unidad (`kg/ha`, `L/ha`, `días`, `%`, `m²`).
   - Sin datos ficticios: los campos no aplicables o no documentados se indican con guion largo («—») o se dejan en blanco.
   - Contraste plano sin sombras ni degradados, con bordes nítidos de separación acordes al contrato de diseño de CUE Digital.