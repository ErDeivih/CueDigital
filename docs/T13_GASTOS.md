# T13 — Gastos, inversiones, repartos y coste de las averías

**Ticket:** `T13 / E7` — «Gastos, activos, repartos y límites de métricas; abono A03».
**Ronda:** 39 bis (05/10/2026). **Depende de:** T12, cerrado.
**Ficheros de este ticket, y solo estos:**

| Fichero | Qué es |
|---|---|
| `backend/app/gastos.py` | La lógica del dominio, **pura**: importes, repartos, cuadres, estados, «no lo sé», el A03 y el coste de las averías. Sin FastAPI y sin base de datos. |
| `backend/app/routers/gastos_api.py` | El router: 24 rutas contra las tablas que se proponen en el apartado 3. |
| `backend/tests/test_gastos.py` | 93 pruebas: 77 de la lógica pura (corren hoy) y 16 del recorrido por la API (se saltan hasta que se integren las tablas, diciendo qué falta). |
| `backend/web/react/pantallas/gastos.js` | La pantalla S13 (la lista de cuentas y la ficha de un gasto), React + htm, pura. |
| `backend/tests_js/gastos.test.js` | 26 pruebas de la pantalla. |
| `docs/T13_GASTOS.md` | Este informe. |

---

## 1. Qué hay hecho, una línea por cosa

**La lógica del dominio (`app/gastos.py`)**

1. Los **cinco registros separados** (gasto, inversión, factura, pago, movimiento bancario), con la tabla que dice qué aporta cada uno al coste de la campaña y una función que decide si algo entra entero en el año (`es_un_gasto_completo_del_cultivo`).
2. Los **seis estados de un gasto** (`sin_importe`, `sin_pagar`, `pagado_en_parte`, `pagado`, `vencido`, `anulado`), cada uno con su prueba.
3. El **pendiente de un gasto**, que nunca es negativo y que es «no lo sé» cuando no se sabe el importe.
4. El **cuadre de los importes de un documento** (base + IVA = total) con los **tres finales**: cuadra, no cuadra, y no lo he podido comprobar.
5. El **importe de un gasto**, con el orden de fuentes escrito: el total escrito manda, si no base + cuota, si no base × (1 + tipo), y si no **«no lo sé»**.
6. Los **cuatro métodos de reparto** (área, horas, consumo, manual), con el método guardado en cada trozo.
7. **El reparto que suma exacto**: el céntimo del redondeo se reparte de uno en uno por la fracción mayor y **se dice a qué destino se le ha puesto**.
8. **Un reparto que no se puede hacer no se hace a medias**: si falta un peso (una hectárea que no consta), el gasto entero se queda **sin asignar** y se dice por qué.
9. El **cuadre del reparto** (`repartido + sin asignar = total conocido`) con lo que falta calculado de verdad, no por construcción.
10. **El A03 entero**: el abono con **dos cifras dichas como distintas** (kg de producto por hectárea y kg de nutriente por hectárea) y el nutriente que no consta **en «no lo sé»**, nunca en cero.
11. **Los pagos parciales y agrupados**: un pago se reparte por orden entre varios gastos, lo que sobra queda dicho como «sin conciliar» y **deshacer devuelve la deuda sin tocar el pago**.
12. **El traspaso entre cuentas propias (A07)**: dos movimientos atados y **cero ingreso y cero gasto operativo**, comprobado con dos ceros explícitos.
13. **Las subvenciones con tres estados** y una función que suma **solo lo cobrado**: la previsión se dice aparte y no se suma nunca.
14. **El coste de las averías** (lo que el T14 dejó declarado como de este ticket), agrupado por avería, con lo que no cuelga de ninguna dicho aparte y con «arreglada» y «coste» como dos cosas distintas.
15. **El margen por concepto** con sus tres columnas (directos, repartidos, sin asignar) y la regla que más importa: **si falta un importe, el margen es `None`** y se dice cuántos faltan.
16. **La cuenta de la explotación** con los cinco registros contados por separado, el pendiente que se vuelve «no lo sé» en cuanto hay un gasto sin importe, y lo que está sin asignar contado.
17. **La caja**, que es otra cosa que el margen, con las ayudas previstas fuera de lo entrado.
18. **`QUE_FALTA`**: las tres cosas que este programa no calcula (la amortización, el extracto del banco y el IVA), cada una con lo que es, para qué haría falta y de quién depende.

**El router (`routers/gastos_api.py`), 24 rutas**

19. `GET /api/gastos` — la pantalla S13 entera, con las cinco listas separadas, las tres columnas del coste, la caja, los márgenes y lo que falta.
20. `GET /api/gastos/avisos` — lo que hay que mirar: gastos vencidos y gastos a los que les falta el importe.
21. `GET /api/gastos/averias` — el coste de cada avería, con las reparaciones que no cuelgan de ninguna aparte.
22. `POST /api/gastos` + `PUT /api/gastos/{id}` — apuntar y corregir un gasto, **con clave de reenvío** (reenviar devuelve el que ya estaba) y **sin bloquear** por un dato que falta.
23. `POST /api/gastos/{id}/anular` — anula con motivo **y revierte los efectos**: el gasto deja de contar, sus repartos se anulan y el dinero aplicado vuelve a estar sin conciliar.
24. `POST /api/gastos/{id}/repartos` — repartir por área/horas/consumo/manual, con la superficie de cada tierra **leída del servidor**, y con el «sin asignar» cuando no se puede.
25. `POST /api/gastos/{id}/sin-asignar` — dejar el gasto entero sin asignar, diciéndolo.
26. `DELETE /api/gastos/{id}/repartos/{reparto_id}` — quitar un trozo de reparto, dejando el rastro entero en la auditoría.
27. `POST|GET /api/gastos/inversiones` + `POST /api/gastos/inversiones/{id}/anular` — las inversiones, con lo que de ellas se ha llevado la campaña y lo que sigue sin asignar.
28. `POST|GET /api/gastos/pagos`, `POST /api/gastos/pagos/{id}/conciliar`, `DELETE /api/gastos/pagos/{id}/aplicaciones/{aplicacion_id}`, `POST /api/gastos/pagos/{id}/anular` — los pagos, parciales, agrupados y **reversibles**.
29. `POST|GET /api/gastos/subvenciones` + su anulación — las ayudas con sus tres importes y sus tres estados.
30. `POST /api/gastos/traspaso` — el A07 por la API: dos movimientos atados, cero ingreso y cero gasto, y **no escribe nada** (los movimientos bancarios son del T20, y se dice).
31. `GET /api/gastos/cuadre` y `GET /api/gastos/que-falta`.

**La pantalla (`web/react/pantallas/gastos.js`)**

32. La tarjeta del **coste con sus tres columnas separadas** y el total conocido, más **cuántos importes no se saben**.
33. La tarjeta de **la caja**, aparte de la del margen, con las ayudas previstas fuera de lo entrado y su frase.
34. **Las inversiones en su tarjeta**, con lo que les toca a la campaña y lo que queda sin asignar.
35. **Las ayudas con sus tres cifras** y su estado en palabras.
36. **Los pagos** con lo aplicado y lo que no se sabe a qué va, y el dinero sin conciliar en su sitio.
37. **El margen por cultivo**, que cuando le falta un importe **no enseña un número**: enseña por qué no se puede.
38. **La ficha de un gasto** con su cuadre de cuatro números (y la cifra que falta cuando no cierra), sus trozos de reparto, su método cada uno y el botón de quitarlo.
39. **Los formularios** (gasto, reparto, anular) con sus campos y sus `id`, los botones de elegir con `data-campo`/`data-valor`/`data-elegido` y **ninguna pregunta que nazca contestada**.
40. **Lo que el programa todavía no calcula**, enseñado en la pantalla.
41. La misma lista **para el móvil y para la tabla del ordenador** (`.solo-movil` y `.solo-escritorio`).
42. Y la pantalla **no hace ni una cuenta de dinero**: hay una prueba que lo comprueba leyendo el fichero.

---

## 2. Qué he comprobado y cómo

### 2.1 Las pruebas de la lógica pura

```
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests/test_gastos.py -q
```

**Medido: `77 passed, 16 skipped in 1.61s`.** Las 77 que pasan son la lógica pura (`app/gastos.py`), que
no necesita servidor ni base de datos. Las 16 que se saltan son el recorrido por la API, y **se saltan
diciendo exactamente qué falta** (ver el apartado 4).

**Recuento:** `pytest tests/test_gastos.py --collect-only` → **93 tests collected**.

### 2.2 Las pruebas de la pantalla

```
cd F:\EspacioCodigo\CueDigital\backend
node --test "tests_js/gastos.test.js"
```

**Medido: `tests 26 · pass 26 · fail 0`.**

### 2.3 Que las pruebas muerden: siete roturas a propósito

No vale «no revienta». He roto el código a propósito **siete veces**, he mirado el rojo y lo he dejado
como estaba. Cada rotura es una de las reglas del encargo, y las siete se han detectado:

| # | Lo que he roto | Regla que protege | Pruebas que se han puesto en rojo |
|---|---|---|---|
| 1 | En `abono_por_hectarea`, el nutriente que no consta pasa a valer `CERO` | **Un importe que no consta no es cero** (A03) | `TestElAbonoDelCasoA03::test_el_fosforo_que_no_consta_no_es_cero` |
| 2 | En `reparto_por_peso`, cuando falta un peso se reparte entre los que sí se saben | **Un gasto que no se sabe repartir no se reparte a medias** | `TestUnPesoQueNoSeSabeNoSeReparteAMedias::test_si_falta_la_superficie_de_una_tierra_no_se_reparte` |
| 3 | En `reparto_por_peso`, el céntimo que sobra deja de repartirse | **La suma exacta, con el redondeo residual a la vista** | `TestElRepartoSumaExacto` — **6 pruebas**, incluidas las cinco parametrizadas de «la suma siempre es exacta» |
| 4 | `CosteDeUnConcepto.margen` calcula aunque falte un importe | **No construir un margen con datos que faltan** | `TestElMargenNoSeConstruyeConDatosQueFaltan::test_con_un_coste_que_no_se_sabe_no_hay_margen` y `::test_un_ingreso_que_no_se_sabe_tambien_deja_el_margen_sin_calcular` |
| 5 | `ingreso_cobrado_de_subvenciones` suma también la previsión | **No sumar previsión al ingreso cobrado** | `TestLasSubvencionesTienenTresEstados::test_la_prevision_no_se_suma_al_ingreso_cobrado` y `TestLaCajaNoEsElMargen::test_las_ayudas_previstas_van_fuera_de_lo_entrado` |
| 6 | En el traspaso, la entrada se apunta como ingreso operativo | **Un traspaso entre cuentas propias no crea ingresos** (A07) | `TestElTraspasoPropioNoEsIngresoNiGasto::test_el_traspaso_no_mueve_el_margen` |
| 7 | En `cuadre_del_reparto`, lo que falta se mete en «sin asignar» (así el cuadre siempre cuadra) | **Lo que no está en ningún sitio se dice cuánto es** | `TestElCuadreDelReparto::test_lo_que_no_esta_en_ningun_sitio_se_dice_cuanto_es` y `::test_repartir_mas_de_lo_que_costo_es_un_error_y_se_ve` |

Después de cada rotura he dejado el fichero como estaba y **he vuelto a correr las pruebas: 77 pasan, 16
se saltan**. Las siete roturas están borradas: no queda ninguna marca `MUTACION` en `app/gastos.py`
(comprobado con un `Select-String`).

### 2.4 Los guardianes que he corrido, y los dos que quedan en rojo hasta integrar

```
..\.venv\Scripts\python.exe -m pytest tests/test_ficheros_de_texto.py tests/test_que_no_falte_ningun_texto.py ^
  tests/test_las_etiquetas_del_rastro_caben.py tests/test_los_botones_hacen_algo.py tests/test_la_migracion_a_react.py -q
```

- **En verde, y es lo que importa:** `test_ficheros_de_texto.py` (los cinco ficheros nuevos son UTF-8
  limpio, sin el destrozo de acentos que este proyecto ha pagado cuatro veces),
  `test_que_no_falte_ningun_texto.py` (la pantalla no pide ni un texto por clave: todo entra por
  propiedades) y `test_las_etiquetas_del_rastro_caben.py` (**las etiquetas de auditoría del router nuevo
  caben en sus columnas y están escritas enteras**, que es el defecto que tumbó producción).
- **En rojo, y es trabajo de integración, no un defecto del código:**
  - `test_los_botones_hacen_algo.py::test_cada_accion_que_se_pinta_la_atiende_alguien` — las **17 acciones**
    que pinta `gastos.js` no las conoce todavía el manejador de clics de `app.js`. Es exactamente lo que
    ese guardián existe para cazar, y se arregla con el bloque del apartado 3.9. (Ese rojo trae también
    las acciones de `trabajos.js`, que es del T15: somos dos escribiendo en el árbol.)
  - `test_la_migracion_a_react.py`: tres pruebas — `test_el_codigo_y_los_ficheros_cuadran`,
    `test_todo_el_javascript_de_react_se_guarda_para_el_campo` y
    `test_el_informe_de_la_migracion_se_puede_contar`. Las tres se arreglan con el bloque del apartado
    3.7–3.10 (la lista `PANTALLAS_EN_REACT`, la caché del service worker y `docs/REACT.md`).
  - `test_lista_de_la_junta.py::test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos` — dice
    «la documentación dice 901 pruebas de JavaScript y hay 951». **De esas 951, 26 son mías y el resto del
    T15**: medido. Ver el apartado 3.10.

