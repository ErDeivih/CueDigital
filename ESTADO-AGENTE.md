titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital ya tiene las pantallas que pidió David tras ver el diseño. en «Mis parcelas», al pinchar una tierra se abre su ficha con el mapa del contorno, lo que se ha hecho hoy sobre ella y su historial por años (siembra, labores, tratamientos, abonos con kg/ha y su mes, cosecha en kg/ha). Hay calendario con el trabajo de cada día, filtros por tipo de trabajo con tierras y cantidades (trazabilidad de la explotación) y una pantalla de facturas que hace fotos, las lee, enseña la propuesta para corregirla y la guarda; si no entiende la foto, lo dice y deja escribirla a mano. En paralelo, el SIGPAC ya devuelve la ortofoto con el contorno de cada parcela dibujado. El apuntar del día a día sigue en la app vieja: es lo siguiente.
estado: en-curso
tarea: implementadas las seis cosas que pidió David (facturas con fotos, tierra primero, historial, calendario, filtros por tipo y contornos del SIGPAC)
nivel: 2
siguiente: el apuntar de 30 segundos en la app nueva (con la puerta del apero que hoy falta) y las pantallas propias de PAC, gastos y facturas detalladas
bloqueado: nada duro; siguen pendientes de terceros las licencias (CIT, IGN), los formatos del expediente y del Cuecyl antiguo, y los presupuestos de PSD2
fecha: 2026-11-05

## Lo que se ha hecho en esta ronda

David vio el diseño, le gustó y pidió, por este orden: facturas con fotos, tierra primero, historial,
calendario, filtros y la integración del SIGPAC con los contornos. Todo está en `/nuevo/` y
**verificado en Chrome a 390, 1024 y 1440 px con 0 fallos**:

1. **Facturas con fotos.** Botón grande de cámara y «elegir archivo»; **varias fotos** por factura
   (factura, envase, albarán) con vista previa y quitar; «Leer la factura» llama al lector del
   servidor; se enseña la **propuesta campo a campo para revisar y corregir** y se guarda; las fotos
   de más se guardan como documentos. Si el lector no está o no entiende la foto, **lo dice y abre la
   factura a mano**: nunca se inventa un dato.
2. **Tierra primero.** Al pinchar una tierra, su ficha con el **trabajo de hoy** sobre ella (o «hoy no
   hay nada apuntado»), sus datos del SIGPAC y del cultivo, y el mapa de la parcela.
3. **Historial de la tierra**, por campañas y sin rellenar años vacíos: siembra (cultivo, variedad,
   **dosis de semilla kg/ha**), labores (arado —el «vertedera» del vocabulario del programa—,
   cultivador, grada, siembra…), tratamientos (producto y dosis), **abonos con kg/ha y el mes** y
   cosecha en **kg/ha**.
4. **Calendario**: rejilla del mes con los días que tienen trabajo (número + palabra), el día elegido
   con sus trabajos y su tierra, y navegación de mes.
5. **Filtros por tipo de trabajo**: cada tipo con su cuenta; al elegir, las tierras con municipio,
   hectáreas y cantidad o por hectárea, y el resumen de n y hectáreas. Trazabilidad de la explotación.
6. **Contornos del SIGPAC**: `GET /api/mapa/tierra/{id}.png` devuelve la **ortofoto del IGN con el
   contorno dibujado** (relleno suave, línea blanca con borde oscuro, margen del 15 %, 800×600 en unos
   2 s); la ficha la enseña. Si la tierra no tiene forma, **se dice** en vez de dibujar un cuadro.

**Lo que la app vieja sigue haciendo** (y no se rompe): el alta del apunte del día a día, la PAC, el
detalle de gastos y facturas y los ajustes. El armazón nuevo enlaza a ella en esos sitios.

**Un hueco encontrado y apuntado**: `POST /api/labores` **no acepta el apero (`subtipo`)**; el dato
solo entra por `detalles`. Es un campo con columna y sin puerta, la familia de fallo que el proyecto ya
pagó; se arregla al hacer el apuntar nuevo. Y «vertedera» no existe en el vocabulario: el equivalente
es «arado», y no se ha traducido una palabra en la otra (decide David si se renombra).

## La última pasada, sobre este mismo HEAD

    Python       5814 recogidas · 5812 superadas, 2 omitidas, 0 fallos
    JavaScript   1270 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, alta/importación, ficha, calendario, filtros y factura   0 fallos
    capturas                                           12 en docs/capturas-nuevo/

## Lo que sigue abierto

- **Apuntar en 30 segundos en la app nueva** (el alta del apunte, con su puerta de apero) y retirar la
  pantalla vieja cuando cubra el recorrido.
- **Pantallas propias de PAC**, gastos y facturas detalladas (hoy son enlaces a la app vieja).
- **PAC de años anteriores** y recintos por campaña de la Junta.
- **PSD2**: dos presupuestos y aprobación del gasto; sin código hasta que haya contrato.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
