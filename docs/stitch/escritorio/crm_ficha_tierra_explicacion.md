He creado la pantalla de escritorio (1440x900) para la **Ficha Integral de Tierra** («El Prado») de **CUE Gestión Despacho**, respetando de manera estricta todas las especificaciones y el contrato visual de diseño:

### Decisiones de diseño y cumplimiento de reglas:
1. **Estricta ausencia de sombras, degradados o animaciones:** Toda la jerarquía se resuelve mediante bordes definidos (2 a 4 px), contrastes de color planos (verde bosque, blanco, ámbar claro, rojo de error y gris verdoso) y tipografía de sistema (`system-ui` / mono).
2. **Navegación e integración con el Despacho:**
   - Módulo **«Tierras y mapa»** activo en el menú lateral.
   - Miga de pan de procedencia (`Tierras y mapa / El Prado`) con botón de retorno que **conserva los filtros** de la tabla de origen (municipio y recintos).
   - Barra superior oficial con selector de finca activa, campaña 2026, estado de conexión SIEX y firma digital.
3. **Resumen fijo (Sticky Header):**
   - Nombre de la tierra («El Prado»), municipio (Villalar de los Comuneros), polígono 503, parcela 51, recinto 1 y referencia catastral.
   - Comparativa de superficie gestionada vs. declarada (4,90 ha) con indicador de descuadre en 0,00 ha.
   - Forma SIGPAC vectorial sin capas pesadas ni dependencias de conexión.
   - Tarjeta destacada de **Próximo trabajo previsto** («Cosecha de Cebada Cervecera», claramente diferenciada de los trabajos ya ejecutados).
   - Botonera principal compacta para ratón: «REGISTRAR TRATAMIENTO O LABOR», «PLANIFICAR», «EDITAR TIERRA» y «VER EN EL MAPA».
4. **Secciones estructuradas con contador exacto:**
   - **Historia de labores y tratamientos (5 eventos):** Tabla ordenable con fecha, tipo de labor, detalle, máquina/persona, hectáreas tratadas y estado oficial. Cada fila dispone de acciones individuales a la derecha («Abrir ficha», «Editar») y no es un botón global. Se aplica la distinción «una labor no es un cultivo» y «previsto ≠ hecho».
   - **Cultivos y rotación multianual (4 campañas):** Histórico de 2023 (barbecho), 2024 (trigo blando), 2025 (cebada cervecera) y 2026 actual (cebada cervecera RGT Planet).
   - **Cuentas y costes de la parcela:** Desglose con dos decimales y €, identificando pagos completos, pagos parciales (50 %) e **importes sin asignar / pendientes** con «—» (sin inventar ceros ni beneficios).
   - **Productos y balance nutricional:** Control de unidades de Nitrógeno (N), Fósforo (P) y Potasio (K) vinculados al boletín oficial de laboratorio.
   - **Papeles y Documentos (3 archivos vinculados):** Contrato de arrendamiento, boletín analítico y etiqueta oficial de semilla certificada.
   - **Compromisos PAC:** Cumplimiento de rotación P3 y mantenimiento de ribazos BCAM 8.
   - **Aviso de maquinaria:** Alerta técnica sobre la cuba con ITEAF vencida para evitar no conformidades en inspección.
5. **Muestrario de los 5 estados técnicos exigidos:** Vacío (sin labores previas), sin resultados por filtro, cargando datos de SIGPAC, error de servicio SIEX y conflicto por superficie solapada con alegación.