**Lo que NO he corrido, y por qué:** la suite entera (**6 minutos** y hay más gente en el árbol, como pide
el encargo) y `scripts/humo.py` (necesita un servidor con las tablas ya integradas, y no puedo levantar
uno en el puerto 8000). `backend/cuedigital.db` **no se ha tocado ni leído**: todas mis pruebas van por
`tests/conftest.py`, que fija una base temporal.

### 2.5 Y lo que sí he podido comprobar de los bloques compartidos, sin tocar esos ficheros

Los bloques del apartado 3 son de ficheros que no son míos, pero **no los he escrito a ojo**: los he
comprobado con las herramientas del propio proyecto, leyéndolos del informe y pasándolos por las
funciones de verdad. Es lo más cerca que se puede estar de haberlos integrado sin integrarlos.

| Qué he comprobado | Cómo | Resultado |
|---|---|---|
| El bloque `textos.GASTOS` **es Python válido** y tiene las claves que la pantalla lee | `ast.literal_eval` del bloque, sacado del informe | **140 claves, 164 textos**, sin un solo error de sintaxis |
| **Ninguna de esas 164 frases lleva jerga** | `textos.palabras_prohibidas_encontradas` sobre cada una | **0 palabras prohibidas** |
| Los **47 mensajes nuevos** se pueden rellenar y no llevan jerga | `string.Formatter.parse` + `format` con «X» en cada hueco + `palabras_prohibidas_encontradas` | **47 mensajes, 0 problemas**: ningún hueco sin nombre válido, ninguno sin rellenar, y **ningún código que ya existiera** |
| Las **etiquetas del rastro** del router caben en sus columnas | `tests/test_las_etiquetas_del_rastro_caben.py`, que lee `app/` entero con el parser | **en verde** (es la prueba que existe porque un texto largo tumbó producción) |
| `app/routers/gastos_api.py` **compila** | `python -m py_compile` | correcto |
| Las **24 rutas** están en un orden que funciona | lectura del árbol del parser: lista de rutas en orden de declaración | las **7 de palabra fija van antes** que `/gastos/{gasto_id}`, que es lo que impide que `pagos` se lea como un identificador |

---

## 3. Cambios que hay que integrar

> **Todo lo de este apartado es de ficheros compartidos, y ninguno se ha tocado.** Los bloques están
> listos para pegar, en el orden en que conviene hacerlo (primero el modelo y los esquemas, después el
> router, y al final la pantalla).

### 3.1 `backend/app/models.py` — las seis tablas

**Por qué:** el router y la pantalla no pueden existir sin ellas. Van juntas y con el porqué escrito, como
las del T14. Se pegan al final del fichero, después de `EnlaceDeContacto`.

```python
# --------------------------------------------------------------------------
# Las cuentas de la explotación (T13, E7, 05/10/2026)
# --------------------------------------------------------------------------
#
# **CINCO REGISTROS QUE NO SON LO MISMO, Y POR QUÉ ESTÁN EN CINCO TABLAS.** El encargo lo exige con
# estas palabras: «Gasto, inversión, factura, pago y movimiento bancario son registros distintos. No
# los mezcles en una tabla ni en un nombre». Aquí eso se cumple con cinco tablas y no con una columna
# `clase`, y el motivo es que cada uno se equivoca por su cuenta:
#
#   · **El gasto** es lo que se ha consumido: el gasóleo, el abono, la reparación. Es **lo único que
#     entra en el margen de la campaña** (`gastos.APORTA_AL_COSTE`).
#   · **La inversión** es lo que se compra para durar (el tractor, la sembradora, la nave). El
#     contrato lo dice literal en S13: «Compra de activo no equivale automáticamente a gasto completo
#     del cultivo». Lo que de ella va a cada campaña lo dice el agricultor con un reparto
#     (`repartos_de_coste`) y, mientras no lo diga, **se queda sin asignar y se ve**.
#   · **La factura** es el papel del proveedor. Ya existe en este programa (`facturas`) y **no se
#     duplica**: el gasto la *apunta* con `factura_id`. Si la factura aportara coste por su cuenta,
#     cada compra contaría dos veces.
#   · **El pago** es el dinero que sale, y puede ser parcial y agrupado: por eso **no cuelga de un
#     gasto** y vive en su tabla, con las aplicaciones aparte (`aplicaciones_de_pago`).
#   · **El movimiento bancario** es lo que pone el extracto, y es del ticket siguiente (T20). Aquí no
#     hay tabla para él a propósito: el traspaso entre cuentas propias se calcula
#     (`gastos.traspaso_entre_cuentas_propias`) y **no se guarda todavía**, y eso se dice en la
#     pantalla en vez de disimularse.
#
# **Y LA PROTECCIÓN QUE MANDA SOBRE TODAS:** el dinero no se cuenta dos veces. Se consigue con dos
# decisiones que están en el esquema y no en un comentario:
#
#   1. **Conciliar un pago no crea un gasto.** La conciliación escribe en `aplicaciones_de_pago`, que
#      solo dice «este dinero va contra este gasto». No hay ninguna línea, ni en el modelo ni en el
#      router, que cree un gasto a partir de un pago.
#   2. **Un pago no puede tener aplicado más de su importe**, y un gasto no puede tener aplicado más
#      de lo que debe. Lo comprueba el router con la frase del agricultor y hay pruebas que lo fijan.
#
# **Un importe que no consta es `None` en las cinco columnas de dinero** (`importe`, `base_imponible`,
# `cuota_iva`, `valor_residual`…), nunca `0.00`: es la regla de la casa entera y en un cuaderno de
# cuentas es la diferencia entre «esta reparación no costó nada» y «no sé lo que costó».


class Gasto(Base):
    """Lo que se ha consumido: el gasóleo, el abono, la reparación, la cuota del seguro.

    Es **el único registro de este bloque que entra en el margen de la campaña**, y por eso es el que
    más cuidado tiene: el importe puede no constar (`importe` en `None`), el total que el agricultor
    leyó en el papel **manda** sobre la suma de base y cuota, y el gasto dice a qué tierra o cultivo
    va (`parcela_id`, `cultivo`) o se reparte después.

    `averia_id` es de donde sale **el coste de las averías**, que el T14 dejó declarado como de este
    ticket: la reparación es **un gasto** —con su factura y su pago, como cualquier otra— que además
    dice de qué avería salió. No se guarda un importe dentro de la avería porque un importe en dos
    sitios acaba diciendo dos cosas el día que alguien corrija una de las dos.
    """

    __tablename__ = "gastos"
    __table_args__ = (
        # Reenviar el mismo gasto (el móvil sin cobertura, un botón pulsado dos veces) devuelve el
        # mismo. Parcial, por lo mismo que en las entregas: un gasto anulado deja libre su clave.
        Index(
            "uq_gasto_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulado = 0"),
            postgresql_where=text("anulado = false"),
        ),
        Index("ix_gasto_fecha", "explotacion_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)

    # El día de la compra o del consumo. Vacío es «no consta» (una reparación apuntada de memoria),
    # y el vencimiento vacío quiere decir que nadie ha pactado un plazo: poner la fecha del gasto
    # sería inventarse uno.
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    vencimiento: Mapped[dt.date | None] = mapped_column(Date)

    # Qué fue, en palabras del agricultor («abono del trigo», «reparación del remolque»). Es
    # obligatorio en el esquema y no en la columna: una columna obligatoria no se puede añadir a una
    # tabla que ya existe, y aquí la puerta es el esquema.
    concepto: Mapped[str | None] = mapped_column(String(200))
    # Nuestra categoría (`gastos.CATEGORIAS_DE_GASTO`). Agrupa y permite leer una lista de un
    # vistazo, y **no decide nada**: no dice de qué máquina es ni si es una inversión.
    categoria: Mapped[str] = mapped_column(String(40), default="otro", index=True)

    proveedor: Mapped[str | None] = mapped_column(String(200))
    proveedor_nif: Mapped[str | None] = mapped_column(String(20))
    contacto_id: Mapped[int | None] = mapped_column(ForeignKey("contactos.id"), index=True)

    # El justificante: la factura de compra que ya existe en el programa. Vacío es «este gasto no
    # tiene factura» (un ticket de gasóleo), y eso no lo hace menos gasto.
    factura_id: Mapped[int | None] = mapped_column(ForeignKey("facturas.id"), index=True)
    # De qué máquina es y de qué avería salió, si se sabe. Es lo que hace que el coste de las
    # averías y el de las máquinas salgan de las cuentas de verdad y no de un número escrito aparte.
    maquina_id: Mapped[int | None] = mapped_column(ForeignKey("maquinas.id"), index=True)
    averia_id: Mapped[int | None] = mapped_column(ForeignKey("averias_de_maquina.id"), index=True)

    # **El coste directo**: cuando el gasto ya dice de qué tierra o de qué cultivo es. Lo que no se
    # sabe a qué va se apunta sin estos dos campos y se reparte después (o se queda sin asignar).
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    cultivo: Mapped[str | None] = mapped_column(String(120))

    # Las cuentas del papel, **cada una puede faltar** y ninguna se convierte en cero. El importe que
    # manda es `importe`: si el agricultor leyó «121,00 €» en el papel, ese es el total aunque
    # `base + cuota` dé 120,99 por un redondeo del proveedor. Ver `gastos.importe_de_un_gasto`.
    base_imponible: Mapped[Decimal | None] = mapped_column(Dinero)
    cuota_iva: Mapped[Decimal | None] = mapped_column(Dinero)
    tipo_iva_pct: Mapped[float | None] = mapped_column(Float)
    # **`None` es «no sé lo que costó», y es un estado de verdad** (`gastos.SIN_IMPORTE`): el
    # agricultor sabe que pagó la reparación y no se acuerda de cuánto, y el contrato dice que «un
    # apunte real con datos incompletos se guarda con pendientes». Un `0.00` aquí diría que salió
    # gratis y el margen del año saldría mejor de lo que es.
    importe: Mapped[Decimal | None] = mapped_column(Dinero)

    notas: Mapped[str | None] = mapped_column(Text)
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class InversionDeLaFinca(Base):
    """Un bien que se compra para durar: el tractor, la sembradora, la nave, el remolque.

    **No es un gasto, y ése es el motivo de que tenga su tabla.** El contrato lo dice en S13 y el
    encargo lo repite: comprar un activo **no** es un gasto completo del cultivo. Si el tractor de
    60.000 € entrara como gasto del año, el margen de esa campaña diría que se perdió dinero y los
    tres años siguientes que fue gratis, y las dos cosas serían mentira.

    **Lo que NO tiene esta tabla, y es una decisión:** no hay `vida_util` ni `cuota_de_amortizacion`.
    No hay en el programa ninguna tabla oficial de años de vida útil por tipo de bien, y este
    proyecto tiene escrito lo que se hace cuando falta una fuente: se declara. Por eso la parte que
    va a cada campaña **la dice el agricultor** con un reparto a la campaña, y mientras no la diga se
    queda sin asignar. El día que haya fuente, se añade la columna y su prueba.
    """

    __tablename__ = "inversiones_de_la_finca"
    __table_args__ = (
        Index(
            "uq_inversion_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulada = 0"),
            postgresql_where=text("anulada = false"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)

    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    concepto: Mapped[str | None] = mapped_column(String(200))
    # Nuestra (`gastos.CATEGORIAS_DE_INVERSION`): maquinaria, apero, instalación, vehículo, terreno.
    categoria: Mapped[str] = mapped_column(String(40), default="otro", index=True)

    proveedor: Mapped[str | None] = mapped_column(String(200))
    proveedor_nif: Mapped[str | None] = mapped_column(String(20))
    contacto_id: Mapped[int | None] = mapped_column(ForeignKey("contactos.id"), index=True)
    factura_id: Mapped[int | None] = mapped_column(ForeignKey("facturas.id"), index=True)
    # Si el bien es una máquina de la lista de maquinaria, aquí se enlaza: así el tractor es uno solo
    # en las tres pantallas (la inversión, la máquina y el gasto de su reparación).
    maquina_id: Mapped[int | None] = mapped_column(ForeignKey("maquinas.id"), index=True)
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)

    # **`None` es «no sé lo que costó»**, igual que en un gasto, y no un cero.
    importe: Mapped[Decimal | None] = mapped_column(Dinero)
    # Lo que se espera sacar por él al final. Casi nunca se sabe, y vacío es «no lo sé».
    valor_residual: Mapped[Decimal | None] = mapped_column(Dinero)

    notas: Mapped[str | None] = mapped_column(Text)
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class RepartoDeCoste(Base):
    """La parte de un gasto o de una inversión que se lleva a una tierra, un cultivo o una máquina.

    **Por qué esto es una tabla y no unas columnas del gasto.** Porque un gasto se reparte entre
    varias cosas a la vez (el seguro de la finca entre sus 12 tierras) y porque **el método con el
    que se repartió tiene que quedar escrito**: «lo repartió el programa por hectáreas» y «lo repartió
    el agricultor a mano» son dos cosas de fiabilidad distinta, y dentro de un año lo único que
    explicará de dónde salió esa cifra es esta columna.

    **Dos claves ajenas y no una polimórfica**: `gasto_id` o `inversion_id`, y exactamente una de las
    dos. Con `origen_tipo`/`origen_id` la cuenta de «qué usa este gasto» no encontraría las filas
    (`correcciones.tablas_que_apuntan_a` busca por el nombre de la columna), y borrar un gasto dejaría
    sus repartos apuntando al vacío.

    **`sin_asignar` es un destino de verdad**, y es la mitad del ticket: lo que no se sabe a qué va
    **no se reparte a medias**, se queda aquí entero y se dice. Un coste sin asignar **sigue siendo un
    coste conocido**: no desaparece de las cuentas, solo no está atribuido a nadie.
    """

    __tablename__ = "repartos_de_coste"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)

    # De dónde sale este trozo: un gasto o una inversión, nunca los dos y nunca ninguno.
    gasto_id: Mapped[int | None] = mapped_column(ForeignKey("gastos.id"), index=True)
    inversion_id: Mapped[int | None] = mapped_column(ForeignKey("inversiones_de_la_finca.id"), index=True)

    # A dónde va: `gastos.DESTINOS_DE_UN_REPARTO` (tierra, cultivo, maquina, campana, sin_asignar).
    destino_tipo: Mapped[str] = mapped_column(String(20), index=True)
    # El nombre o el identificador como texto. Se guarda **el texto** para que el reparto histórico no
    # cambie si mañana se renombra la tierra, y `parcela_id` aparte para poder sumar por tierra.
    destino: Mapped[str | None] = mapped_column(String(120))
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)
    maquina_id: Mapped[int | None] = mapped_column(ForeignKey("maquinas.id"), index=True)

    # El trozo. **Ya redondeado al céntimo y sumando exacto** con los demás trozos del mismo gasto:
    # el céntimo del redondeo se le pone a uno y se dice a cuál (`gastos.reparto_por_peso`).
    importe: Mapped[Decimal | None] = mapped_column(Dinero)
    # area | horas | consumo | manual (`gastos.METODOS_DE_REPARTO`). **Se guarda: dentro de un año es
    # lo único que explica de dónde salió esta cifra.**
    metodo: Mapped[str] = mapped_column(String(20), default="manual")
    # **Si el agricultor ha confirmado el método.** Nace en falso y no en verdadero: un reparto que
    # hizo el programa y nadie ha mirado no puede parecer confirmado.
    confirmado_por_el_agricultor: Mapped[bool] = mapped_column(Boolean, default=False)

    notas: Mapped[str | None] = mapped_column(Text)
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class PagoDeGasto(Base):
    """El dinero que sale. **No es un gasto y no cuelga de un gasto.**

    Las dos decisiones que hacen que esto esté bien, y las dos tienen prueba:

      · **No cuelga de un gasto** (`gasto_id` no existe aquí) porque un pago puede saldar **varios**
        gastos (pagar la factura del taller y la del gasóleo con una transferencia) y un gasto puede
        pagarse con **varios** pagos. Eso se dice en `aplicaciones_de_pago`, que es una tabla aparte.
      · **No cambia el coste de nada.** El coste existe desde que se consume, se haya pagado o no; lo
        que hace un pago es cambiar **el pendiente**, que es otra cuenta.

    Un pago **sin ninguna aplicación** es un estado de verdad y no un error: es el dinero que salió y
    todavía no se sabe a qué va (se mira el banco antes que los papeles). Se queda dicho con esa
    palabra —«sin conciliar»— y la pantalla lo enseña en su lista, esperando.

    **Sin campaña propia**, como el `Cobro` del T12 y por el mismo motivo: es dinero que sale un día,
    no un apunte del cuaderno, y la campaña de lo que se paga la tiene el gasto al que salda.
    """

    __tablename__ = "pagos_de_gasto"
    __table_args__ = (
        Index(
            "uq_pago_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulado = 0"),
            postgresql_where=text("anulado = false"),
        ),
        Index("ix_pago_fecha", "explotacion_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)

    # El día en que salió el dinero. Vacío es «no consta», no «hoy».
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    # **Obligatorio y mayor que cero**: un pago de cero euros no es un pago, y admitirlo llenaría la
    # lista de renglones que no dicen nada. Es la única columna de dinero de este bloque que no
    # admite vacío, justamente porque un pago sin importe no es nada.
    importe: Mapped[Decimal] = mapped_column(Dinero, nullable=False)

    proveedor: Mapped[str | None] = mapped_column(String(200))
    contacto_id: Mapped[int | None] = mapped_column(ForeignKey("contactos.id"), index=True)
    # transferencia | efectivo | cheque | confirming | otro (`ventas.FORMAS_DE_COBRO`, la MISMA lista
    # que la del cobro: no puede haber dos verdades sobre cómo se mueve el dinero).
    forma: Mapped[str] = mapped_column(String(20), default="transferencia")
    referencia: Mapped[str | None] = mapped_column(String(120))
    notas: Mapped[str | None] = mapped_column(Text)

    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class AplicacionDeUnPago(Base):
    """Contra qué gasto va un pago, y cuánto. **Es lo único que crea la conciliación.**

    ## La regla del encargo, en una tabla

    «Conciliar un pago no crea un segundo gasto.» Aquí se ve por qué está escrita así: esta tabla
    **solo dice «este dinero va contra este gasto»**. No tiene importe propio de nada, no crea
    ninguna fila en `gastos` y **deshacerla es borrarla a ella** (con `correcciones.borrar`, que deja
    el rastro entero en la auditoría). El pago sigue apuntado con su importe entero y el gasto vuelve
    a estar pendiente: es literalmente el contrato —«Deshacer conciliación no borra el movimiento
    original»—, y es lo que hace que el dinero no desaparezca de ninguna de las dos pantallas.

    **Muchos a muchos**, que es lo que el contrato pide para los pagos parciales y agrupados: varias
    filas con el mismo `pago_id` (un pago que salda tres gastos) y varias con el mismo `gasto_id`
    (tres pagos que saldan uno). Y las dos cantidades están comprobadas en el router: la suma de las
    aplicaciones de un pago no pasa de su importe, y la de un gasto no pasa de lo que debe.
    """

    __tablename__ = "aplicaciones_de_pago"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    pago_id: Mapped[int] = mapped_column(ForeignKey("pagos_de_gasto.id"), index=True)
    gasto_id: Mapped[int] = mapped_column(ForeignKey("gastos.id"), index=True)
    importe: Mapped[Decimal] = mapped_column(Dinero, nullable=False)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Subvencion(Base):
    """Una ayuda: lo que se pide, lo que se concede y lo que se cobra.

    ## Tres importes y no uno con un estado

    El contrato lo dice en S13: «Subvención prevista, concedida y cobrada son estados distintos. **No
    sumar previsión al ingreso cobrado**». Tres columnas y no una porque **los tres pueden convivir**:
    se pidió una ayuda esperando 12.000 €, concedieron 9.000 y todavía no ha entrado nada. Con una
    sola columna, apuntar la concesión borraría la previsión y el agricultor perdería la cuenta de lo
    que pidió.

    **Y el estado se deduce, no se guarda** (`gastos.estado_de_una_subvencion`): el estado más
    avanzado de los tres que consten. Guardarlo además de los importes sería tener dos verdades sobre
    lo mismo, y la del día que se apuntó dejaría de ser verdad al día siguiente.

    **Solo el importe cobrado cuenta como ingreso.** La previsión se enseña, con su palabra, en su
    propia tarjeta: un agricultor que ve su previsión sumada al ingreso cree que tiene un dinero que
    todavía no ha entrado.
    """

    __tablename__ = "subvenciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)

    concepto: Mapped[str | None] = mapped_column(String(200))
    organismo: Mapped[str | None] = mapped_column(String(200))
    fecha_solicitud: Mapped[dt.date | None] = mapped_column(Date)
    fecha_concesion: Mapped[dt.date | None] = mapped_column(Date)
    fecha_cobro: Mapped[dt.date | None] = mapped_column(Date)

    # **Cada uno puede faltar por su cuenta**, y vacío es «no consta»: una ayuda de la que no se sabe
    # el importe concedido no tiene concedido cero euros.
    importe_previsto: Mapped[Decimal | None] = mapped_column(Dinero)
    importe_concedido: Mapped[Decimal | None] = mapped_column(Dinero)
    importe_cobrado: Mapped[Decimal | None] = mapped_column(Dinero)

    notas: Mapped[str | None] = mapped_column(Text)
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
```

