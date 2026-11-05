# WALL — lo que falta para el cuaderno digital del agricultor

> **Copia del bloque 4 de `F:\EspacioCodigo\_flujo-dsh\MAPA-DE-OBJETIVOS.md`** (fuente de verdad).
> Aquí se marca lo que se va cerrando, con la evidencia al lado. **Una casilla solo se marca cuando
> está terminada de punta a punta**, no cuando hay una parte.
>
> **Objetivo final**: la app con la que el agricultor de CyL lleva **el cuaderno de campo digital que
> la Junta exige para 2028**, con sus tierras, sus labores, productos y PAC, y una buena interfaz.
>
> **Terminado cuando**: el agricultor sube su cuaderno y su PAC, ve sus tierras en el mapa y puede
> rellenar el cuaderno digital sin ayuda.
>
> Actualizado: **2026-11-05** (segunda entrega del día).

## Las casillas de David

- [x] **Tierras**: meter una tierra por su código o **eligiéndola en una ventana del SIGPAC**,
      resaltada por color, catalogada y editable.
  - Hecho en `/nuevo/` → «Mis parcelas» → «Añadir tierras»:
    - **Por código**: se pega la referencia del SIGPAC (`37:70:0:0:503:51`) o se escriben los siete
      números; «Buscar» devuelve los recintos con superficie, uso, pendiente y **su dibujo**. Se marcan
      con casilla y «Añadir los marcados» los da de alta en bloque.
    - **Ventana del SIGPAC**: al buscar se abre la ortofoto centrada en los recintos encontrados y
      **cada uno se dibuja resaltado con su color y su etiqueta** (`puntos` del servidor); clic en el
      mapa pregunta al SIGPAC qué recinto hay en ese punto y también se puede añadir.
    - **Catalogada y editable**: el panel de la tierra enseña uso, coeficiente, región, admisibilidad,
      superficie y cultivo, y deja **editar nombre y superficie**; lo del SIGPAC se enseña y no se
      toca (es de la administración). Clic en una tierra → sus datos.
  - **Verificado en Chrome** (390/1024/1440, 0 fallos) con 64 tierras: búsqueda por referencia → 1
    recinto, dibujado en el mapa, marcado y añadido (64 → 65). Captura en
    `docs/capturas-nuevo/alta-y-cuaderno.png`.
  - *Lo que no está verificado*: la búsqueda escribiendo **los nombres** de provincia y municipio
    devolvió 0 recintos en la prueba (la referencia, que es la vía del papel, sí funciona). Queda
    pendiente comprobarlo con la lista de municipios elegida de catálogo.
- [x] Leer el **cuaderno digital de un cliente** (el que él aporte) y **reconocer la parcela
      automáticamente** para dejarla grabada en el mapa.
  - Hecho: «Añadir tierras» → «Traer un cuaderno» sube el **Cuecyl `.xlsx`**, enseña **qué trae**
    (titular, año, tierras del cuaderno) y lo aplica: **reconoce las referencias SIGPAC de cada
    línea**, crea las tierras que faltan y **no duplica** al repetir. Además **rellena los huecos del
    titular** de la finca (nombre, NIF, registro, dirección, localidad, código postal, teléfono,
    correo) sin pisar lo que ya había.
  - **Verificado en Chrome**: subida del cuaderno de ejemplo → resultado en pantalla y la lista pasa
    de 65 a 72 tierras. Pruebas: `tests/test_nuevo_importar.py` (12) y `test_cuaderno_cyl.py`.
  - *Límite deliberado*: **el municipio no se rellena** porque el cuaderno trae localidad y provincia
    pero no municipio, y deducirlo del nombre sería inventar (`AGENTS.md` §3.3).
- [x] **Mapa del cliente con sus tierras**: clicar una y ver sus datos.
  - Hecho en `/nuevo/`: lista agrupada por municipio, ortofoto del IGN con los linderos, zoom, selector
    de zona, **coloreado por uso o cultivo con leyenda palabra + color**, y panel con los datos de la
    tierra y sus otros años al clicar (en el mapa o en la fila). Verificado en Chrome a 390/1024/1440
    px, 0 fallos.
