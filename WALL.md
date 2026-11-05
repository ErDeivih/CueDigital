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
  - **Parado a propósito (nivel 3)**: **ningún candidato publica precio** (Enable Banking y
    Powens/Unnax piden presupuesto con mínimo mensual), así que la regla «la más barata que cumpla» no
    se puede aplicar. Hay que pedir dos presupuestos y que David apruebe el gasto. **Nada de código**
    hasta que haya contrato.
- [x] Cuaderno guiado: decir qué falta para que esté completo.
  - Hecho en «Hoy»: bloque **«falta para el cuaderno»** con el número y la lista de lo que falta, **qué
    es** y **dónde se arregla** (`GET /api/nuevo/que-falta`), sacado de lo que de verdad hay apuntado
    (`cuaderno-cyl/que-falta` + las 8 de `iuws.QUE_FALTA`). Verificado en Chrome.

## Lo que se ha cerrado y cómo se comprueba

| Fecha | Qué | Evidencia |
|---|---|---|
| 2026-11-05 | Tierras: alta por código y en la ventana del SIGPAC, resaltada, catalogada y editable | Arnés de Chrome, 0 fallos (búsqueda → recinto dibujado → añadido, 64 → 65); capturas en `docs/capturas-nuevo/` |
| 2026-11-05 | Importar el cuaderno de un cliente y crear sus tierras sin teclear | Arnés de Chrome (subida real del `.xlsx`, 65 → 72); `tests/test_nuevo_importar.py` (12) |
| 2026-11-05 | Mapa coloreado por uso/cultivo con leyenda y ficha al clicar | Arnés de Chrome a 390/1024/1440, 0 fallos |
| 2026-11-05 | Cuaderno guiado: qué falta y dónde se arregla | Arnés de Chrome (bloque en «Hoy»), `GET /api/nuevo/que-falta` |
| 2026-11-05 | Gastos e ingresos en «Hoy» | Arnés de Chrome, `GET /api/nuevo/resumen` |
| 2026-11-05 | Facturas (OCR) confirmadas | `app/facturas.py`, `app/ocr.py`, `POST /api/facturas/leer`; pruebas de facturas en verde |
| 2026-11-05 | PSD2: investigación y dos opciones medidas, sin contratar | `docs/PSD2-AGREGADORES.md` (parado en nivel 3: precios no publicados) |