### 3.2 `backend/app/schemas.py` — los esquemas de entrada

**Por qué:** son la puerta de lo que entra, y el router importa estos nombres. Se pega al final del
fichero.

```python
# --------------------------------------------------------------------------
# Las cuentas de la explotación (T13, E7, 05/10/2026)
# --------------------------------------------------------------------------
#
# **Lo que estos esquemas tienen de particular, y por qué**: los importes son `Decimal | None` y
# **`None` quiere decir «no lo sé»**, no cero. Es la regla del encargo («un importe que no consta NO
# es cero: es “no lo sé”, y así tiene que viajar de punta a punta») y empieza aquí: si el esquema
# rechazara un importe vacío, el agricultor no podría apuntar la reparación de la que no se acuerda
# del precio, y acabaría escribiendo un cero que es mentira.
#
# Los campos de texto llevan su tope **leído del modelo** (`_cabe_en_la_columna`), como los del
# dinero del T12: un texto más largo que su columna en SQLite entra y **en PostgreSQL tumba la
# operación entera**.


class GastoEntrada(EntradaBase):
    """Lo que hace falta para apuntar un gasto. **Ningún importe es obligatorio.**"""

    campana_id: int | None = None
    fecha: dt.date | None = None
    vencimiento: dt.date | None = None
    concepto: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Gasto, "concepto")
    )
    categoria: str = "otro"
    proveedor: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Gasto, "proveedor")
    )
    proveedor_nif: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Gasto, "proveedor_nif")
    )
    contacto_id: int | None = None
    factura_id: int | None = None
    maquina_id: int | None = None
    averia_id: int | None = None
    parcela_id: int | None = None
    cultivo: str | None = Field(default=None, max_length=_cabe_en_la_columna(models.Gasto, "cultivo"))
    # **Los cuatro pueden venir vacíos**, cada uno por su cuenta: el total escrito manda, si no se
    # suman base y cuota, si no se aplica el tipo a la base, y si no hay nada el gasto **no tiene
    # importe** (`gastos.importe_de_un_gasto`).
    base_imponible: Decimal | None = None
    cuota_iva: Decimal | None = None
    tipo_iva_pct: float | None = None
    importe: Decimal | None = None
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Gasto, "clave_de_reenvio")
    )

    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.Gasto)


class InversionEntrada(EntradaBase):
    """Lo que hace falta para apuntar un bien que dura. **No es un gasto y no entra en el margen.**"""

    campana_id: int | None = None
    fecha: dt.date | None = None
    concepto: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.InversionDeLaFinca, "concepto")
    )
    categoria: str = "otro"
    proveedor: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.InversionDeLaFinca, "proveedor")
    )
    proveedor_nif: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.InversionDeLaFinca, "proveedor_nif")
    )
    contacto_id: int | None = None
    factura_id: int | None = None
    maquina_id: int | None = None
    parcela_id: int | None = None
    importe: Decimal | None = None
    valor_residual: Decimal | None = None
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.InversionDeLaFinca, "clave_de_reenvio")
    )

    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.InversionDeLaFinca)


class TrozoDeRepartoEntrada(BaseModel):
    """Un trozo de un reparto hecho a mano: a dónde va y cuánto."""

    destino_tipo: str = "tierra"
    destino: str = ""
    importe: Decimal | None = None


class RepartoDeUnGastoEntrada(EntradaBase):
    """Cómo se reparte un gasto. **El método lo confirma el agricultor**, y por eso se pregunta.

    Los cuatro métodos (área, horas, consumo y manual) y lo que trae cada uno:

      · **area** — `parcela_ids`. Las hectáreas las lee el servidor de cada tierra: el agricultor no
        las teclea, y así no hay dos verdades sobre cuánto mide su parcela. **Si a una le falta la
        superficie, el reparto no se hace y el gasto se queda sin asignar.**
      · **horas** y **consumo** — `pesos`: las horas o los litros de cada sitio, que los dice él.
      · **manual** — `trozos`: los importes, uno a uno.
    """

    metodo: str = "manual"
    destino_tipo: str = "tierra"
    parcela_ids: list[int] = Field(default_factory=list)
    pesos: dict[str, Decimal | None] = Field(default_factory=dict)
    trozos: list[TrozoDeRepartoEntrada] = Field(default_factory=list)
    # Si el agricultor ha confirmado el método. **Nace en falso**: un reparto que hizo el programa y
    # nadie ha mirado no puede parecer confirmado.
    confirmado: bool = False
    # Por qué se deja sin asignar. Solo lo usa la puerta de «dejarlo sin asignar».
    porque: str = ""


class AplicacionDePagoEntrada(BaseModel):
    """Cuánto de un pago va contra un gasto. Sin importe, va lo que falte de ese gasto."""

    gasto_id: int
    importe: Decimal | None = None


class PagoEntrada(EntradaBase):
    """El dinero que sale, con lo que salda si ya se sabe.

    **`aplicaciones` puede venir vacío**, y entonces el pago se queda **sin conciliar** y se dice: es
    lo normal cuando se mira el banco antes que los papeles.
    """

    fecha: dt.date | None = None
    # **Obligatorio y mayor que cero**: un pago de cero euros no es un pago. Lo comprueba el router
    # con la frase del agricultor.
    importe: Decimal | None = None
    proveedor: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.PagoDeGasto, "proveedor")
    )
    contacto_id: int | None = None
    forma: str = "transferencia"
    referencia: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.PagoDeGasto, "referencia")
    )
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.PagoDeGasto, "clave_de_reenvio")
    )
    aplicaciones: list[AplicacionDePagoEntrada] = Field(default_factory=list)

    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.PagoDeGasto)


class ConciliacionDePagoEntrada(BaseModel):
    """Decir contra qué gastos va un dinero que ya estaba apuntado. **No crea ningún gasto.**

    Con `automatico` y `gastos`, el dinero se reparte **por orden, el más antiguo primero**
    (`gastos.reparto_de_un_pago`): así la suma de lo aplicado es exactamente el dinero disponible y no
    hay ningún reparto por porcentaje, que es donde aparecerían los céntimos perdidos.
    """

    aplicaciones: list[AplicacionDePagoEntrada] = Field(default_factory=list)
    automatico: bool = False
    gastos: list[int] = Field(default_factory=list)


class SubvencionEntrada(EntradaBase):
    """Una ayuda, con sus tres importes. Los tres pueden venir, y ninguno es obligatorio."""

    campana_id: int | None = None
    concepto: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Subvencion, "concepto")
    )
    organismo: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Subvencion, "organismo")
    )
    fecha_solicitud: dt.date | None = None
    fecha_concesion: dt.date | None = None
    fecha_cobro: dt.date | None = None
    importe_previsto: Decimal | None = None
    importe_concedido: Decimal | None = None
    importe_cobrado: Decimal | None = None
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Subvencion, "clave_de_reenvio")
    )

    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.Subvencion)
```