- [ ] Cargar la **PAC/registros de años anteriores** y crear la explotación desde ahí sin meter datos
      a mano.
  - *Parcial*: la importación del **Cuecyl de cualquier campaña** ya crea su campaña y sus tierras sin
    teclear nada (probado con el cuaderno de ejemplo de 2026), y la finca se rellena con el titular
    del fichero. **Falta**: importar los **recintos por campaña de la Junta** (canal verificado
    2023–2026) y la PAC de años anteriores; y **no hay fichero oficial de la solicitud PAC**, así que
    la PAC se modela (2026 y su paquete) pero no se presenta desde aquí. La creación de una finca
    nueva desde el fichero tampoco está: se importa en la finca activa.
- [x] **Leer facturas** (OCR) — tiene que estar ya.
  - **Confirmado**: `app/facturas.py` + `app/ocr.py` leen PDF, escaneo y foto; devuelven una
    **propuesta** campo a campo que el agricultor revisa (`POST /api/facturas/leer`). Probado contra
    una factura sintética (`7/7`) y con las pruebas de facturas en verde. **La precisión sobre
    facturas reales sigue sin medirse**: el corpus de D08 está aparcado por decisión de David. En
    «Hoy» hay tarjeta del número de facturas; el detalle sigue en la app vieja.
- [x] **Gastos e ingresos** de la explotación.
  - **Hecho en el servidor** (gastos, inversiones, pagos, reparto por tierra, ventas, facturas emitidas
    y cobros) y **enseñado en «Hoy»**: tarjetas de gastos (total y pendiente) y ventas (total, cobrado
    y pendiente) con `/api/nuevo/resumen`, sin mezclar cosas de distinta naturaleza. El alta y el
    detalle siguen en la app vieja.
- [ ] **Conexión bancaria por API (PSD2)** para consultar saldos y movimientos, no operar.
  - **Investigación hecha** (`docs/PSD2-AGREGADORES.md`): la vía es **contratar un AISP autorizado**,
    no sacar licencia propia; 5+ candidatos con API de solo lectura y sandbox; para solo lectura no
    hace falta licencia de iniciación de pagos; consentimiento en el banco, sin ver credenciales.
  - **El coste, en claro (05/11 tarde)**: **ningún proveedor publica precio de producción**. Solo hay
    una cifra: **sandbox de BBVA = 0 €**; Tink publica «por usuario/mes» sin importe y GoCardless la
    unidad «requisición activa al mes» sin precio; los demás, presupuesto por correo. El coste anual
    del escenario (2 cuentas, ≈30 consultas/mes) **no es calculable** sin presupuesto: no se inventa.
  - **Parado a propósito (nivel 3)**: sin coste publicado **no se propone contratar**; hay que pedir
    **dos presupuestos escritos** (Enable Banking y Powens/Unnax) y **David decide el gasto**, que aún
    no ha aprobado. Criterio de parada: si supera el coste de seguir con el extracto por fichero
    (0 €, ya existe), no se contrata. **Nada de código de PSD2** hasta contrato.
- [x] **Cuaderno guiado**: decir qué falta para que esté completo.
  - Hecho en `/nuevo/`: la entrada «Cuaderno» abre una vista propia con **cuántas cosas faltan**, la
    lista **agrupada por dónde se arregla**, cada cosa con su «dónde» y un botón que lleva a la
    pantalla nueva cuando existe; lo que **bloquea el envío a la Junta** se dice con palabra. Si no
    falta nada, «El cuaderno está completo». Con los datos de la finca de prueba: **29 secciones y
    123 cosas** (las de cada tierra incluidas). Al pie, «Abrir el cuaderno de la Junta».
- [x] **Productos y abonos con dosis por hectárea** (corrección 4 del diseño y bloque 4):
  - Hecho en `/nuevo/`: pestañas de **productos** y **abonos** con buscador; cada producto enseña
    **dosis máxima por hectárea con su unidad**, materia activa y plazo de seguridad; cada abono, su
    riqueza N/P/K. «Apuntar en una tierra» con la tierra, la fecha, las hectáreas de la tierra, la
    dosis por hectárea y **el total calculado (dosis × hectáreas) antes de guardar**; guarda con
    `/api/tratamientos` o `/api/fertilizaciones`. Si el servidor no deja guardar, se enseña su aviso
    en palabras de agricultor. **Verificado en Chrome**: 24 productos y el total calculado.
