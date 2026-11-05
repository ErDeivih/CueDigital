titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital ya cierra el bucle que pidió David: en «Mis parcelas» se pincha una tierra y se ve su ficha con la ortofoto y el contorno, el trabajo de hoy y el historial por años; desde esa misma ficha se apunta el trabajo del día con su apero (arado, cultivador, grada, rodillo, fresadora u otro), y se guarda de verdad. El calendario enseña el trabajo de cada día, los filtros por tipo dan tierras y cantidades para la trazabilidad, las facturas se hacen con fotos y se revisan antes de guardar, y cada tierra lleva su miniatura del contorno. Falta llevar a la app nueva los tratamientos, abonos, siembra y cosecha del día a día, y las pantallas propias de PAC y gastos.
estado: en-curso
tarea: implementado el apuntar del trabajo del día desde la tierra (con la puerta del apero abierta), las miniaturas del contorno y el resto del bucle tierra → historial → calendario → filtros → facturas
nivel: 2
siguiente: tratamientos, abonos, siembra y cosecha desde la app nueva (con la cola sin cobertura) y las pantallas de PAC y gastos
bloqueado: nada duro; siguen pendientes de terceros las licencias (CIT, IGN), los formatos del expediente y del Cuecyl antiguo, y los presupuestos de PSD2
fecha: 2026-11-05

## Lo que se ha hecho en esta ronda

El bucle que pidió David está completo en `/nuevo/` y verificado en Chrome a 390, 1024 y 1440 px:

1. **Tierra primero**: al pinchar una tierra se abre su ficha con la **ortofoto y el contorno**, los
   datos del SIGPAC y del cultivo, **«Hoy en esta tierra»** y el **historial por campañas** (siembra
   kg/ha, labores, tratamientos, abonos kg/ha y mes, cosecha kg/ha).
2. **El trabajo del día se apunta desde la tierra** (lo nuevo de esta ronda): botón «Apuntar un
   trabajo» en la ficha y destino «Apuntar» en la barra del móvil y en la lateral. Se elige el
   **apero del vocabulario del servidor**, la fecha de hoy y las hectáreas de la tierra; se guarda y
   la ficha se refresca. **Verificado en Chrome y en la API**: el apunte queda en la base con su
   apero y la pantalla lo dice (0 fallos).
3. **La puerta del apero, abierta**: `POST /api/labores` acepta el `subtipo` (rodillo, cultivador,
   arado, grada, fresadora, otro), lo valida contra el catálogo (un apero inventado contesta **422
   con la lista de los que valen**) y lo guarda en su columna; `GET /api/labores` ya lo devuelve.
   El apero no es obligatorio, para no romper a la app vieja, y lo que ya estaba en `detalles` se
   sigue leyendo.
4. **Calendario** con el trabajo de cada día, **filtros por tipo** con tierras, municipio, hectáreas
   y cantidades, y **facturas con fotos** (cámara, varias fotos, lectura, propuesta corregible,
   guardado y «a mano» si no se lee).
5. **El contorno se ve también al elegir tierra**: miniatura en cada fila de «Mis parcelas» y de la
   lista de apuntar, y botón «Guardar la imagen» en la ficha.
6. **«Vertedera» se llama «arado»** en el vocabulario del programa y no se ha traducido una palabra
   en la otra (sería inventar). David decide si se renombra la etiqueta; aparece sola en las tres
   puertas.

**Lo que sigue en la app vieja**: tratamientos, abonos, siembra y cosecha del día a día (el trabajo
de suelo ya está), la cola sin cobertura, PAC, gastos y facturas detalladas, y los ajustes.

## La última pasada, sobre este mismo HEAD

    Python       5832 recogidas · 5830 superadas, 2 omitidas, 0 fallos
    JavaScript   1276 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, apuntar, ficha, calendario, filtros y factura   0 fallos
    capturas                                            13 en docs/capturas-nuevo/

## Lo que sigue abierto

- **El resto del apuntar**: tratamientos, abonos, siembra y cosecha desde la app nueva, y la **cola sin
  cobertura** (guardar en el móvil y que llegue solo).
- **PAC de años anteriores** y recintos por campaña de la Junta; las pantallas propias de PAC y gastos.
- **PSD2**: dos presupuestos y aprobación del gasto; sin código hasta que haya contrato.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