### 3.3 `backend/app/main.py` — el router

**Por qué:** sin esto las 24 rutas no existen y la pantalla no tiene a quién pedirle nada.

```python
# 1) En la lista de importaciones de `from .routers import (...)` (va en orden alfabético, entre
#    `firmas_api` y `interfaz`):
    gastos_api,

# 2) Entre los `include_router` (busca el bloque donde están todos y añade el suyo):
    # **Las cuentas de la explotación (T13, E7, 05/10/2026).** El router de los gastos, las
    # inversiones, los repartos, los pagos y las ayudas. Va detrás del de las ventas porque comparte
    # su vocabulario de formas de pago (`ventas.FORMAS_DE_COBRO`) y porque el orden de los routers no
    # decide nada: cada uno tiene su prefijo (`/api/gastos`).
    app.include_router(gastos_api.router)
```

### 3.4 `backend/app/textos.py` — los textos

**Por qué:** «Los textos de la pantalla no se escriben en el JavaScript: van en `app/textos.py`».
Son **dos bloques**: el vocabulario de la pantalla (`GASTOS`) y los mensajes (`MENSAJES`).

```python
# --------------------------------------------------------------------------
# Las cuentas de la explotación (T13, E7, 05/10/2026)
# --------------------------------------------------------------------------
#
# POR QUÉ ESTE VOCABULARIO ES TAN LARGO, Y POR QUÉ ESO ES LO CORRECTO AQUÍ. Esta pantalla es la
# primera del programa donde hay que decir **«no lo sé»** muchas veces y de muchas maneras: falta el
# importe de un gasto, falta la superficie de una tierra, falta saber a qué va un coste, falta saber
# si una ayuda se ha cobrado. Cada una de esas cosas se dice con su frase y **dice qué hacer**, que es
# la regla de la casa: describir el problema y callarse no vale.
#
# Y las listas cerradas (las categorías, los métodos de reparto, las formas de pago) llevan **su
# orden y su nombre**, y el orden no se saca de las claves del diccionario: unos botones que cambian
# de sitio se pulsan mal.

GASTOS: dict = {
    "titulo": "Mis cuentas",
    "explica": (
        "Aquí está lo que te ha costado, a qué va y cuánto te queda por pagar. Lo que no sepas se "
        "queda en blanco y el programa te lo dice: un hueco no es un cero."
    ),
    "cuantas": "Tienes {cuantos} gastos apuntados.",
    "cuantas_uno": "Tienes 1 gasto apuntado.",
    "sin_gastos": (
        "Todavía no has apuntado ningún gasto. Empieza por el que tengas el papel a mano: el abono, "
        "el gasóleo o la reparación. Si no sabes lo que costó, apúntalo igual y se queda en blanco."
    ),
    "sin_resultados": (
        "Ningún gasto coincide con lo que buscas. Prueba con otras letras o pulsa VER TODAS para "
        "verlos todos otra vez."
    ),
    "nuevo": "APUNTAR UN GASTO",
    "nuevo_pago": "APUNTAR UN PAGO",
    "nueva_inversion": "APUNTAR UNA INVERSIÓN",
    "nueva_ayuda": "APUNTAR UNA AYUDA",
    "buscar": "BUSCAR",
    "buscar_pista": "Escribe las primeras letras del concepto o del proveedor",
    "ver_todas": "VER TODAS",
    "abrir": "VER ESTE GASTO",
    "corregir": "CORREGIR",
    "anular": "ANULAR",
    "anular_motivo": "¿Por qué lo anulas?",
    "rellenar": "RELLENAR EL IMPORTE",
    "importe": "Lo que costó",
    "pagado": "Pagado",
    "pendiente": "Falta por pagar",
    "como_esta": "Cómo está",
    "proveedor": "Proveedor:",
    "su_tierra": "Va a",
    "su_cuenta": "La cuenta de este gasto",
    "no_se_sabe": "No lo sé",
    "sin_asignar_corto": "Sin asignar",
    "sin_asignar_explica": (
        "Lo que está sin asignar es un coste que ya sabes que existe pero todavía no está en ninguna "
        "tierra. Sigue contando en tus cuentas: lo único que falta es decir a dónde va."
    ),
    "estado_sin_importe": "Falta saber lo que costó",
    "estado_sin_pagar": "Sin pagar",
    "estado_pagado_en_parte": "Pagado a medias",
    "estado_pagado": "Pagado",
    "estado_vencido": "Vencido",
    "estado_anulado": "Anulado",
    "esta_anulado": "Esto está anulado, con su motivo. Sigue aquí para que sepas que estuvo.",
    "esta_anulada": "Esta compra está anulada.",
    "cuadre_titulo": "Las cuentas de este gasto",
    "cuadre_entero": "Lo que costó",
    "cuadre_repartido": "En tierras, cultivos o máquinas",
    "cuadre_sin_asignar": "Sin asignar",
    "cuadre_no_cierra": (
        "Estas cuentas no cierran: hay una parte del gasto que no está ni en un sitio ni en el otro. "
        "Míralo y repártelo otra vez."
    ),
    "todavia_sin_reparto": (
        "Todavía no has dicho a qué tierra o cultivo va este gasto. Sigue contando en tus cuentas, "
        "pero está sin asignar."
    ),
    "reparto_metodo": "Se repartió",
    "reparto_quitar": "QUITARLO DE AQUÍ",
    "repartir": "REPARTIRLO",
    "dejarlo_sin_asignar": "DEJARLO SIN ASIGNAR",
    "metodo_area": "por hectáreas",
    "metodo_horas": "por horas",
    "metodo_consumo": "por lo que se gastó en cada sitio",
    "metodo_manual": "a mano",
    "coste_titulo": "Lo que te ha costado",
    "coste_explica": (
        "Lo directo es lo que dice el papel de un gasto de esa tierra. Lo repartido lo has repartido "
        "tú. Y lo sin asignar es un coste que existe y todavía no va a ningún sitio."
    ),
    "coste_directo": "Directo",
    "coste_repartido": "Repartido",
    "coste_sin_asignar": "Sin asignar",
    "coste_total_conocido": "Total conocido",
    "cuantos_sin_importe": "Gastos de los que no sabes el importe",
    "sin_importe_explica": "De esos no se puede hacer la cuenta hasta que apuntes lo que costaron",
    "caja_titulo": "La caja",
    "caja_explica": (
        "Esto es el dinero que ha entrado y salido de verdad. No es lo mismo que el margen: puedes "
        "haber vendido mucho y no haber cobrado nada todavía."
    ),
    "caja_entrado": "Ha entrado",
    "caja_salido": "Ha salido",
    "caja_saldo": "Queda",
    "caja_por_pagar": "Falta por pagar",
    "ayudas_cobradas": "Ayudas cobradas",
    "ayudas_previstas": "Ayudas pedidas o concedidas, sin cobrar",
    "prevision_no_es_ingreso": "Esto no se suma a lo que ha entrado: todavía no es dinero tuyo",
    "margen_titulo": "El margen de cada cultivo",
    "margen_explica": (
        "Lo que has ingresado menos lo que te ha costado. Si falta el importe de un gasto, el margen "
        "no se puede calcular y aquí se dice por qué, en vez de enseñar una cifra que no es."
    ),
    "ingresos": "Has ingresado",
    "coste_conocido": "Te ha costado",
    "margen": "Margen",
    "margen_incompleto": (
        "De este cultivo no se puede calcular el margen: falta el importe de algún gasto o de algún "
        "ingreso. Apunta lo que falta y vuelve a mirarlo."
    ),
    "inversiones_titulo": "Las inversiones",
    "inversiones_explica": (
        "Un tractor o una nave no son un gasto del año: duran años. Lo que de ellos le toca a esta "
        "campaña lo dices tú, y lo que no digas se queda sin asignar y se ve aquí."
    ),
    "inversion_en_la_campana": "De esto le toca a esta campaña",
    "una_inversion_no_es_un_gasto": (
        "Una inversión no entra entera en el año en que se compra: lo que le toca a cada campaña lo "
        "dices con un reparto."
    ),
    "ayudas_titulo": "Las ayudas",
    "ayudas_explica": (
        "Lo que has pedido, lo que te han concedido y lo que has cobrado son tres cosas distintas, y "
        "aquí van separadas. Lo que todavía no has cobrado no es dinero que tengas."
    ),
    "ayuda_prevista": "Pedido",
    "ayuda_concedida": "Concedido",
    "ayuda_cobrada": "Cobrado",
    "ayuda_estado_prevista": "Pedida, sin resolver",
    "ayuda_estado_concedida": "Concedida, sin cobrar",
    "ayuda_estado_cobrada": "Cobrada",
    "pagos_titulo": "Los pagos",
    "pagos_explica": "El dinero que ha salido, y a qué gastos va.",
    "sin_pagos": "Todavía no has apuntado ningún pago.",
    "pago_aplicado": "Va a gastos por",
    "pago_sin_conciliar": "Sin saber a qué va",
    "pago_conciliar": "DECIR A QUÉ VA",
    "pago_deshacer": "DESHACER ESTO",
    "sin_conciliar_titulo": "Dinero que salió y todavía no sabes a qué va",
    "sin_conciliar_explica": (
        "Ese dinero está apuntado y no se ha perdido: lo único que falta es decir contra qué gasto "
        "va. Cuando lo digas, se descuenta de lo que debes."
    ),
    "sus_pagos": "Los pagos de este gasto",
    "que_falta_titulo": "Lo que este programa todavía no calcula",
    "que_falta_explica": (
        "Se dice para que no te fíes de una cifra que no está: cuando el programa no tiene el dato, "
        "no se lo inventa."
    ),
    "que_falta_para_que": "Para qué haría falta",
    "que_falta_depende": "De quién depende",
    "el_traspaso_no_se_guarda": (
        "Un traspaso de una cuenta tuya a otra no es un ingreso ni un gasto, así que no se apunta ni "
        "en los ingresos ni en los gastos. Guardarlo junto al extracto del banco es el trabajo "
        "siguiente: hoy el programa solo te dice cómo quedan los dos movimientos."
    ),
    "form_nuevo_titulo": "Apuntar un gasto",
    "form_nuevo_pista": (
        "Con el concepto y lo que costó ya queda apuntado. Lo que no sepas se deja en blanco: un "
        "hueco se queda en blanco y no se escribe un cero."
    ),
    "form_corregir_titulo": "Corregir este gasto",
    "form_corregir_pista": (
        "Está puesto lo que apuntaste. Cambia lo que esté mal: lo que había antes queda guardado en "
        "el historial del cuaderno."
    ),
    "form_repartir_titulo": "Repartir este gasto",
    "form_repartir_pista": (
        "Elige cómo lo repartes. Si no sabes a qué va, déjalo sin asignar: se queda dicho y sigue "
        "contando en tus cuentas."
    ),
    "form_pago_titulo": "Apuntar un pago",
    "form_pago_pista": (
        "Lo que ha salido de tu cuenta y, si lo sabes, contra qué gasto va. Si no lo sabes, apúntalo "
        "igual: se queda esperando a que lo digas."
    ),
    "form_inversion_titulo": "Apuntar una inversión",
    "form_inversion_pista": (
        "Lo que has comprado para que dure. Su precio no entra entero en este año: después le dices "
        "qué parte le toca a cada campaña."
    ),
    "form_ayuda_titulo": "Apuntar una ayuda",
    "form_ayuda_pista": (
        "Lo que has pedido, lo que te han concedido y lo que has cobrado. Rellena solo lo que sepas: "
        "lo demás se queda en blanco."
    ),
    "form_anular_titulo": "Anular",
    "guardar": "GUARDAR",
    "cancelar": "VOLVER SIN GUARDAR",
    "guardando": "Guardando…",
    "anular_confirmar": "ANULARLO CON ESTE MOTIVO",
    "campo_concepto": "¿Qué fue?",
    "campo_concepto_pista": "«Gasóleo», «abono del trigo», «reparación del remolque»",
    "campo_categoria": "¿De qué es?",
    "campo_categoria_pista": "Para agrupar tus gastos. Si no lo tienes claro, «otro»",
    "campo_importe": "¿Cuánto costó?",
    "campo_importe_pista": "Si no lo sabes, déjalo en blanco: el programa no escribe un cero",
    "campo_base": "Lo que cuesta sin el IVA",
    "campo_cuota": "El IVA",
    "campo_fecha": "¿Cuándo fue?",
    "campo_vencimiento": "¿Cuándo hay que pagarlo?",
    "campo_vencimiento_pista": "Si lo tienes pactado. Si no, déjalo en blanco",
    "campo_proveedor": "¿A quién se lo compraste?",
    "campo_metodo": "¿Cómo lo reparto?",
    "campo_destino": "¿A qué se reparte?",
    "campo_pesos": "¿Cuánto en cada sitio?",
    "campo_horas": "Horas",
    "campo_litros": "Litros o kilos",
    "campo_motivo": "¿Por qué lo anulas?",
    "categorias_de_gasto": {
        "abono": "Abono",
        "fitosanitario": "Producto para las plagas y las hierbas",
        "semilla": "Semilla",
        "gasoleo": "Gasóleo",
        "reparacion": "Reparación",
        "servicio": "Trabajo de otro",
        "alquiler": "Alquiler",
        "seguro": "Seguro",
        "impuesto": "Impuesto",
        "cuota": "Cuota",
        "otro": "Otra cosa",
    },
    "categorias_de_inversion": {
        "maquinaria": "Máquina",
        "apero": "Apero",
        "instalacion": "Nave o instalación",
        "vehiculo": "Vehículo",
        "terreno": "Tierra",
        "otro": "Otra cosa",
    },
    "metodos_de_reparto": {
        "area": "Por hectáreas",
        "horas": "Por horas",
        "consumo": "Por lo que se gastó en cada sitio",
        "manual": "A mano",
    },
    # **La misma lista que la del cobro** (`ventas.FORMAS_DE_COBRO`): no puede haber dos verdades
    # sobre cómo se mueve el dinero.
    "formas_de_pago": {
        "transferencia": "Transferencia",
        "efectivo": "Efectivo",
        "cheque": "Cheque",
        "confirming": "Confirming",
        "otro": "Otra forma",
    },
    "estados_de_una_subvencion": {
        "prevista": "Pedida, sin resolver",
        "concedida": "Concedida, sin cobrar",
        "cobrada": "Cobrada",
    },
}


# Y los mensajes. **Los que bloquean llevan «qué pasa + qué hago ahora»**, que es la estructura
# obligatoria de este programa: decir el problema y callarse no vale.
MENSAJES.update(
    {
        "G1_el_gasto_de_cero_euros_no_es_un_gasto": (
            "Un gasto de cero euros no es un gasto. Si lo que pasa es que no sabes lo que costó, deja "
            "el importe en blanco y el programa lo apuntará como que falta por saber."
        ),
        "G2_esa_categoria_no_es_ninguna_de_las_que_hay": (
            "«{valor}» no es ninguna de las categorías que hay ({lista}). Elige una de la lista o "
            "apúntalo como «Otra cosa» y escribe en el concepto lo que fue."
        ),
        "G3_el_pago_tiene_que_ser_mayor_que_cero": (
            "Un pago tiene que ser mayor que cero. Escribe lo que de verdad ha salido de tu cuenta."
        ),
        "G4_un_pago_no_puede_aplicarse_mas_de_lo_que_se_debe": (
            "A «{concepto}» le faltan {pendiente} por pagar y has puesto {quiere}. Baja el importe "
            "hasta lo que se debe, o apunta primero lo que falte del gasto."
        ),
        "G5_ese_metodo_de_reparto_no_es_ninguno_de_los_cuatro": (
            "«{valor}» no es ninguna de las formas de repartir ({lista}). Elige una de la lista."
        ),
        "G6_no_se_puede_repartir_porque_falta_la_superficie": (
            "No se ha podido repartir porque a una de las tierras le falta la superficie, y sin ella "
            "no se sabe qué parte le toca. El gasto se ha quedado sin asignar: mira la superficie de "
            "la tierra y vuelve a repartirlo."
        ),
        "G7_el_reparto_a_mano_suma_mas_que_el_gasto": (
            "Lo que has repartido suma más de lo que costó el gasto. Repasa los importes: la suma no "
            "puede pasar de lo que costó."
        ),
        "G8_ese_pago_ya_no_tiene_dinero_libre": (
            "De ese pago ya está todo dicho a qué va. Si quieres cambiar a qué va, deshaz primero lo "
            "que tiene puesto."
        ),
        "G9_el_gasto_no_tiene_importe_y_no_se_puede_repartir": (
            "Este gasto no tiene importe, así que no se puede repartir: no se sabe cuánto llevar a "
            "cada sitio. Apunta lo que costó y vuelve a repartirlo."
        ),
        "G10_esa_forma_de_pago_no_es_ninguna_de_las_que_hay": (
            "«{valor}» no es ninguna de las formas de pago ({lista}). Elige una de la lista."
        ),
        "G11_ese_importe_no_cabe": (
            "Ese importe («{importe}») no cabe donde se guarda: parece un número de más al teclearlo. "
            "Míralo y vuelve a escribirlo."
        ),
        "G12_la_inversion_de_cero_euros_no_es_una_inversion": (
            "Una inversión de cero euros no es una inversión. Si no sabes lo que costó, deja el "
            "importe en blanco: se queda como que falta por saber."
        ),
        "G15_eso_no_es_un_importe": (
            "«{importe}» no es un importe. Escríbelo con números, por ejemplo 121,50."
        ),
        "G16_el_gasto_necesita_saber_que_es": (
            "Un gasto tiene que decir qué fue. Escribe dos o tres palabras —«gasóleo», «abono del "
            "trigo»— y guárdalo otra vez."
        ),
        "G17_el_gasto_se_ha_guardado_sin_importe": (
            "Se ha guardado, pero sin el importe: hasta que no sepas lo que costó, esta cuenta no "
            "entra en el margen. Apúntalo cuando tengas el papel."
        ),
        "G18_no_se_pueden_comprobar_las_cuentas": (
            "No se han podido comprobar las cuentas del papel porque falta {faltan}. Si lo tienes "
            "delante, apúntalo: el programa no lo supone."
        ),
        "G19_las_cuentas_del_gasto_no_cuadran": (
            "Las cuentas de este gasto no cuadran: la base más el IVA no da el total, se llevan "
            "{diferencia}. El programa guarda lo que has escrito, pero míralo en el papel."
        ),
        "G20_el_gasto_todavia_no_esta_en_ninguna_tierra": (
            "El gasto está apuntado y todavía no está en ninguna tierra: sigue contando en tus "
            "cuentas, pero aparece como sin asignar. Dile a qué va cuando puedas."
        ),
        "G21_eso_esta_anulado_y_no_se_corrige": (
            "Esto está anulado, así que no se puede corregir. Si te has equivocado al anularlo, "
            "apunta el gasto otra vez."
        ),
        "G22_para_anular_hace_falta_el_motivo": (
            "Para anularlo hace falta el motivo: dentro de un año, ese motivo es lo único que "
            "explicará por qué está tachado. Escríbelo y vuelve a pulsar el botón."
        ),
        "G23_su_gasto_se_anulo": "Su gasto se anuló",
        "G24_gasto_anulado": (
            "Anulado, con su motivo («{motivo}»). Sigue en tu cuaderno, tachado, y deja de contar en "
            "las cuentas."
        ),
        "G25_el_dinero_ha_vuelto_a_estar_sin_conciliar": (
            "El dinero que estaba puesto en este gasto ha vuelto a quedar sin decir a qué va ({cuantos} "
            "apuntes). Dilo cuando sepas a qué gasto va."
        ),
        "G26_eso_no_es_un_sitio_donde_repartir": (
            "«{valor}» no es un sitio donde se pueda repartir un gasto ({lista}). Elige uno de la "
            "lista."
        ),
        "G27_queda_parte_sin_asignar": (
            "Queda {importe} sin asignar: está apuntado y sigue contando en tus cuentas, pero "
            "todavía no va a ninguna tierra."
        ),
        "G28_el_reparto_no_cuadra": (
            "Este reparto no cuadra: hay {falta} del gasto que no están ni repartidos ni sin asignar. "
            "Repártelo otra vez para que la suma sea la del gasto."
        ),
        "G29_el_gasto_se_queda_sin_asignar_diciendolo": (
            "El gasto se queda sin asignar, y así se dice. Sigue contando en tus cuentas: solo falta "
            "decir a dónde va."
        ),
        "G30_la_inversion_necesita_saber_que_es": (
            "Una inversión tiene que decir qué es. Escribe dos o tres palabras —«tractor», «nave del "
            "grano»— y guárdala otra vez."
        ),
        "G31_esa_categoria_de_inversion_no_existe": (
            "«{valor}» no es ninguna de las categorías de inversión que hay ({lista}). Elige una de "
            "la lista."
        ),
        "G32_una_inversion_no_es_un_gasto_del_ano": (
            "Apuntada. Ojo con una cosa: su precio no entra entero en el año en que se compró. Dile "
            "qué parte le toca a cada campaña y lo que no digas se queda sin asignar."
        ),
        "G33_la_inversion_se_ha_guardado_sin_importe": (
            "Se ha guardado sin el importe. Mientras no sepas lo que costó, no se puede decir qué "
            "parte le toca a cada campaña."
        ),
        "G34_inversion_anulada": (
            "Anulada, con su motivo («{motivo}»). Sus repartos dejan de contar."
        ),
        "G35_hay_gastos_sin_importe_y_no_se_les_aplica_el_dinero": (
            "Hay {cuantos} gastos de los que no sabes el importe, así que este dinero no se les ha "
            "podido aplicar: no se sabe cuánto deben. Apunta lo que costaron y vuelve a decir a qué "
            "va este pago."
        ),
        "G36_una_parte_del_pago_queda_sin_conciliar": (
            "Se ha aplicado lo que se debía y quedan {importe} sin decir a qué van: están apuntados y "
            "esperando. Dilo cuando sepas contra qué gasto van."
        ),
        "G37_a_este_gasto_no_se_le_puede_aplicar_dinero_sin_saber_lo_que_costo": (
            "A «{concepto}» no se le puede aplicar dinero porque no se sabe lo que costó. Apunta "
            "primero su importe y después dile a qué va el pago."
        ),
        "G38_ese_pago_no_tiene_tanto_dinero_libre": (
            "De este pago solo quedan {libre} sin decir a qué van y has puesto {quiere}. Baja el "
            "importe o deshaz antes lo que tenga puesto."
        ),
        "G39_ese_pago_esta_anulado": (
            "Ese pago está anulado, así que no se le puede decir a qué va. Si te has equivocado al "
            "anularlo, apúntalo otra vez."
        ),
        "G40_el_pago_sigue_apuntado_y_sin_conciliar": (
            "Deshecho. El pago sigue apuntado con todo su importe y otra vez sin decir a qué va: el "
            "dinero no se ha borrado."
        ),
        "G41_pago_anulado": (
            "Pago anulado, con su motivo («{motivo}»). Los gastos que saldaba vuelven a estar "
            "pendientes."
        ),
        "G42_la_ayuda_necesita_saber_de_que_es": (
            "Una ayuda tiene que decir de qué es. Escribe dos o tres palabras —«ayuda a la cosecha de "
            "cereal»— y guárdala otra vez."
        ),
        "G43_una_ayuda_prevista_no_es_un_ingreso": (
            "Apuntada. Recuerda que una ayuda pedida o concedida **no es dinero que hayas cobrado**: "
            "no se suma a lo que ha entrado hasta que te la ingresen."
        ),
        "G44_ayuda_anulada": (
            "Anulada, con su motivo («{motivo}»). Deja de contar como ingreso."
        ),
        "G45_un_traspaso_a_la_misma_cuenta_no_es_un_traspaso": (
            "Ese traspaso sale y entra en la misma cuenta, así que no es un traspaso. Mira de qué "
            "cuenta sale y a cuál entra."
        ),
        "G46_faltan_importes_por_saber_uno": "Falta 1 importe por saber",
        "G46_faltan_importes_por_saber_varios": "Faltan {cuantos} importes por saber",
        "G47_gastos_sin_saber_a_donde_van_uno": "1 gasto sin saber a dónde va",
        "G47_gastos_sin_saber_a_donde_van_varios": "{cuantos} gastos sin saber a dónde van",
    }
)
```