- **El flujo que pidió David**, encadenado con un «siguiente paso»: **foto a la factura o al envase →
  elegir tierra → trabajo del día → historial → calendario → filtros por tipo con cantidades**. Las
  piezas están y ahora se enlazan: tras guardar la factura, «Elige la tierra»; en la ficha, «Ver el
  calendario» y «Ver todos los trabajos»; tras apuntar, «Ver el trabajo de hoy».

## La ronda de David del 05/11 (tarde): lo que ha visto y pedido

David vio el diseño («tiene buena pinta») y pidió, en su orden: **facturas con fotos**, **tierra
primero**, **historial de la tierra**, **calendario**, **filtros por tipo** y **contornos del SIGPAC**.
Todo está construido en `/nuevo/` y verificado en Chrome a 390/1024/1440 (0 fallos):

- [x] **Facturas con fotos**: botón grande «Hacer una foto» (cámara del móvil) y elegir archivo;
      **varias fotos** (factura, envase, albarán) con vista previa; «Leer la factura» con el lector
      del servidor; **propuesta campo a campo para revisar y corregir** (proveedor, NIF, número,
      fecha, base, IVA, total, líneas); «Guardar». Si el lector no está o no entiende la foto, **lo
      dice y deja escribirla a mano**, nunca inventa. **Verificado**: una foto sintética se lee y
      sale la propuesta; las fotos de más se guardan como documentos.
- [x] **Tierra primero**: al pinchar una tierra (en la lista o en el mapa) se abre su ficha con el
      **«Hoy en esta tierra»**: los trabajos de hoy sobre ella o «hoy no hay nada apuntado».
  - **Y desde la propia tierra se apunta el trabajo del día** (nuevo, 05/11 tarde): botón «Apuntar un
    trabajo» en la ficha y destino «Apuntar» en la barra del móvil y en la lateral. Se elige el
    **apero del vocabulario del servidor** (rodillo, cultivador, arado, grada, fresadora, otro), la
    fecha de hoy y las hectáreas de la tierra; se guarda y la ficha se refresca con el trabajo en
    «Hoy en esta tierra» y en el historial. **Verificado en Chrome**: el apunte queda en la base con su
    apero y la pantalla lo dice (0 fallos).
- [x] **Historial de la tierra**: por campañas, con **siembra** (cultivo, variedad, dosis de semilla
      kg/ha), **labores** (vertedera —en el programa se llama **arado**—, cultivador, grada, siembra…),
      **tratamientos** (producto y dosis), **abonos con kg/ha y el mes** y **cosecha en kg/ha**. Los
      años sin datos no se rellenan.
- [x] **Calendario**: rejilla del mes con los días que tienen trabajo (número + palabra, nunca solo
      color); al pinchar un día, sus trabajos con la tierra; mes anterior y siguiente.
- [x] **Filtros por tipo de trabajo**: botones por tipo con su cuenta; al elegir, las tierras con su
      municipio, hectáreas y cantidad o por hectárea, y el resumen de n y hectáreas. Trazabilidad de
      toda la explotación.
- [x] **Contornos del SIGPAC**: `GET /api/mapa/tierra/{id}.png` devuelve la **ortofoto del IGN con el
      contorno dibujado** (relleno suave y línea blanca con borde oscuro), centrada y con margen; la
      ficha la enseña. Si la tierra no tiene forma, la ficha **lo dice** («no tiene forma en el
      SIGPAC») en vez de dibujar un cuadro inventado. 800×600 en unos 2 s en caliente.
  - **Y el GeoPackage ya se abre** (05/11 tarde): `app/geopackage_sigpac.py` lee el `.gpkg` de la
    caché **sin GDAL ni shapely** (descubre tabla y columna de geometría, descubre atributos por
    nombre, traduce el blob GPKG/WKB a WKT) y `POST /api/sigpac/cache/{provincia}/contornos` rellena
    `geometria`/`dibujo` de las parcelas de la finca que casan por su referencia SIGPAC, de forma
    idempotente. 21 pruebas con un gpkg sintético. **Queda por probar con un gpkg real de 600 MB**
    (streaming/índice) y solo admite Polygon/MultiPolygon (rechaza Z/M con su código, no los lee mal).
