He diseñado la pantalla principal **«Inicio de Gestión» (1440×900)** para el modo despacho de **CUE Digital CyL**, respetando escrupulosamente los principios de diseño y las reglas operativas de la explotación:

### 1. Navegación persistente y cabecera de despacho
- **Barra superior persistente:** incluye el selector de finca activa (*«Las Suertes y El Prado · 187,42 ha»*), el **selector directo de campaña (2026 activa, con alternancia histórica 2024–2026)**, el estado oficial con SIEX/REGEPA al día, la **búsqueda global universal** con atajo (`Ctrl+K` para buscar parcelas, referencias SIGPAC, contactos, productos, facturas o aperos), el botón directo de añadir y el avisador de pendientes personales.
- **Menú lateral de despacho (fijo):** con todos los módulos de gestión, badges numéricos reales (24 apuntes, 64 tierras, 10 sin cultivo, 1 máquina vencida, etc.) y resalte activo con borde de foco de alto contraste. En el pie se visualiza el estado de la base de datos local SQLite y atajos de teclado.

### 2. Las Tres Zonas de Control Diario
1. **Pendientes que requieren acción inmediata:**
   - **10 tierras sin cultivo declarado** con botón directo `VERLAS Y ASIGNAR`.
   - **4 trabajos previstos esta semana** con acceso directo `VER LA AGENDA`.
   - **3 documentos por revisar** (albaranes y boletines pendientes de cotejo) con botón `REVISAR DOCUMENTOS`.
   - **2 cobros de cosecha vencidos (1.240,00 €)** con enlace directo a liquidaciones.
   - **1 pago vencido a proveedor (380,50 €)** con aviso explícito de pago parcial registrado.
   - **1 inspección ITEAF de maquinaria vencida** (Cuba Aguirre 600L bloqueante para tratamientos en SIEX).
   *Todas las cifras grandes actúan como enlace filtrado directo.*

2. **Resumen oficial de la campaña con fecha de corte y cautelas de cálculo:**
   - **187,42 ha** de superficie gestionada total frente a **154,20 ha** con cultivo declarado (destacando las 33,22 ha restantes).
   - **62,40 ha** de área trabajada acumulada.
   - **8.420,00 €** en ventas de cereal con la leyenda obligatoria **«con los importes registrados»**.
   - **3.014,00 €** en compras, advirtiendo explícitamente que existe 1 factura con importe pendiente («—»), sin inventar totales ni márgenes ficticios.
   - Conteo riguroso de registros incompletos: **13 fichas** (10 sin cultivo + 3 parcelas sin geometría SIGPAC).

3. **Agenda técnica y control documental:**
   - Tabla de próximos trabajos de campo con nombres reales y largos (ej. *«501/10015-1 VEZA VELLOSA»*, *«Las Suertes de Arriba (parcela 12)»*), fecha, máquina, persona y columna fija de acciones (`Ver ficha` / `Editar`).
   - Panel de documentos pendientes de vincular/cotejar.
   - Franja inferior para trámites y emisión oficial de cuadernos e informes.
   - Aviso de esquina discreto indicando los datos pendientes de completar.

### 3. Rigor técnico y visual
- Cero sombras, cero degradados, cero transparencias y cero animaciones.
- Iconografía técnica SVG pura.
- Botones compactos (32–40 px) adaptados al uso ágil con ratón y teclado, manteniendo textos de tabla y cabeceras con alto contraste para trabajo de despacho.