Y en `textos_visibles()`, justo detrás de las tres líneas del T14, para que el test de jerga los revise:
```python
    # Las cuentas de la explotación (T13, E7, 05/10/2026): lo que ha costado, a qué va, cuánto se ha
    # pagado y qué falta por saber. Se recogen enteros, y con `_recoger` y no con `.values()` porque
    # dentro llevan cuatro diccionarios (las categorías, los métodos de reparto, las formas de pago y
    # los estados de una ayuda): con `.values()` esos textos llegarían al test de jerga como
    # diccionarios en vez de como frases, y son justo los que más se leen.
    textos.extend(_recoger(GASTOS))
```

**Y tres añadidos más a `textos.py`, que son de este ticket aunque no sean suyos los ficheros.** Los
dos primeros los pide el `app.js` del apartado 3.9 y **sin ellos la tabla de las cuentas sale sin
rótulos** (es el fallo que caza `test_que_no_falte_ningun_texto.py`: un texto que falta no revienta
nada, solo deja un hueco). El tercero son los títulos de columna, que van en `TABLA` como los de las
demás tablas.

```python
# 1) En `TABLA` (los nombres de las columnas de la tabla del ordenador). Son frases que lee el
#    agricultor, así que viven aquí y no en un componente:
    # **La tabla de las cuentas (T13, 05/10/2026).** La última columna, «Acciones», la pinta la pieza
    # (`piezas/tabla.js`) y por eso tiene su rótulo aunque su celda no la prepare `app.js`.
    "cuentas_concepto": "Qué fue",
    "cuentas_coste": "Lo que costó",
    "cuentas_va_a": "Va a",
    "cuentas_pagado": "Pagado",
    "cuentas_pendiente": "Falta por pagar",
    "cuentas_estado": "Cómo está",
    "cuentas_acciones": "Acciones",
    "cuentas_tierra": "Una tierra",
    "cuentas_cultivo": "Un cultivo",
    "resumen_cuentas": "{cuantas} gastos · {total} de coste conocido",
    "resumen_cuentas_uno": "1 gasto · {total} de coste conocido",
    "resumen_cuentas_filtrado": "{cuantas} de {total} gastos",

# 2) En `ACCIONES`, los títulos cortos que faltan para los botones nuevos (los que ya existen —volver,
#    corregir, borrar— se reutilizan y no hay que tocar nada):
    "ver_las_cuentas": "MIS CUENTAS",
```

