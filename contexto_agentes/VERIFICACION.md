# Verificación independiente del 11/10/2026

Revisor: Codex. Destino revisado: `F:\EspacioCodigo\CueDigital`.
Último commit observado: `8c3a45a`; árbol limpio antes de la revisión.
No se ha modificado el código del CRM ni ejecutado su suite completa en esta revisión.

## Ejecutado y observado

- Reenvíos de factura, migración y ficha: **33 pruebas**, salida 0. Ejecución desde backend:
  `..\.venv\Scripts\python.exe -m pytest tests/test_la_factura_reenviada_no_se_duplica.py tests/test_la_migracion_del_reenvio.py tests/test_la_ficha_de_la_compra.py -q`.
  conftest selecciona base temporal. Avisos de deprecación, no fallos.
- Laboratorio: `run-smoke-tests.ps1`, **6 comprobaciones, 0 fallos, salida 0**.
  Versionado, proveedores, JS sintético, proyección resumen, .NET y recursos PE.
  **No ejecutada la prueba nativa**: que Ghidra aparezca disponible no acredita su análisis real hoy.
- Vistas de compra inspeccionadas visualmente: `docs/capturas/compra-escritorio.png`,
  `compra-escritorio-1024.png`, `compra-movil.png`.
  Se ven los cuatro indicadores, tabla de líneas y cifras con coma/moneda.
- Base real consultada únicamente para tamaño/huella:
  1.302.528 bytes; SHA-256 `CC65753395EF33B3E15679BB74EA77A706DD8557615486CEB709F73F12334B12`.
  Coincide con la huella aportada. No se han escrito datos del agricultor.

Las suites completas **4746 / 1081**, el recorrido **49** y el navegador **44** son resultados
aportados por DeepSeek, no repetidos por este revisor. Mantener esta distinción.

## Hallazgos del cierre

1. **Barra de escritorio cortada en la captura.** `APUNTAR` queda parcialmente fuera y no se ven
   las acciones del extremo derecho. En `comprobar_la_ficha_de_la_compra_en_el_navegador.py`,
   `visible` exige tamaño/estilos pero no contención dentro de viewport ni ancestros que recortan.
   Contar cuatro cajas existentes no acredita cuatro controles utilizables. CRM-00 lo corrige.
2. **Resumen actual desactualizado.** La tabla de §0 del contrato aún dice **4736 / 1080** mientras
   README/AGENTS y la entrega dicen **4746 / 1081**. No confundir las cifras históricas con esa tabla.
3. **Compatibilidad PostgreSQL pendiente.** No declararla verificada. La migración nueva contiene
   SQL `anulada = 0`: revisar la portabilidad con booleanos reales antes de activar ese motor.
4. **Migración de huellas históricas.** Se calcula con el contenido actual, que puede ser ya corregido.
   No describirla como prueba recuperada del comando original. Añadir caso legado corregido y explicitar
   qué reenvíos pueden verificarse y cuáles requieren revisión; no inventar la petición perdida.

## Kit REA: qué sirve y qué falta para este destino

El kit existe y aporta metodología, plantillas y referencias. No es una evaluación ya hecha de
competidores agrarios. Sus prioridades globales conducen a RadioPV/facylf y su ESTADO contiene fechas
12/10/2026, posteriores a la revisión de hoy. No usarlas como evidencia cronológica.
Las descripciones de apps instaladas son candidatas; una ruta real no prueba la función buscada.
Algunos ejemplos CLI del PLAYBOOK dependen del directorio: el lanzador está en la raíz del sandbox,
no dentro de estudiar-apps. Ejecutar desde la raíz o usar ruta absoluta y help real del comando.
El ejemplo de projection requiere un JSON de entrada válido: no basta con mencionar `vista.json`.
Este perfil no cambia prioridades globales ni instalación REA/DSH.

## Referencias consultadas, con nivel de evidencia

Fecha de consulta: 11/10/2026. **Documentación o presentación oficial, no recorrido de demo.**

- [farmOS: modelo de datos](https://farmos.org/model/): activos, registros y planes.
- [farmOS: activos](https://farmos.org/guide/assets/): relaciones y registros asociados.
- [ERPNext: Payment Entry](https://docs.frappe.io/erpnext/payment-entry): pagos, aplicaciones y anticipos.
- [Odoo 19: finanzas](https://www.odoo.com/documentation/19.0/applications/finance.html): índice de funciones.
- [Odoo 19: compras e inventario](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp.html).
- [AGRIVI: Farm Insights](https://www.agrivi.com/products/360-farm-insights/): planificación, meteo/satélite anunciados.

La página específica de conciliación de Odoo no se pudo abrir con la herramienta en esta revisión.
No atribuirle detalles de interacción no observados. No se han descompilado estas referencias,
no se han abierto sus cuentas ni copiado sus implementaciones. Cada ticket investigará solo lo necesario.