- **Verificado en Chrome**: ficha (trabajo de hoy, historial, imagen del contorno), calendario,
  filtros y factura leída, con **0 fallos**; capturas nuevas en `docs/capturas-nuevo/`
  (`tierra-historial.png`, `calendario.png`, `trabajos-filtrados.png`, `factura-leida.png`).

**Decisiones que David tiene que conocer:**
- **«Vertedera» no existe en el vocabulario del programa**: los aperos son rodillo, **arado**,
  cultivador, grada, fresadora y otro. Se ha dejado «arado» y **no se ha traducido una palabra en la
  otra** (sería inventar). Si quiere que se llame «vertedera», se cambia la etiqueta y sale sola en
  las tres puertas. **Ya se puede apuntar el apero desde la app nueva**: `POST /api/labores` acepta
  `subtipo` y lo valida (un apero inventado contesta 422 con la lista de los que valen); el dato se
  guarda en su columna y `GET /api/labores` ya lo devuelve.
- **El apuntar de todos los días está a medias en la app nueva**: el trabajo de suelo (arado,
  cultivador, grada, rodillo, fresadora, otro) ya se apunta desde la tierra; **tratamientos, abonos,
  siembra y cosecha siguen en la app vieja**, y la cola sin cobertura también. Es lo siguiente.
- Las pantallas de **PAC** y **gastos/facturas detalladas** siguen enlazando a la app vieja.

## Lo que se ha cerrado y cómo se comprueba

| Fecha | Qué | Evidencia |
|---|---|---|
| 2026-11-05 | **Cuaderno guiado y productos/abonos con dosis por hectárea** | Arnés de Chrome, 0 fallos (29 secciones / 123 cosas; 24 productos; total calculado); capturas `cuaderno-guiado.png` y `productos-dosis.png` |
| 2026-11-05 | **GeoPackage del SIGPAC abierto: contornos de las parcelas** | `POST /api/sigpac/cache/{provincia}/contornos`; 21 pruebas con gpkg sintético (sin internet); lee Polygon/MultiPolygon, rechaza Z/M y tipos raros |
| 2026-11-05 | **Apuntar el trabajo del día desde la tierra (con apero)** | Arnés de Chrome: apero del servidor, guardado y apunte en la base; `tests/test_labores_con_apero.py` (15) |
| 2026-11-05 | **Tierra primero, historial, calendario y filtros por tipo** | Arnés de Chrome, 0 fallos (ficha con trabajo de hoy e historial; calendario con días; filtros con tierras y hectáreas); `tests/test_nuevo_historial.py` (18) |
| 2026-11-05 | **Facturas con varias fotos, lectura y propuesta corregible** | Arnés de Chrome: foto → propuesta; captura `factura-leida.png` |
| 2026-11-05 | **Contornos del SIGPAC: ortofoto + contorno dibujado** | `GET /api/mapa/tierra/{id}.png`; 23 pruebas sin internet; captura `tierra-historial.png` |
| 2026-11-05 | Tierras: alta por código y en la ventana del SIGPAC, resaltada, catalogada y editable | Arnés de Chrome, 0 fallos (búsqueda → recinto dibujado → añadido, 64 → 65); capturas en `docs/capturas-nuevo/` |
| 2026-11-05 | Importar el cuaderno de un cliente y crear sus tierras sin teclear | Arnés de Chrome (subida real del `.xlsx`, 65 → 72); `tests/test_nuevo_importar.py` (12) |
| 2026-11-05 | Mapa coloreado por uso/cultivo con leyenda y ficha al clicar | Arnés de Chrome a 390/1024/1440, 0 fallos |
| 2026-11-05 | Cuaderno guiado: qué falta y dónde se arregla | Arnés de Chrome (bloque en «Hoy»), `GET /api/nuevo/que-falta` |
| 2026-11-05 | Gastos e ingresos en «Hoy» | Arnés de Chrome, `GET /api/nuevo/resumen` |
| 2026-11-05 | Facturas (OCR) confirmadas | `app/facturas.py`, `app/ocr.py`, `POST /api/facturas/leer`; pruebas de facturas en verde |
| 2026-11-05 | PSD2: investigación y dos opciones medidas, sin contratar | `docs/PSD2-AGREGADORES.md` (parado en nivel 3: precios no publicados) |