> **Nota sobre la copia de los textos de las pruebas de JavaScript.** `tests_js/gastos.test.js` lleva
> una **copia literal** de `textos.GASTOS` (como `tests_js/maquinaria.test.js` con los del T14), con
> **las claves que el componente lee de verdad**: es la lista de arriba menos las que solo usa el
> servidor. Si al integrar cambia alguna frase, hay que cambiarla **en los dos sitios** o la copia
> miente. Lo ideal, y lo que hizo el T14, es añadir una prueba de backend que compare las dos
> (`tests/test_gastos.py` no la lleva porque su fichero de textos no lo escribe este ticket): el
> coordinador tiene el patrón en `tests/test_revision_t14.py`.

### 3.5 `backend/app/routers/interfaz.py` — el vocabulario servido

**Por qué:** la pantalla pide sus palabras a `/api/interfaz` y las guarda en el móvil. Sin esto,
`textos.gasto` llega vacío y la pantalla sale **sin una sola frase**.

```python
# Dentro del diccionario que devuelve `interfaz()`, detrás del bloque de la maquinaria (T14):
        # **Las cuentas de la explotación (T13, E7, 05/10/2026).** Las palabras de la pantalla nueva:
        # sus tarjetas, sus estados, sus cuatro métodos de reparto y sus frases de «no lo sé». Va
        # aquí —y no solo dentro de las respuestas de la API— por el mismo motivo que las del almacén
        # y las de la maquinaria: **esto se guarda en el móvil**, y las cuentas se miran en el
        # despacho y también de pie en la parcela, que es donde peor va la cobertura.
        #
        # Y hay una razón más, que es la del ticket: la pantalla tiene que poder decir **«no lo sé»**
        # aunque el servidor no conteste. Si esas frases vivieran solo en la respuesta, la pantalla se
        # quedaría muda justo en el caso que más importa.
        "gastos": textos.GASTOS,
        # Las cuatro listas cerradas, **con su orden y con su nombre**. El orden no se saca de las
        # claves del diccionario: unos botones que cambian de sitio se pulsan mal.
        "categorias_de_gasto": [
            {"valor": clave, "texto": textos.GASTOS["categorias_de_gasto"][clave]}
            for clave in gastos.CATEGORIAS_DE_GASTO
        ],
        "categorias_de_inversion": [
            {"valor": clave, "texto": textos.GASTOS["categorias_de_inversion"][clave]}
            for clave in gastos.CATEGORIAS_DE_INVERSION
        ],
        "metodos_de_reparto": [
            {"valor": clave, "texto": textos.GASTOS["metodos_de_reparto"][clave]}
            for clave in gastos.METODOS_DE_REPARTO
        ],
        "formas_de_pago": [
            {"valor": clave, "texto": textos.GASTOS["formas_de_pago"][clave]}
            for clave in ventas.FORMAS_DE_COBRO
        ],
        # Y lo que el programa **todavía no sabe calcular** de las cuentas (la amortización, el
        # extracto del banco y el resumen del IVA), con lo que es, para qué haría falta y de quién
        # depende. Sin esto, el agricultor creería que una cifra que no aparece es un fallo del
        # programa en vez de un dato que falta (la receta de `AGENTS.md`).
        "gastos_que_falta": list(gastos.QUE_FALTA),
```

Y en la cabecera del fichero, `gastos` en la lista de importaciones:

```python
from .. import catalogos, contactos, gastos, legal, maquinaria, semillas, sigpac, textos, ventas
```

### 3.6 `backend/app/routers/explotacion.py` — las tablas que cuelgan del año

**Por qué:** `test_todas_las_tablas_del_ano_estan_clasificadas` **se pone rojo** en cuanto existan las
tablas nuevas, porque tres de ellas llevan `campana_id`. Hay que decidir qué son, y lo que son es «las
demás cosas». Sin este cambio, la prueba avisa y el año contaría de más en silencio.

```python
    # **Las cuentas de la explotación (T13, E7, 05/10/2026).** Son la decimocuarta, la decimoquinta y
    # la decimosexta tabla que cuelgan del año, y la prueba `test_todas_las_tablas_del_ano_estan_clasificadas`
    # avisó de que había que decidir qué es (que es exactamente para lo que está). Decidido: **las
    # tres son «las demás cosas»**. No son apuntes del cuaderno —no son un trabajo ni un producto
    # echado— ni tierras con su cultivo dicho: son la cuenta de lo que costó el año.
    #
    #   · **`Gasto`**: lo que se consumió. Tiene que contar para el total, porque borrar el año se
    #     llevaría por delante sus cuentas y sus repartos quedarían apuntando al vacío.
    #   · **`InversionDeLaFinca`**: lo que se compró para durar. Cuenta también: aunque no entre
    #     entera en el margen del año, sí es una compra de ese año y su reparto a la campaña se
    #     perdería con él.
    #   · **`RepartoDeCoste`**: a dónde fue cada trozo. Cuenta por el mismo motivo que los dos de
    #     arriba.
    #
    # **El pago (`PagoDeGasto`) NO está aquí, y es la misma decisión que con el `Cobro`**: no cuelga
    # del año. El dinero sale un día y salda un gasto, y es el gasto quien tiene la campaña; colgarlo
    # del año obligaría a decidir de qué año es un pago de enero que salda la compra de diciembre, y
    # esa decisión no la tiene el programa.
    "Gasto",
    "InversionDeLaFinca",
    "RepartoDeCoste",
```

### 3.7 `backend/web/react/rutas.js` — las dos direcciones

**Por qué:** las dos pantallas se reconstruyen enteras al abrir su dirección (piden sus datos al
servidor), así que se pueden enlazar, recargar y mandar a quien ayuda. **Los tramos de texto fijo van
antes que los identificadores**, como en todas las familias de esta tabla.

```javascript
  // **Las cuentas de la explotación** (T13, 05/10/2026). La lista se reconstruye entera al abrir su
  // dirección —pide sus datos al servidor— y **la ficha de un gasto también** (se pide a su puerta),
  // así que las dos se pueden enlazar, recargar y mandar a quien ayuda. El tramo de texto fijo va
  // **antes** que el identificador, como en todas las familias de esta tabla: el día que exista
  // `#/cuentas/nuevo`, tiene que ir por encima de `#/cuentas/:id`.
  { clave: "gastos", patron: ["cuentas"] },
  { clave: "gasto", patron: ["cuentas", ":id"] },
```

*(Se pega detrás del bloque de `ventas`, antes de `medidas`.)*

### 3.8 `backend/web/service-worker.js` — la caché del campo

**Por qué:** un fichero de React que no está en la caché es un hueco en el campo: el agricultor abre
esa pantalla sin cobertura y no se dibuja. Hay una prueba que lo exige
(`test_la_migracion_a_react.py::test_todo_el_javascript_de_react_se_guarda_para_el_campo`).

```javascript
// 1) En la lista `FICHEROS`, junto a las demás pantallas:
  "/react/pantallas/gastos.js",
```

Y **subir el número de la caché en el mismo cambio** (el fichero lo explica donde está: sin subirlo, el
móvil se queda con la versión vieja). El comentario que hay que añadir al lado:

```javascript
// Y vigésimo cuarta, el 05/10/2026: **las cuentas de la explotación** (T13). Entra **un fichero con
// dos pantallas** —`gastos.js`: la lista de lo que ha costado, con sus tres columnas de coste, la
// caja, las inversiones, las ayudas y el margen; y la ficha de un gasto, con sus repartos y su
// cuadre—. Se guarda para el campo por el mismo motivo que las demás, y aquí con más razón: las
// cuentas se miran también de pie en la nave, y una cifra de dinero a medias es peor que ninguna.
```

### 3.9 `backend/web/app.js` — el menú, el enrutador y las 17 acciones

**Por qué:** sin esto la pantalla existe y no se llega a ella. Son seis trozos pequeños y un bloque de
manejador.

**a) La importación** (junto a las demás pantallas, detrás de la de maquinaria):

```javascript
// **Las cuentas de la explotación (T13, E7, 05/10/2026).** Un fichero con las dos pantallas del
// contrato: la lista (`#/cuentas`) y la ficha de un gasto (`#/cuentas/<id>`). Es un solo fichero
// porque las dos comparten las mismas piezas —la tarjeta de cifras, el cuadre del reparto y los
// formularios— y separarlas obligaría a copiarlas.
import { pantallaDeLasCuentas, pantallaDeUnGasto } from "./react/pantallas/gastos.js";
```

**b) En `PANTALLAS_EN_REACT`** (detrás de `"maquinaria"`):

```javascript
  // T13 (05/10/2026): las cuentas de la explotación. Un solo fichero (`gastos.js`) con las dos
  // pantallas: la lista con su tabla y la ficha de un gasto, que es donde se reparte a las tierras,
  // los cultivos y las máquinas. Va aquí, y en la caché del campo, por lo de siempre: las cuentas se
  // miran en el despacho y también de pie en la nave.
  "gastos",
```

**c) En `MODULOS`** (delante del renglón de los papeles):

```javascript
  // **Las cuentas (T13, 05/10/2026).** Va detrás de la maquinaria y delante de los papeles: es lo que
  // se mira cuando se quiere saber cómo va el año —lo que ha costado y lo que falta por pagar—, y no
  // al final, con lo que se toca una vez al año.
  { clave: "cuentas", texto: "gastos.titulo", accion: "gastos-ver" },
```

**d) En `RUTA_DE_LA_PANTALLA`** (el mapa de pantalla → clave de dirección):

```javascript
  // Las cuentas (T13, 05/10/2026): la lista coge la dirección de su renglón del menú (`#/cuentas`), y
  // **la ficha de un gasto tiene la suya** (`#/cuentas/12`), porque se puede enlazar y recargar: sus
  // repartos y sus pagos se piden al servidor al abrirla.
  PantallaDeUnGasto: "gasto",
```

**e) En `MODULO_DE_LA_PANTALLA`**:

```javascript
  // Las cuentas (T13): las dos pantallas cuelgan del renglón de las cuentas, que es de donde se llega
  // y donde el agricultor tiene que verse marcado.
  PantallaDeLasCuentas: "cuentas",
  PantallaDeUnGasto: "cuentas",
```

**f) Y el bloque del manejador de clics.** Es el trozo grande, y va **entero**: son las **17 acciones**

```javascript
// ---------------------------------------------------------------------------
// Las cuentas de la explotación (T13, E7, 05/10/2026)
// ---------------------------------------------------------------------------
//
// LO QUE ESTE BLOQUE HACE, Y LO QUE NO. Hace tres cosas y ninguna más:
//
//   1. **Pide los datos** a `GET /api/gastos` y los pasa a la pantalla, que no calcula nada.
//   2. **Recoge lo que el agricultor escribe** por los `id` de los campos y lo manda al servidor.
//   3. **Atiende las 17 acciones** de sus botones, una por una.
//
// Lo que **no** hace: ni una cuenta de dinero. Todos los importes, los repartos, los cuadres y los
// márgenes llegan calculados del servidor (`app/gastos.py`, con `Decimal`), porque en el navegador
// todo número es de coma flotante y el total de la pantalla dejaría de coincidir con el de la base
// por céntimos.

/** El estado de las cuentas, creado la primera vez que hace falta (como el del almacén). */
function estadoDeLasCuentas() {
  if (!estado.cuentas) {
    estado.cuentas = {
      // Lo que devolvió `GET /api/gastos`: las cinco listas, las tres columnas del coste, la caja,
      // los márgenes y lo que falta.
      datos: null,
      // La ficha de un gasto abierta (`GET /api/gastos/<id>`), o nada.
      gasto: null,
      // El formulario que está abierto: apuntar un gasto, repartirlo, apuntar un pago, una inversión
      // o una ayuda. `clase` dice cuál, y es lo que el botón de guardar manda al servidor.
      formulario: null,
      // El borrador: lo que el agricultor ha ido eligiendo (la categoría, el método de reparto, los
      // destinos). **Vive aquí y no en el DOM**: al repintar para enseñar una cosa nueva se perdería.
      borrador: null,
      anulando: null,
      filtro: "",
      guardando: false,
      error: "",
      aviso: "",
    };
  }
  return estado.cuentas;
}

/** El vocabulario de estas pantallas: el de las cuentas y los dos botones de corregir y borrar. */
function textosDeLasCuentas() {
  return {
    gasto: t("gastos", {}),
    acciones: accion("volver") ? { volver: accion("volver") } : {},
    tabla: t("tabla", {}),
  };
}

/** Abre «mis cuentas»: se pinta enseguida y se vuelve a pintar con lo que contesta el servidor. */
async function abrirLasCuentas() {
  const suyo = estadoDeLasCuentas();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.anulando = null;
  suyo.gasto = null;
  pantallaLasCuentas();
  await recargarLasCuentas();
  pantallaLasCuentas();
}

/** Vuelve a pedir las cuentas de la finca. */
async function recargarLasCuentas() {
  const suyo = estadoDeLasCuentas();
  const campana = campanaActual();
  const consulta = campana && campana.id ? `?campana_id=${campana.id}` : "";
  try {
    suyo.datos = await apiJson(`/api/gastos${consulta}`);
    suyo.error = "";
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo;
}

/** La lista de las cuentas, ya en React. */
function pantallaLasCuentas() {
  const suyo = estadoDeLasCuentas();
  const g = t("gastos", {});
  const datos = suyo.datos || {};
  const casan = (datos.gastos || []).filter((gasto) => {
    const busca = (suyo.filtro || "").toLocaleLowerCase("es");
    if (!busca) return true;
    return `${gasto.concepto || ""} ${gasto.proveedor || ""}`
      .toLocaleLowerCase("es")
      .includes(busca);
  });
  const cuantos = casan.length;
  return montar(() =>
    pantallaDeLasCuentas({
      textos: textosDeLasCuentas(),
      // El singular y el plural con las dos formas del servidor: «Tienes 1 gastos» es lo primero que
      // hace desconfiar de un programa.
      cuentas: { ...datos, gastos: casan },
      resumen: cuantos ? conCuenta(g, "cuantas", cuantos) : "",
      filtro: suyo.filtro,
      tabla: tablaDeLasCuentas(casan),
      formulario: elFormularioDeLasCuentas(suyo.formulario, suyo.borrador),
      anulando: suyo.anulando,
      guardando: suyo.guardando,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** La tabla del ordenador: una celda menos que columnas (la última, «Acciones», la pone la pieza). */
function tablaDeLasCuentas(gastos) {
  const g = t("gastos", {});
  const col = (clave) => t(`tabla.cuentas_${clave}`, "");
  const columnas = [
    { texto: col("concepto"), campo: "concepto" },
    { texto: col("coste") },
    { texto: col("va_a") },
    { texto: col("pagado") },
    { texto: col("pendiente") },
    { texto: col("estado") },
    { texto: col("acciones") },
  ];
  const filas = (gastos || []).map((gasto) => ({
    celdas: [
      {
        texto: gasto.concepto,
        accion: "gasto-abrir",
        datos: { id: gasto.id },
      },
      // **Un importe que no consta se enseña con su palabra, no con un cero.**
      { texto: gasto.importe ? gasto.texto_importe : g.no_se_sabe },
      {
        texto: gasto.repartos.length
          ? gasto.repartos.map((uno) => uno.etiqueta_destino || uno.destino).filter(Boolean).join(", ")
          : g.sin_asignar_corto,
        pista: gasto.esta_sin_repartir ? g.sin_asignar_explica : "",
      },
      { texto: gasto.texto_pagado },
      { texto: gasto.pendiente ? gasto.texto_pendiente : g.no_se_sabe },
      { texto: g[`estado_${gasto.estado}`] || "" },
    ],
    acciones: [],
  }));
  return {
    clave: "gastos",
    etiqueta: g.titulo,
    columnas,
    filas,
    resumen: filas.length
      ? rellena(t("tabla.resumen_cuentas", ""), {
          cuantas: filas.length,
          total: (estadoDeLasCuentas().datos || {}).coste_por_clase
            ? estadoDeLasCuentas().datos.coste_por_clase.texto_total_conocido
            : "",
        })
      : "",
  };
}

/** Abre la ficha de un gasto, pidiéndola a su puerta (`GET /api/gastos/<id>`). */
async function abrirUnGasto(id) {
  const suyo = estadoDeLasCuentas();
  if (!id) return abrirLasCuentas();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.anulando = null;
  let respuesta = null;
  try {
    respuesta = await api(`/api/gastos/${id}`);
  } catch (fallo) {
    respuesta = null;
  }
  if (!respuesta) {
    if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
    avisarDelError(mensaje("no_se_pudo"));
    return;
  }
  if (respuesta.status === 404) return pantallaDeDireccionQueNoLlevaANingunaParte();
  if (!respuesta.ok) {
    avisarDelError(mensaje("no_se_pudo"));
    return;
  }
  suyo.gasto = await respuesta.json();
  pantallaUnGasto();
}

/** La ficha de un gasto, ya en React. */
function pantallaUnGasto() {
  const suyo = estadoDeLasCuentas();
  const gasto = suyo.gasto || {};
  const susPagos = [];
  for (const pago of (suyo.datos || {}).pagos || []) {
    for (const aplicacion of pago.aplicaciones || []) {
      if (aplicacion.gasto_id !== gasto.id) continue;
      susPagos.push({
        id: pago.id,
        aplicacion_id: aplicacion.id,
        texto_importe: pago.texto_importe,
        texto_aplicado: aplicacion.texto_importe,
      });
    }
  }
  return montar(() =>
    pantallaDeUnGasto({
      textos: textosDeLasCuentas(),
      gasto,
      pagos: susPagos,
      formulario: elFormularioDeLasCuentas(suyo.formulario, suyo.borrador),
      repartiendo:
        suyo.formulario && suyo.formulario.clase === "reparto"
          ? elFormularioDeLasCuentas(suyo.formulario, suyo.borrador)
          : null,
      anulando: suyo.anulando,
      guardando: suyo.guardando,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/**
 * El formulario que está abierto, con sus bloques.
 *
 * **Los campos llevan su `id` y los botones de elegir su `campo`**: es lo único que este fichero
 * tiene para leer lo que el agricultor ha escrito. Y **ninguna pregunta nace contestada**: lo que no
 * haya elegido él va con `elegido: ""`, y la pantalla no marca ninguna opción.
 */
function elFormularioDeLasCuentas(cual, borrador) {
  if (!cual) return null;
  const g = t("gastos", {});
  const b = borrador || {};
  const opcionesDe = (lista, elegido) =>
    (lista || []).map((uno) => ({ valor: uno.valor, texto: uno.texto, elegido: uno.valor === elegido }));
  const base = {
    guardar: g.guardar,
    cancelar: g.cancelar,
    guardando: g.guardando,
    datos: { clase: cual.clase, id: cual.id || "" },
    bloques: [],
  };
  if (cual.clase === "gasto") {
    return {
      ...base,
      titulo: cual.id ? g.form_corregir_titulo : g.form_nuevo_titulo,
      pista: cual.id ? g.form_corregir_pista : g.form_nuevo_pista,
      bloques: [
        { tipo: "texto", id: "gasto-concepto", etiqueta: g.campo_concepto, pista: g.campo_concepto_pista, valor: cual.concepto || "" },
        {
          tipo: "opciones",
          campo: "categoria",
          etiqueta: g.campo_categoria,
          pista: g.campo_categoria_pista,
          elegido: b.categoria || cual.categoria || "",
          opciones: opcionesDe((estado.interfaz || {}).categorias_de_gasto, b.categoria || cual.categoria),
        },
        { tipo: "numero", id: "gasto-importe", etiqueta: g.campo_importe, pista: g.campo_importe_pista, valor: cual.importe || "" },
        { tipo: "numero", id: "gasto-base", etiqueta: g.campo_base, valor: cual.base_imponible || "" },
        { tipo: "numero", id: "gasto-cuota", etiqueta: g.campo_cuota, valor: cual.cuota_iva || "" },
        { tipo: "fecha", id: "gasto-fecha", etiqueta: g.campo_fecha, valor: cual.fecha || "" },
        { tipo: "fecha", id: "gasto-vencimiento", etiqueta: g.campo_vencimiento, pista: g.campo_vencimiento_pista, valor: cual.vencimiento || "" },
        { tipo: "texto", id: "gasto-proveedor", etiqueta: g.campo_proveedor, valor: cual.proveedor || "" },
      ],
    };
  }
  if (cual.clase === "reparto") {
    return {
      ...base,
      titulo: g.form_repartir_titulo,
      pista: g.form_repartir_pista,
      bloques: [
        {
          tipo: "opciones",
          campo: "metodo",
          etiqueta: g.campo_metodo,
          elegido: b.metodo || "",
          opciones: opcionesDe((estado.interfaz || {}).metodos_de_reparto, b.metodo),
        },
        {
          tipo: "opciones",
          campo: "destino_tipo",
          etiqueta: g.campo_destino,
          elegido: b.destino_tipo || "",
          opciones: [
            { valor: "tierra", texto: t("tabla.cuentas_tierra", ""), elegido: b.destino_tipo === "tierra" },
            { valor: "cultivo", texto: t("tabla.cuentas_cultivo", ""), elegido: b.destino_tipo === "cultivo" },
            { valor: "maquina", texto: t("maquinaria.titulo", ""), elegido: b.destino_tipo === "maquina" },
          ],
        },
        // Las horas o los litros de cada sitio: un campo por tierra elegida (los monta el borrador).
        ...(b.pesos || []).map((uno) => ({
          tipo: "numero",
          id: `gasto-peso-${uno.clave}`,
          etiqueta: uno.nombre,
          sufijo: b.metodo === "horas" ? g.campo_horas : g.campo_litros,
          valor: uno.valor || "",
        })),
      ],
    };
  }
  if (cual.clase === "pago") {
    return {
      ...base,
      titulo: g.form_pago_titulo,
      pista: g.form_pago_pista,
      bloques: [
        { tipo: "numero", id: "pago-importe", etiqueta: g.campo_importe, valor: "" },
        { tipo: "fecha", id: "pago-fecha", etiqueta: g.campo_fecha, valor: hoy() },
        { tipo: "texto", id: "pago-proveedor", etiqueta: g.campo_proveedor, valor: "" },
        {
          tipo: "opciones",
          campo: "forma",
          etiqueta: t("cobro.forma", ""),
          elegido: b.forma || "transferencia",
          opciones: opcionesDe((estado.interfaz || {}).formas_de_pago, b.forma || "transferencia"),
        },
      ],
    };
  }
  if (cual.clase === "inversion") {
    return {
      ...base,
      titulo: g.form_inversion_titulo,
      pista: g.form_inversion_pista,
      bloques: [
        { tipo: "texto", id: "inversion-concepto", etiqueta: g.campo_concepto, valor: "" },
        {
          tipo: "opciones",
          campo: "categoria",
          etiqueta: g.campo_categoria,
          elegido: b.categoria || "",
          opciones: opcionesDe((estado.interfaz || {}).categorias_de_inversion, b.categoria),
        },
        { tipo: "numero", id: "inversion-importe", etiqueta: g.campo_importe, pista: g.campo_importe_pista, valor: "" },
        { tipo: "fecha", id: "inversion-fecha", etiqueta: g.campo_fecha, valor: "" },
        { tipo: "texto", id: "inversion-proveedor", etiqueta: g.campo_proveedor, valor: "" },
      ],
    };
  }
  if (cual.clase === "ayuda") {
    return {
      ...base,
      titulo: g.form_ayuda_titulo,
      pista: g.form_ayuda_pista,
      bloques: [
        { tipo: "texto", id: "ayuda-concepto", etiqueta: g.campo_concepto, valor: "" },
        { tipo: "texto", id: "ayuda-organismo", etiqueta: g.campo_proveedor, valor: "" },
        { tipo: "numero", id: "ayuda-previsto", etiqueta: g.ayuda_prevista, valor: "" },
        { tipo: "numero", id: "ayuda-concedido", etiqueta: g.ayuda_concedida, valor: "" },
        { tipo: "numero", id: "ayuda-cobrado", etiqueta: g.ayuda_cobrada, valor: "" },
      ],
    };
  }
  return null;
}

/** Guarda lo que haya abierto, con la clase que diga el botón. */
async function guardarLasCuentas(datos) {
  const suyo = estadoDeLasCuentas();
  const clase = (datos && datos.clase) || "";
  const id = datos && datos.id ? Number(datos.id) : null;
  const b = suyo.borrador || {};
  const campos = (ids) => {
    const salida = {};
    for (const nombre of ids) salida[nombre] = valorDeLaCasilla(nombre);
    return salida;
  };
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaLasCuentas();
  let ruta = "/api/gastos";
  let cuerpo = {};
  let metodo = "POST";
  if (clase === "gasto") {
    const suyos = campos(["gasto-concepto", "gasto-importe", "gasto-base", "gasto-cuota", "gasto-fecha", "gasto-vencimiento", "gasto-proveedor"]);
    cuerpo = {
      concepto: suyos["gasto-concepto"],
      // **Un importe vacío viaja como `null`**, nunca como 0: es la regla del encargo de punta a punta.
      importe: suyos["gasto-importe"] || null,
      base_imponible: suyos["gasto-base"] || null,
      cuota_iva: suyos["gasto-cuota"] || null,
      fecha: suyos["gasto-fecha"] || null,
      vencimiento: suyos["gasto-vencimiento"] || null,
      proveedor: suyos["gasto-proveedor"],
      categoria: b.categoria || "otro",
      campana_id: campanaActual() ? campanaActual().id : null,
      clave_de_reenvio: claveDeReenvio("gasto"),
    };
    if (id) {
      metodo = "PUT";
      ruta = `/api/gastos/${id}`;
      delete cuerpo.clave_de_reenvio;
    }
  } else if (clase === "reparto") {
    metodo = "POST";
    ruta = `/api/gastos/${id}/repartos`;
    cuerpo = {
      metodo: b.metodo || "manual",
      destino_tipo: b.destino_tipo || "tierra",
      parcela_ids: b.parcela_ids || [],
      pesos: b.pesosRecogidos || {},
      trozos: b.trozos || [],
      confirmado: true,
    };
  } else if (clase === "pago") {
    cuerpo = {
      importe: valorDeLaCasilla("pago-importe"),
      fecha: valorDeLaCasilla("pago-fecha") || null,
      proveedor: valorDeLaCasilla("pago-proveedor"),
      forma: b.forma || "transferencia",
      clave_de_reenvio: claveDeReenvio("pago"),
      aplicaciones: b.aplicaciones || [],
    };
  } else if (clase === "inversion") {
    cuerpo = {
      concepto: valorDeLaCasilla("inversion-concepto"),
      importe: valorDeLaCasilla("inversion-importe") || null,
      fecha: valorDeLaCasilla("inversion-fecha") || null,
      proveedor: valorDeLaCasilla("inversion-proveedor"),
      categoria: b.categoria || "otro",
      campana_id: campanaActual() ? campanaActual().id : null,
      clave_de_reenvio: claveDeReenvio("inversion"),
    };
  } else if (clase === "ayuda") {
    cuerpo = {
      concepto: valorDeLaCasilla("ayuda-concepto"),
      organismo: valorDeLaCasilla("ayuda-organismo"),
      importe_previsto: valorDeLaCasilla("ayuda-previsto") || null,
      importe_concedido: valorDeLaCasilla("ayuda-concedido") || null,
      importe_cobrado: valorDeLaCasilla("ayuda-cobrado") || null,
      campana_id: campanaActual() ? campanaActual().id : null,
      clave_de_reenvio: claveDeReenvio("ayuda"),
    };
  }
  try {
    const respuesta = await api(ruta, { metodo, cuerpo });
    if (!respuesta.ok) {
      suyo.error = mensaje("no_se_pudo");
    } else {
      const contestado = await respuesta.json();
      suyo.aviso = (contestado.avisos || []).join(" ");
      suyo.formulario = null;
      suyo.borrador = null;
      await recargarLasCuentas();
    }
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  if (suyo.gasto) {
    await abrirUnGasto(suyo.gasto.id);
  } else {
    pantallaLasCuentas();
  }
}

/** Las 17 acciones de los botones de estas pantallas. */
async function atenderLasCuentas(nombre, elemento) {
  const suyo = estadoDeLasCuentas();
  const g = t("gastos", {});
  const id = Number(elemento.dataset.id || 0);
  if (nombre === "gastos-ver") return abrirLasCuentas();
  if (nombre === "gasto-abrir") return abrirUnGasto(id);
  if (nombre === "gastos-ver-todas") {
    suyo.filtro = "";
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-nuevo") {
    suyo.formulario = { clase: "gasto", id: id || null };
    suyo.borrador = {};
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-pago-nuevo") {
    suyo.formulario = { clase: "pago" };
    suyo.borrador = { aplicaciones: [] };
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-inversion-nueva") {
    suyo.formulario = { clase: "inversion" };
    suyo.borrador = {};
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-ayuda-nueva") {
    suyo.formulario = { clase: "ayuda" };
    suyo.borrador = {};
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-repartir") {
    suyo.formulario = { clase: "reparto", id };
    // Las tierras que se pueden elegir, con sus hectáreas: el servidor las leerá al repartir, y aquí
    // solo se ofrecen para que el agricultor diga a cuáles.
    suyo.borrador = { metodo: "", destino_tipo: "tierra", parcela_ids: [], pesos: [] };
    return pantallaUnGasto();
  }
  if (nombre === "gasto-sin-asignar") {
    suyo.guardando = true;
    pantallaUnGasto();
    try {
      const respuesta = await api(`/api/gastos/${id}/sin-asignar`, {
        metodo: "POST",
        cuerpo: { porque: "no_se_reparte_porque_no_ha_dicho_el_metodo" },
      });
      const contestado = await respuesta.json();
      suyo.gasto = contestado.gasto;
      suyo.aviso = (contestado.avisos || []).join(" ");
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    suyo.guardando = false;
    return pantallaUnGasto();
  }
  if (nombre === "gasto-reparto-quitar") {
    const reparto = Number(elemento.dataset.reparto || 0);
    try {
      const respuesta = await api(`/api/gastos/${id}/repartos/${reparto}`, { metodo: "DELETE" });
      const contestado = await respuesta.json();
      suyo.gasto = contestado.gasto;
      suyo.aviso = (contestado.avisos || []).join(" ");
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    return pantallaUnGasto();
  }
  if (nombre === "gasto-elegir") {
    // **El borrador vive aquí y no en el DOM**: al repintar se perdería, y el agricultor tendría que
    // volver a elegir lo que ya había elegido.
    const campo = elemento.dataset.campo || "";
    const valor = elemento.dataset.valor || "";
    suyo.borrador = { ...(suyo.borrador || {}), [campo]: valor };
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-guardar") return guardarLasCuentas(elemento.dataset);
  if (nombre === "gasto-cancelar") {
    suyo.formulario = null;
    suyo.borrador = null;
    suyo.anulando = null;
    suyo.error = "";
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-anular") {
    const clase = elemento.dataset.clase || "gasto";
    suyo.anulando = {
      titulo: `${g.anular} · ${clase === "pago" ? g.pagos_titulo : g.titulo}`,
      pista: g.anular_motivo,
      id: "gasto-motivo-anulacion",
      confirmar: g.anular_confirmar,
      cancelar: g.cancelar,
      datos: { id, clase },
      error: "",
    };
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-anular-confirmar") {
    // **Sin motivo no se anula**: dentro de un año, ese motivo es lo único que explicará por qué está
    // tachado. El servidor también lo exige; aquí se dice antes para no hacer el viaje.
    const motivo = (valorDeLaCasilla("gasto-motivo-anulacion") || "").trim();
    if (!motivo) {
      suyo.anulando.error = mensaje("G22_para_anular_hace_falta_el_motivo");
      return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
    }
    const clase = elemento.dataset.clase || "gasto";
    const rutaBase =
      clase === "pago"
        ? `/api/gastos/pagos/${id}/anular`
        : clase === "inversion"
          ? `/api/gastos/inversiones/${id}/anular`
          : clase === "ayuda"
            ? `/api/gastos/subvenciones/${id}/anular`
            : `/api/gastos/${id}/anular`;
    try {
      const respuesta = await api(rutaBase, { metodo: "POST", cuerpo: { motivo } });
      const contestado = await respuesta.json();
      suyo.aviso = (contestado.avisos || []).join(" ");
      suyo.anulando = null;
      if (clase === "gasto" && contestado.gasto) suyo.gasto = contestado.gasto;
      await recargarLasCuentas();
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    return suyo.gasto && clase === "gasto" ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-pago-conciliar") {
    // **Conciliar un pago no crea un gasto**: se dice contra qué va y ya está. Se reparte solo, por
    // orden y el más antiguo primero, que es la regla de cualquier cuenta corriente.
    const deudos = (suyo.datos.gastos || [])
      .filter((gasto) => gasto.pendiente && Number(gasto.pendiente) > 0)
      .map((gasto) => gasto.id);
    try {
      const respuesta = await api(`/api/gastos/pagos/${id}/conciliar`, {
        metodo: "POST",
        cuerpo: { automatico: true, gastos: deudos, aplicaciones: [] },
      });
      const contestado = await respuesta.json();
      suyo.aviso = (contestado.avisos || []).join(" ");
      await recargarLasCuentas();
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-pago-deshacer") {
    const aplicacion = Number(elemento.dataset.aplicacion || 0);
    try {
      const respuesta = await api(`/api/gastos/pagos/${id}/aplicaciones/${aplicacion}`, {
        metodo: "DELETE",
      });
      const contestado = await respuesta.json();
      suyo.aviso = (contestado.avisos || []).join(" ");
      await recargarLasCuentas();
      if (suyo.gasto) suyo.gasto = await apiJson(`/api/gastos/${suyo.gasto.id}`);
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  return false;
}
```

Y en el manejador de clics, **una sola línea** donde están las demás:

```javascript
  // Las cuentas de la explotación (T13, E7, 05/10/2026)
  const enLasCuentas = await atenderLasCuentas(nombre, elemento);
  if (enLasCuentas !== false) return enLasCuentas;
```

*(Y el despachador de direcciones: `case "gastos": return abrirLasCuentas();` y
`case "gasto": return abrirUnGasto(parametros.id);` donde estén los demás.)*

### 3.10 `docs/REACT.md` y los tres recuentos

**Por qué:** `test_la_migracion_a_react.py` exige que la guía lleve la fila de la pantalla nueva, y
`test_lista_de_la_junta.py` exige que los números de pruebas de los tres documentos sean los de verdad.

```markdown
# 1) En la tabla de pantallas de `docs/REACT.md`, una fila más:
| Cuentas y la ficha de un gasto (T13) | `pantallas/gastos.js` | ✅ En React |
```

```markdown
# 2) Y el número de pantallas migradas, escrito con letra, en `docs/REACT.md`
#    («veintiocho» → «veintinueve»).
```

```markdown
# 3) Los recuentos de pruebas, en los tres sitios a la vez (README.md, AGENTS.md y
#    docs/LO_QUE_PIDE_LA_JUNTA.md), CON EL NÚMERO MEDIDO Y NO CON EL QUE HABÍA:
#
#    JavaScript: el README decía 901 y **este fichero añade 26**. Ojo: el árbol tiene además 24 del
#    T15 (`tests_js/trabajos.test.js`), así que el número de verdad hay que volver a medirlo entero.
#    Medido hoy en este árbol: `node --test "tests_js/*.test.js"` cuenta 951 en los ficheros.
#
#    Python: el README decía 3960 y **este fichero añade 93** (`pytest tests/test_gastos.py
#    --collect-only` → 93). Medido hoy en este árbol: `pytest --collect-only` → 4235 recogidas
#    (con T15 y lo demás que hay en marcha). El número que se escriba tiene que ser el que dé la
#    suite entera **después** de integrarlo todo.
```

---

## 4. Lo que NO he podido comprobar, y por qué

1. **El recorrido por la API, de punta a punta: NO está comprobado.** Las **16 pruebas** que lo cubren
   (`TestElRecorridoDeUnGastoDePuntaAPunta` y `TestElCosteDeLasAveriasPorLaApi`) **se saltan**, y se
   saltan diciendo qué falta: `app/models.py` no tiene todavía las seis tablas y `app/schemas.py` no
   tiene sus esquemas. En cuanto se integren los apartados 3.1 y 3.2, esas 16 pruebas corren solas.
   **El router no se ha ejecutado ni una vez**: no puede importarse sin las tablas. Lo que sí está
   comprobado es que **compila** (`python -m py_compile`) y que sus etiquetas de auditoría caben en sus
   columnas (el guardián del rastro las lee con el parser).
2. **La pantalla no se ha visto en un navegador.** Está probada con `renderToStaticMarkup` (26 pruebas),
   que es lo que hacen las demás pantallas del proyecto, pero no se ha abierto con
   `scripts/comprobar_en_un_navegador.py` porque la ruta no existe hasta que se integre `app.js`.
3. **La tabla del ordenador** (`.solo-escritorio`) se pinta con la pieza compartida `Tabla`, y lo que se
   ha comprobado es que el contenedor y las dos vistas salen en el HTML. **Que las columnas quepan a
   1024 px no lo he medido**: eso se mide en el navegador, y no he podido.
4. **El reparto por horas y por consumo no se ha probado con datos reales de la finca.** La lógica pura
   sí (reparto por peso, con sus sumas exactas), pero los pesos los teclea el agricultor y el formulario
   que los recoge es del bloque de `app.js` que no se ha ejecutado.
5. **El traspaso entre cuentas propias (A07) se calcula pero NO se guarda.** No hay tabla de movimientos
   bancarios: es el ticket T20. Lo que sí está garantizado —y probado— es que **no se cuenta como
   ingreso ni como gasto**, que es el fallo que el caso A07 existe para impedir. Está declarado en
   `gastos.QUE_FALTA` y en el texto `el_traspaso_no_se_guarda`, que se enseña en la pantalla.
6. **La amortización no existe y no se ha inventado.** Sin una tabla de años de vida útil con fuente, la
   parte de una inversión que va a cada campaña la dice el agricultor. Hay una prueba que impide que
   alguien «arregle» el módulo metiendo una vida útil sin fuente.
7. **PostgreSQL no se ha probado.** Todo lo medido es sobre SQLite. Las columnas de dinero son `Dinero`
   (texto decimal canónico, exacto en los dos motores) y los textos llevan su tope leído del modelo,
   que es lo que evita el defecto de longitud que ya tumbó producción una vez; pero **eso no es lo
   mismo que haberlo corrido allí**.
8. **Tres guardianes están en rojo hasta integrar**, y son de integración, no del código: ver el
   apartado 2.4. Los tres se arreglan con los bloques del apartado 3.
9. **El árbol tiene dos escritores.** Mientras yo trabajaba apareció `web/react/pantallas/trabajos.js`
   (T15). Los rojos de `test_los_botones_hacen_algo.py` y del recuento de pruebas son **de los dos**, y
   por eso los números del apartado 3.10 hay que volver a medirlos después de integrar.
