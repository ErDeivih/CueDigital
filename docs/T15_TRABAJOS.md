# T15 — Trabajos por tierra, historial y estado derivado (S03/S04/S05)

> **Ticket:** T15 / E9 (dependencias T05, T09 y T14, cerradas). **Fecha:** 05/10/2026.
> **Qué entrega, en una frase:** la lógica de los trabajos por tierra —**previsto frente a realizado**, el
> historial de una tierra y su estado derivado— con las reglas del encargo escritas y probadas; la pantalla
> de la agenda, la ficha de un trabajo y la historia de una tierra en React; y el router `/api/trabajos`.
>
> **Puesto al día el 07/10/2026.** Aquí decía que el router estaba «escrito y todavía no ejecutable»,
> esperando las tablas, los esquemas y los textos del coordinador. **Eso ya está integrado y el router se
> ejecuta**: la revisión del recorrido lo comprobó (`pytest tests/test_trabajos.py -q -rs` → **77 pasan,
> 0 saltan**), y el recorrido entero —planificar, marcar lo hecho, historial, existencias y anular— está
> probado contra la API **y andado en un navegador de verdad** (`scripts/comprobar_el_recorrido.py`,
> 14 comprobaciones). Los apartados §3 y §4 se dejan como están, con su fecha: son el registro de lo que se
> integró y de lo que entonces no se pudo comprobar; lo que no se podía dejar era la frase de arriba, que
> dejó de ser verdad.

---

## 1. Lo que funciona

### 1.1 Las cuatro reglas del encargo, cada una con su prueba

| Regla | Cómo está cumplida | Dónde |
|---|---|---|
| **Un trabajo previsto no consume existencias ni acredita trabajo hecho** | Lo previsto vive en **su propia tabla** y su estado nunca se confunde con un hecho. `consume_existencias()` devuelve `(False, TJ1)` para un plan y `(False, TJ2)` para un trabajo **del que no consta si se hizo**: lo que no se sabe no se supone en ninguna dirección. Y lo que un plan gastaría se enseña como **estimación** (`dosis × hectáreas`), con `consume_existencias: False` escrito en el dato | `trabajos.consume_existencias`, `trabajos.estimacion_de_lo_previsto`, `test_un_trabajo_previsto_no_consume_existencias`, `test_un_plan_de_siembra_no_anade_una_labor_hecha` (A05) |
| **Un rodillo después de sembrar no borra el estado de siembra** | El cultivo que se enseña sale de **la última siembra o plantación que cuenta y de nada más** (`cambia_el_cultivo`): solo `siembra` y `plantacion` cambian el estado. Un apero detrás de una siembra se apunta, sale en el historial, **y no toca lo sembrado** —y la pantalla lo explica con su frase (`TJ8`) | `trabajos.cambia_el_cultivo`, `estado_de_una_tierra`, `test_un_rodillo_despues_de_sembrar_no_borra_el_estado_de_siembra` (A04) |
| **Una lluvia no acredita nascencia ni salud del cultivo** | La lluvia es un **hecho del tiempo**, no un trabajo: sale en el historial y no suma hectáreas. La nascencia **solo** sale de una observación de alguien que la ha visto; si ha llovido y nadie ha mirado, la nascencia es `None` con su frase (`TJ7`). Y después de la cosecha no se afirma que la tierra quedó vacía: `en_el_suelo` es `None` hasta que alguien lo diga (`TJ15`) | `trabajos.HECHOS_DEL_TIEMPO`, `estado_de_una_tierra`, `test_una_lluvia_no_acredita_nascencia`, `test_la_cosecha_no_dice_que_la_tierra_quedo_vacia` |
| **Anular o corregir no duplica consumos y no toca lo firmado** | Una salida del almacén cuenta solo si **su apunte acredita trabajo hecho**, no está anulada ella misma y no es la segunda del mismo apunte y envase. Anular hace que la salida **deje de contar sin tocar el libro**; corregir **anula la vieja y apunta la nueva** (nunca dos vivas, nunca una cantidad reescrita por detrás). Un apunte firmado **no se borra** (se anula) y corregirlo es **una revisión nueva** con la firma antigua intacta y `bytes_identicos` (A14) | `trabajos.consumos_que_cuentan`, `anular`, `corregir`, `se_puede_borrar`, `test_anular_no_duplica_consumos`, `test_corregir_lo_que_salio_anula_la_salida_vieja_y_apunta_la_nueva`, `test_corregir_lo_firmado_es_una_revision_nueva_y_la_firma_sigue_valiendo` |

### 1.2 Lo que se puede hacer hoy, ya probado

| Qué | Dónde | Prueba |
|---|---|---|
| **Planificar un trabajo**: tipo, subtipo de labor de suelo, tierra o grupo, día previsto, hectáreas previstas, horas previstas, máquina, responsable y lo que hará falta | `trabajos.un_previsto`, `estimacion_de_lo_previsto` | `test_lo_que_gastaria_lo_previsto_se_dice_como_estimacion`, `test_sin_hectareas_no_se_estima_nada_y_se_dice_lo_que_falta` |
| **Marcar lo que de verdad se hizo**, con su día, sus hectáreas, sus horas y lo que se gastó —y compararlo con lo que se había pensado— | `trabajos.marcar_como_hecho`, `lo_previsto_y_lo_hecho` | `test_un_plan_no_se_marca_hecho_dos_veces`, `test_lo_previsto_y_lo_hecho_se_emparejan_solo_por_el_vinculo` |
| **El historial de una tierra**: **todos** los eventos por orden, con lo anulado dentro (tachado y con su motivo), diciendo de cada línea si cuenta, si gasta y **qué cambió** en lo que hay sembrado | `trabajos.historial_de_una_tierra` | `test_el_historial_tiene_los_dos_eventos_y_el_cultivo_permanece`, `test_anular_deja_el_apunte_en_el_historial_con_su_motivo`, `test_un_trabajo_sin_fecha_no_se_tira` |
| **El estado derivado**: qué tiene sembrado, qué se ha hecho, qué queda previsto, y —separado, como pide el contrato— la última labor, el cultivo declarado, las observaciones de campo y las estimaciones | `trabajos.estado_de_una_tierra` | `test_el_historial_y_el_estado_sacan_las_mismas_cifras`, `test_anular_una_siembra_devuelve_el_estado_a_lo_de_antes` |
| **Reprogramar**: mover un plan de día dejando escrito el día que tenía; **y no se puede reprogramar lo que ya se hizo** (`TJ9`) | `trabajos.reprogramar` | `test_no_se_reprograma_un_trabajo_ya_hecho`, `test_reprogramar_conserva_la_fecha_de_antes` |
| **Corregir** un hecho en la misma fila, con `[antes, ahora]` campo por campo, y moviendo el almacén **solo** si cambia lo que salió | `trabajos.corregir` | `test_corregir_deja_lo_que_decia_antes_campo_por_campo`, `test_corregir_unas_horas_no_toca_el_almacen` |
| **Anular** con motivo (obligatorio, tres letras), devolviendo al almacén lo que salió **sin tocar el libro**, y sin que anular dos veces haga nada nuevo | `trabajos.anular` | `test_anular_sin_motivo_no_se_hace`, `test_anular_dos_veces_no_duplica_ni_el_motivo_ni_la_devolucion` |
| **Reenviar desde el móvil no duplica nada**: la clave de reenvío deja un trabajo y una salida, y lo que no se puede comprobar (sin clave) **se dice** (`TJ12`) | `trabajos.quita_los_reenvios` | `test_reenviar_desde_el_movil_no_duplica_trabajos` (A12), `test_dos_salidas_del_mismo_apunte_y_envase_cuentan_una` |
| **Datos ausentes ≠ cero**, con las dos reglas de la casa: en un panel se suma **lo que consta** y se dice cuántos huecos hay; en un **saldo** no se da a medias (`None` y el motivo) | `trabajos.sumando_lo_que_se_sabe`, `saldo_de_los_consumos` | `test_sumar_lo_que_se_sabe_no_convierte_los_huecos_en_ceros`, `test_un_saldo_no_se_da_a_medias`, `test_las_hectareas_que_faltan_se_cuentan_aparte_y_se_dicen` |
| **El cuaderno y los paneles, los mismos hechos**: hay **una sola** cuenta de hectáreas, horas e insumos, y el historial y el estado la llevan dentro tal cual | `trabajos.cifras_de_una_tierra` | `test_el_historial_y_el_estado_sacan_las_mismas_cifras` (con un anulado, un hueco, una lluvia y un trabajo sin tierra dentro) |
| **Lo que no se sabe, declarado en el dato**: la fuente de lluvia y la nascencia medida (T17/T18), las horas del cuenta-horas y los costes (T13) | `trabajos.QUE_FALTA` | `test_lo_que_no_se_puede_saber_se_declara_en_el_propio_dato` |

### 1.3 Las tres decisiones que sostienen todo lo demás

1. **«No consta» es un estado, y es distinto de «no».** `estado` vale `previsto`, `en_curso`,
   `realizado`, `cancelado` **y `None`**. Lo ausente no se rellena por ningún lado: un trabajo sin estado
   declarado no acredita trabajo hecho, no gasta y sale en la lista de lo que no se sabe.
   > Y aquí está el defecto que el ticket avisa: **una columna `estado` en la tabla de labores con el
   > valor por defecto «previsto» convertiría en planificado todo el cuaderno que el agricultor ya tiene
   > apuntado** (esos apuntes son hechos: los apuntó pulsando «HE SEMBRADO»). Por eso lo previsto vive en
   > **su propia tabla** y `Labor` no lleva `estado`. El único sitio donde «realizado» se pone sin que
   > nadie lo haya escrito es `trabajos.un_hecho`, que es quien lee la tabla de labores, y está escrito
   > allí con su motivo.
2. **Lo previsto y lo hecho se emparejan solo cuando alguien lo dice** (`previsto_id`). Emparejar por
   «misma tierra y mismo tipo en fechas parecidas» sería adivinar, y la adivinación aquí daría por hecho
   un trabajo que no se hizo (A05).
3. **Las cifras salen de un solo sitio.** `cifras_de_una_tierra` es la única cuenta del módulo, y hay una
   prueba que se pone roja si alguien suma por su cuenta en otra parte.

### 1.4 Las tres pantallas (React, sin compilar)

| Pantalla | Qué enseña |
|---|---|
| **La agenda** (`PantallaDeLosTrabajos`) | **Dos listas separadas con dos títulos**: «Lo que tengo pensado hacer» (con lo que gastaría, como estimación, y la frase que dice que **no ha gastado nada**) y «Lo que he hecho» (con su día, su tierra, sus huecos dichos como huecos y los anulados dentro, tachados y con su motivo). Botones: planificar, marcar hecho, cambiar de día, cancelar, corregir y anular |
| **La ficha de un trabajo** (`PantallaDeUnTrabajo`) | Cinco modos con **cinco acciones distintas**: `planificar`, `reprogramar`, `hecho`, `corregir` y `anular`. Al marcar lo hecho, **lo que se había pensado se enseña al lado**. En `reprogramar` solo se puede tocar el día. En `anular` solo se escribe el motivo |
| **La historia de una tierra** (`PantallaDeLaTierra`) | Qué hay hoy (lo sembrado, la última labor), el historial completo —con lo anulado y lo corregido—, **lo previsto aparte de lo hecho**, lo que no consta con su explicación y las observaciones de campo |

Las tres pantallas **no calculan nada** (las cifras llegan contadas del servidor), **no llevan ni una frase
escrita a mano** (todas vienen de `textos.py` por propiedades) y **no tocan el navegador**.

---

## 2. Cómo se ha comprobado (los comandos y los números)

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests/test_trabajos.py -q
node --test "tests_js/trabajos.test.js"
```

| | Medido (05/10/2026) |
|---|---|
| `tests/test_trabajos.py` | **68 en verde, 2 saltadas** (las dos con su motivo escrito: §4) **→ el 07/10/2026, 77 en verde y 0 saltadas**, porque lo que faltaba está integrado |
| `tests_js/trabajos.test.js` | **24 en verde, 0 en rojo** |
| Los tres ficheros compilan | `python -m py_compile app/trabajos.py app/routers/trabajos_api.py tests/test_trabajos.py` → sin error |
| El router dice lo que le falta | la prueba `test_las_puertas_del_router_se_ejecutan_cuando_este_integrado` se salta y **cuenta el motivo exacto**: `ImportError: cannot import name 'MarcarHechoEntrada' from 'app.schemas'` **→ ya no se salta: el router se ejecuta y el recorrido entero está probado contra la API y andado en el navegador** |
| Los guardianes del proyecto que leen mis ficheros | **996 pruebas en verde**; las únicas rojas son las cinco de §2.2, y todas son de la integración pendiente, no del código del ticket |

### 2.1 Pruebas que muerden (hechas, vistas y deshechas)

El encargo pide comprobar que las pruebas **muerden**. Se ha roto el código a propósito, seis veces, se ha
mirado el rojo y se ha dejado como estaba:

| Lo que rompí | Qué se puso rojo | Vuelto a dejar bien |
|---|---|---|
| `cambia_el_cultivo` devolviendo «sí» a cualquier trabajo (un rodillo que borra la siembra) | **7 pruebas**: las cinco de `TestUnAperoNoCambiaLoSembrado`, la de la cosecha y la del tipo que no existe | Sí |
| `consume_existencias` devolviendo «sí» siempre (lo previsto gasta) | **3 pruebas**: la del previsto que no consume, la del estado que no consta y la de lo que está en curso | Sí |
| Deducir la nascencia de la lluvia (`nascencia: True` cuando hay lluvia) | **1 prueba**: `test_una_lluvia_no_acredita_nascencia`, la que el encargo nombra | Sí |
| `consumos_que_cuentan` contando también lo anulado | **1 prueba**: `test_anular_no_duplica_consumos`, la que el encargo nombra | Sí |
| `normaliza_trabajo` con `superficie_ha or 0` (un hueco convertido en cero) | **4 pruebas**: las tres de «lo que no se sabe no es cero» y la de las mismas cifras | Sí |
| La pantalla pintando `trabajo-hecho-guardar` en el modo de planificar | **2 pruebas** de JavaScript: la que exige que planificar no apunte un trabajo hecho, y la del catálogo de acciones | Sí |

Después de cada vuelta atrás se ha corrido la suite entera del ticket: **68 + 24, en verde**.

### 2.2 Y las pruebas que se ponen rojas **hasta que se integre**, dichas con nombre y apellido

Esto no es un descuido: el mapa de ficheros del ticket dice que `models.py`, `schemas.py`, `main.py`,
`textos.py` y `web/app.js` los integra el coordinador, y **tres guardianes del proyecto leen esos
ficheros**. Los he medido uno por uno, con el resultado exacto:

| Guardián | Qué dice hoy | Qué hay que hacer |
|---|---|---|
| `test_los_botones_hacen_algo.py::test_cada_accion_que_se_pinta_la_atiende_alguien` | lista **mis 12 acciones** como «botones que se pintan y no hacen nada»: `trabajo-abrir`, `trabajo-anular`, `trabajo-anular-confirmar`, `trabajo-cancelar`, `trabajo-corregir`, `trabajo-guardar`, `trabajo-hecho`, `trabajo-hecho-guardar`, `trabajo-planificar`, `trabajo-previsto-guardar`, `trabajo-reprogramar`, `trabajos-ver` | atenderlas en el manejador de clics de `app.js` (§3.6, con lo que tiene que hacer cada una) |
| `test_la_migracion_a_react.py::test_el_codigo_y_los_ficheros_cuadran` | `hay ficheros de pantalla que no están en PANTALLAS_EN_REACT: ['gastos', 'trabajos']` | añadir `"trabajos"` a `PANTALLAS_EN_REACT` (§3.6). **`gastos` no es mío**: es del T13, que va en paralelo |
| `test_la_migracion_a_react.py::test_todo_el_javascript_de_react_se_guarda_para_el_campo` | `NO se guardan para abrir sin cobertura: ['/react/pantallas/gastos.js', '/react/pantallas/trabajos.js']` | añadirlo a `FICHEROS` del service-worker y subir la caché (§3.7) |
| `test_la_migracion_a_react.py::test_el_informe_de_la_migracion_se_puede_contar` | `las cuentas no cuadran: {"migradas": 49, "con_fichero": 51, "en_la_guia": 49, "en_la_cache": 49}` | la fila de `docs/REACT.md` y la caché (§3.7, §3.8) |
| `test_lista_de_la_junta.py::test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos` | `la documentación dice 901 pruebas de JavaScript y hay 951` | alinear los recuentos (§3.9) |

**Y cuatro guardianes que he corrido y que NO se ponen rojos con mis ficheros** (importa decirlo, porque
era lo que había que comprobar): `test_ficheros_de_texto.py` (mis seis ficheros nuevos son UTF-8 sin marca
de orden de bytes), `test_que_no_falte_ningun_texto.py` (la pantalla no pide ninguna clave que no exista:
las frases llegan por propiedades), `test_las_etiquetas_del_rastro_caben.py` (mis etiquetas del rastro son
textos fijos y cortos) y `test_sin_jerga.py`.

---

## 3. Cambios que hay que integrar

Todo lo de este apartado es de ficheros que **no son míos**. Los bloques van literales, para copiarlos.

### 3.1 `backend/app/models.py` — dos tablas nuevas y tres columnas

Se añade al final del bloque de labores (después de `class Labor`, antes de `class Auditoria`):

```python
class TrabajoPrevisto(Base):
    """**Un trabajo PLANIFICADO**: lo que se piensa hacer, no lo que se ha hecho.

    POR QUÉ ESTA TABLA EXISTE, Y POR QUÉ NO ES UNA COLUMNA DE `Labor`

    Lo previsto y lo hecho son dos cosas distintas y el encargo lo dice con todas las letras: *un
    trabajo previsto no consume existencias ni acredita trabajo hecho*. La forma de que eso no se pueda
    confundir es que **vivan en tablas distintas**: una fila de `labores` es un hecho por construcción
    (el agricultor apunta ahí lo que ya ha pasado), y una fila de aquí es un plan.

    Y por eso `Labor` **no** lleva una columna `estado`: con un valor por defecto «previsto», todos los
    apuntes que el agricultor ya tiene en su cuaderno —que son hechos— pasarían a leerse como
    planificados. Es exactamente el defecto que este ticket persigue (`app/trabajos.py` lo explica).

    Lo que sí puede pasar: `estado` aquí admite vacío (`None` = «no consta»), y la lógica pura no lo
    toma ni por previsto ni por hecho.
    """

    __tablename__ = "trabajos_previstos"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int] = mapped_column(ForeignKey("campanas.id"), index=True)

    tipo: Mapped[str] = mapped_column(String(30), index=True)
    # El apero, para las labores de suelo: rodillo, cultivador, arado, grada… Es un dato del contrato
    # (§4, S05) y va en su columna, no en un JSON, por la regla de la casa: un dato con nombre y número
    # tiene que poder consultarse y sumarse.
    subtipo: Mapped[str | None] = mapped_column(String(30))
    # **Sin valor por defecto, y es una decisión**: lo pone quien crea el plan, a la vista, para que
    # ninguna puerta futura pueda convertir en «previsto» algo que nadie ha dicho. Vacío es «no consta».
    estado: Mapped[str | None] = mapped_column(String(20), index=True)

    fecha_prevista: Mapped[dt.date | None] = mapped_column(Date, index=True)
    fecha_fin_prevista: Mapped[dt.date | None] = mapped_column(Date)
    # El día que tenía antes de moverlo: cambiar una fecha sin dejar la anterior es de las cosas que
    # después nadie puede explicar.
    fecha_prevista_antes: Mapped[dt.date | None] = mapped_column(Date)

    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupos_parcelas.id"))
    superficie_ha: Mapped[float | None] = mapped_column(Float)
    cultivo: Mapped[str | None] = mapped_column(String(120))
    variedad: Mapped[str | None] = mapped_column(String(120))
    equipo_id: Mapped[int | None] = mapped_column(ForeignKey("equipos_aplicacion.id"))
    persona: Mapped[str | None] = mapped_column(String(120))
    # Las horas que se **piensan** estar. No son las que se estuvo: hasta que el trabajo se haga, esto
    # es una previsión y se enseña como tal.
    horas_previstas: Mapped[float | None] = mapped_column(Float)

    observaciones: Mapped[str | None] = mapped_column(Text)
    # El motivo de cancelarlo, cuando se cancela. Un plan cancelado no se borra: queda y se explica.
    motivo_cancelacion: Mapped[str | None] = mapped_column(Text)

    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120), index=True)

    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    lineas: Mapped[list["LineaDeTrabajoPrevisto"]] = relationship(
        back_populates="trabajo", cascade="all, delete-orphan"
    )


class LineaDeTrabajoPrevisto(Base):
    """Una tierra de un trabajo planificado, **con su cantidad dicha**.

    El contrato (§4, S04) pide que un trabajo de varias tierras tenga «cabecera y líneas por tierra, con
    cantidades asignadas explícitas» y dice, con esas palabras, que **no se reparta automáticamente el
    total por igual**: repartirlo sería inventarse lo que se va a hacer en cada tierra. Por eso cada
    línea lleva su superficie, su cantidad y sus horas, y lo que no se sepa se queda vacío.
    """

    __tablename__ = "lineas_de_trabajo_previsto"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    trabajo_previsto_id: Mapped[int] = mapped_column(
        ForeignKey("trabajos_previstos.id", ondelete="CASCADE"), index=True
    )
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcelas.id"), index=True)
    superficie_ha: Mapped[float | None] = mapped_column(Float)
    cantidad: Mapped[float | None] = mapped_column(Float)
    unidad: Mapped[str | None] = mapped_column(String(10))
    dosis_por_ha: Mapped[float | None] = mapped_column(Float)
    articulo_id: Mapped[int | None] = mapped_column(ForeignKey("articulos.id"))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id"))
    horas: Mapped[float | None] = mapped_column(Float)
    observaciones: Mapped[str | None] = mapped_column(Text)

    trabajo: Mapped["TrabajoPrevisto"] = relationship(back_populates="lineas")
```

Y **tres columnas (y una cuarta opcional) en `class Labor`**, porque el router lee y escribe ahí:

```python
    # ── Lo que el T15 necesita de una labor (05/10/2026) ──────────────────
    #
    # El subtipo de una labor de suelo (rodillo, cultivador, arado…). El contrato lo pide con nombre y
    # número (§4, S05) y `detalles` es un JSON donde no se puede consultar ni sumar. **Mientras no
    # exista, el router lo lee de `detalles`**, así que se puede dejar fuera; lo que no se puede es
    # dejar fuera las tres de abajo.
    subtipo: Mapped[str | None] = mapped_column(String(30))
    # Las horas que se estuvo. Los «medios» de un trabajo las piden (§4, S04/S05) y hasta ahora no había
    # dónde apuntarlas: van en `detalles`, que no se puede sumar ni volcar. Vacío es «no se sabe».
    horas: Mapped[float | None] = mapped_column(Float)
    # La clave del móvil, como en los tratamientos, los albaranes y los movimientos: **es lo que impide
    # que la cola del móvil apunte el mismo trabajo dos veces** (A12) y que descuente dos veces.
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120), index=True)
    # Qué trabajo planificado cumplió esta labor, cuando alguien lo ha dicho. **No se empareja por
    # parecido**: el vínculo lo dice el agricultor (A05).
    previsto_id: Mapped[int | None] = mapped_column(ForeignKey("trabajos_previstos.id"), index=True)
```

> **Y lo que NO hay que añadir**: una columna `estado` en `Labor`. Está explicado arriba y en
> `app/trabajos.py`: un valor por defecto convertiría en planificado el cuaderno entero del agricultor.
> Las tres columnas de arriba son anulables, así que `crear_tablas()` las añade sola en las instalaciones
> que ya existen (`AGENTS.md` §3.9), y no hay ninguna reconstrucción de tabla pendiente.

### 3.2 `backend/app/schemas.py` — seis esquemas de entrada

No hay esquemas de **salida** a propósito: lo que devuelve este router es lo que dice la lógica pura
(`trabajos.py`), que ya está tipado y probado allí. Si el coordinador prefiere `response_model`, los seis
de abajo son la mitad del trabajo; los de salida son `TrabajoSalida` y `TrabajoPrevistoSalida` con los
mismos campos que los diccionarios de `normaliza_trabajo`.

```python
# --------------------------------------------------------------------------
# Los trabajos por tierra (T15, 05/10/2026)
# --------------------------------------------------------------------------


class InsumoDeUnTrabajoEntrada(EntradaBase):
    """Lo que un trabajo gasta de un envase, o lo que se piensa gastar.

    `cantidad` y `unidad` son opcionales: lo que no se sabe **no se resta** (se dice por qué), y un total
    inventado aquí sería un descuento que nadie ha hecho.
    """

    articulo_id: int | None = None
    lote_id: int | None = None
    cantidad: float | None = Field(default=None, gt=0)
    unidad: str | None = None
    # Para lo previsto: lo de cada hectárea, que es lo que permite estimar el total sin confundirlo con él.
    dosis_por_ha: float | None = Field(default=None, ge=0)
    aceptar_descuadre: bool = False


class TrabajoEntrada(EntradaBase):
    """Un trabajo **hecho**: lo que pasó, con su día y lo que se gastó de verdad."""

    campana_id: int
    tipo: str
    subtipo: str | None = None
    fecha: dt.date
    parcela_id: int | None = None
    grupo_id: int | None = None
    superficie_ha: float | None = Field(default=None, ge=0)
    cultivo: str | None = None
    variedad: str | None = None
    equipo_id: int | None = None
    horas: float | None = Field(default=None, ge=0)
    observaciones: str | None = None
    insumos: list[InsumoDeUnTrabajoEntrada] | None = None
    previsto_id: int | None = None
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class TrabajoPrevistoEntrada(EntradaBase):
    """Un trabajo **planificado**. Todo lo que no se sepa se queda en blanco."""

    campana_id: int
    tipo: str
    subtipo: str | None = None
    fecha_prevista: dt.date | None = None
    fecha_fin_prevista: dt.date | None = None
    parcela_id: int | None = None
    grupo_id: int | None = None
    superficie_ha: float | None = Field(default=None, ge=0)
    cultivo: str | None = None
    variedad: str | None = None
    equipo_id: int | None = None
    persona: str | None = None
    horas: float | None = Field(default=None, ge=0)
    observaciones: str | None = None
    lineas: list["LineaDeTrabajoPrevistoEntrada"] | None = None
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class LineaDeTrabajoPrevistoEntrada(EntradaBase):
    """Una tierra del plan, con **su cantidad dicha**. No se reparte el total por igual."""

    parcela_id: int
    superficie_ha: float | None = Field(default=None, ge=0)
    cantidad: float | None = Field(default=None, ge=0)
    unidad: str | None = None
    dosis_por_ha: float | None = Field(default=None, ge=0)
    articulo_id: int | None = None
    lote_id: int | None = None
    horas: float | None = Field(default=None, ge=0)
    observaciones: str | None = None


class MarcarHechoEntrada(EntradaBase):
    """Lo que de verdad se hizo, cuando se cumple un plan. **El plan no se copia: se apunta el hecho.**"""

    fecha: dt.date
    superficie_ha: float | None = Field(default=None, ge=0)
    cultivo: str | None = None
    variedad: str | None = None
    equipo_id: int | None = None
    horas: float | None = Field(default=None, ge=0)
    observaciones: str | None = None
    insumos: list[InsumoDeUnTrabajoEntrada] | None = None
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class ReprogramarEntrada(EntradaBase):
    """Mover un plan de día, con su motivo. **Lo que ya se hizo no se mueve.**"""

    fecha_prevista: dt.date
    motivo: str | None = Field(default=None, max_length=500)
```

### 3.3 `backend/app/textos.py` — los códigos y el bloque de la pantalla

**Los 28 códigos** que `app/trabajos.py` puede devolver, con su frase. El módulo **no escribe frases**: devuelve
el código y el router pide `textos.mensaje(codigo)`. Hay una prueba que exige que esta lista y la del módulo
sean exactamente la misma (`test_las_frases_de_los_codigos_del_informe_son_las_del_modulo`).

```python
MENSAJES.update({
    "TJ1_el_previsto_no_gasta": (
        "Este trabajo está previsto y todavía no se ha hecho: no ha gastado nada del almacén."
    ),
    "TJ2_no_consta_si_se_hizo": (
        "De este trabajo no consta si se llegó a hacer, así que no cuenta como trabajo hecho. "
        "Dilo y queda apuntado."
    ),
    "TJ3_el_apunte_esta_anulado": (
        "Este apunte está anulado: lo que había salido del almacén vuelve a contar."
    ),
    "TJ4_lo_que_salio_cambio": (
        "Se corrigió el trabajo: la salida de antes ya no cuenta y se ha apuntado la nueva."
    ),
    "TJ5_falta_el_motivo_para_anular": (
        "Para anular un trabajo hace falta decir por qué. Escríbelo y vuelve a pulsar."
    ),
    "TJ6_el_trabajo_ya_estaba_anulado": (
        "Este trabajo ya estaba anulado, así que no ha cambiado nada."
    ),
    "TJ7_de_la_lluvia_no_sale_la_nascencia": (
        "Que haya llovido no quiere decir que la planta haya nacido: eso se mira en el campo y se "
        "apunta como una observación."
    ),
    "TJ8_un_rodillo_no_cambia_lo_sembrado": (
        "Pasar el rodillo no cambia lo que tienes sembrado: la siembra sigue apuntada."
    ),
    "TJ9_no_se_reprograma_lo_ya_hecho": (
        "Este trabajo ya se hizo, así que su fecha es la del día en que se hizo. Si hiciste otro, "
        "apúntalo."
    ),
    "TJ10_lo_firmado_no_se_borra": (
        "Este apunte está firmado y no se puede borrar: se anula, con su motivo, y queda el rastro."
    ),
    "TJ11_el_trabajo_ya_estaba": (
        "Este trabajo ya estaba apuntado: no se ha vuelto a descontar del almacén."
    ),
    "TJ12_no_se_pudo_comprobar_si_ya_estaba": (
        "Esta petición no trae la clave para saber si ya se había apuntado, así que no he podido "
        "comprobarlo."
    ),
    "TJ13_faltan_las_hectareas": (
        "Hay trabajos de este año que no dicen cuántas hectáreas se trabajaron, así que las que se "
        "ven son solo las que constan."
    ),
    "TJ14_faltan_las_horas": (
        "Hay trabajos de este año que no dicen cuántas horas se estuvo, así que las que se ven son "
        "solo las que constan."
    ),
    "TJ15_la_tierra_quedo_o_no": (
        "Se cogió la cosecha, pero no consta si la tierra quedó con algo o vacía: eso se mira en el "
        "campo y se apunta como una observación."
    ),
    "TJ16_sin_maquina": "Hay trabajos apuntados sin decir con qué máquina se hicieron.",
    "TJ17_un_plan_no_es_un_trabajo": (
        "Esto está planificado y todavía no es un trabajo hecho: cuando lo hagas, apunta lo que de "
        "verdad pasó, con su día y lo que gastaste."
    ),
    "TJ18_sin_tierra": (
        "Hay trabajos que no dicen de qué tierra eran, así que no salen en el historial de ninguna."
    ),
    "TJ19_la_revision_de_lo_firmado": (
        "Lo firmado no se cambia: queda la revisión nueva, y la firma de antes sigue valiendo para lo "
        "que se firmó."
    ),
    "TJ20_no_se_pueden_sumar_unidades": (
        "Hay cantidades en unidades distintas, así que no se pueden juntar en una sola cifra."
    ),
    "TJ21_falta_la_cantidad": (
        "Hay un consumo apuntado sin cantidad, así que no se puede saber lo que queda."
    ),
    "TJ22_falta_la_unidad": (
        "Hay un consumo apuntado sin decir en qué se mide, así que no se puede hacer la cuenta."
    ),
    "TJ23_faltan_las_hectareas_de_la_tierra": (
        "Esta tierra no dice cuántas hectáreas tiene, así que no se puede comparar con lo trabajado."
    ),
    "TJ24_no_hay_fecha_de_hoy": (
        "No sé qué día es hoy, así que no te puedo decir cuánto falta ni cuánto se ha pasado."
    ),
    "TJ25_la_fecha_prevista_no_se_sabe": (
        "Este trabajo está planificado sin día, así que no se puede decir cuándo toca."
    ),
    "TJ26_el_apunte_del_consumo_no_esta": (
        "Hay una salida del almacén que dice venir de un trabajo que no encuentro, así que no la he "
        "podido comprobar."
    ),
    "TJ27_no_se_sabe_si_nacio": (
        "No consta si la planta ha nacido: eso se mira en el campo y se apunta como una observación."
    ),
    "TJ28_no_se_sabe_que_se_sembro": (
        "La siembra está apuntada, pero no dice qué se sembró. Apúntalo y el estado de la tierra "
        "quedará completo."
    ),
})
```

**Y el bloque de la pantalla** (`AGENDA`), con las 82 frases que lee `trabajos.js`. Va en `textos.py` y se
sirve en `/api/interfaz` como `"agenda"` (ver §3.5). Las claves son las mismas que las de la copia del test
del móvil: hay una prueba que compara las dos listas, para que ninguna frase salga en blanco.

```python
AGENDA: dict[str, str] = {
    "titulo": "Los trabajos",
    "explica": "Aquí tienes lo que tienes pensado hacer y lo que ya has hecho, en dos listas separadas. Lo que está pensado no ha gastado nada del almacén: lo que se gasta se apunta cuando el trabajo se hace.",
    "buscando": "Buscando…",
    "ver_el_cuaderno": "VER MI CUADERNO",
    "volver_a_los_trabajos": "VOLVER A LOS TRABAJOS",
    "previstos_titulo": "Lo que tengo pensado hacer",
    "lo_que_ha_sido": "Lo que ha sido esta tierra",
    "decir_el_cultivo": "Qué hay sembrado",
    "superficie": "Superficie",
    "hectareas_corto": "ha",
    "referencia": "Referencia oficial SIGPAC",
    "costes_sin_importe_uno": "Hay 1 gasto de esta tierra que no dice lo que costó.",
    "mis_tierras": "Mis parcelas, productos y máquinas",
    "previstos_explica": "Lo que está pensado no es un trabajo hecho y no ha gastado nada.",
    "previstos_vacio": "No tienes nada planificado. Cuando sepas lo que vas a hacer, apúntalo aquí.",
    "planificar": "PLANIFICAR UN TRABAJO",
    "planificar_titulo": "Planificar un trabajo",
    "planificar_explica": "Apunta lo que piensas hacer. No gasta nada del almacén: eso se apunta el día que lo hagas, con lo que de verdad gastes.",
    "guardar_previsto": "GUARDAR LO QUE PIENSO HACER",
    "ya_lo_he_hecho": "YA LO HE HECHO",
    # (ronda 9) Un plan ya cumplido sigue en la lista de lo pensado —el plan es lo que se pensó— pero no
    # puede ofrecer el botón de apuntarlo otra vez: el servidor contesta 409. Se dice cuándo se hizo.
    "ya_esta_hecho": "Ya lo apuntaste como hecho:",
    "cambiarlo_de_dia": "CAMBIARLO DE DÍA",
    "cancelarlo": "CANCELARLO",
    "reprogramar_titulo": "Cambiar de día este trabajo",
    "reprogramar_explica": "Elige el día nuevo. El día que tenía queda apuntado, para que se pueda explicar el cambio.",
    "cambiar_el_dia": "CAMBIARLO DE DÍA",
    "hechos_titulo": "Lo que he hecho",
    "hechos_explica": "Cada trabajo con su día, su tierra, su máquina y lo que se gastó. Lo anulado sale también, con su motivo.",
    "hechos_vacio": "Todavía no has apuntado ningún trabajo hecho.",
    "hecho_titulo": "Lo que he hecho de verdad",
    "hecho_explica": "Apunta lo que de verdad has hecho: el día, las hectáreas y las horas de verdad, y lo que gastaste. No tiene que ser igual que lo que habías pensado.",
    "lo_que_estaba_previsto": "Lo que tenías pensado",
    "lo_previsto_no_gasta": "Lo pensado no ha gastado nada del almacén.",
    "guardar_trabajo": "APUNTAR LO QUE HE HECHO",
    "corregir_titulo": "Corregir este trabajo",
    "corregirlo": "CORREGIRLO",
    "guardar_correccion": "GUARDAR LA CORRECCIÓN",
    "anular_titulo": "Anular este trabajo",
    "anularlo": "ANULARLO",
    "anular_explica": "Un trabajo no se borra: se anula y queda dicho por qué. Lo que había salido del almacén vuelve a contar.",
    "anular_confirmar": "ANULARLO",
    "motivo_anulacion": "Por qué lo anulas",
    "motivo_anulacion_pista": "Escríbelo pensando en que lo vas a leer dentro de dos años.",
    "guardando": "Guardando…",
    "tipo": "Qué trabajo",
    "tipo_pista": "Rodillo, cultivador, siembra, riego…",
    "elige_el_trabajo": "Elige el trabajo",
    "subtipo": "Con qué apero",
    "subtipo_pista": "Solo para las labores de suelo: rodillo, cultivador, arado…",
    "sin_decir": "Sin decir",
    "tierra": "En qué tierra",
    "elige_la_tierra": "Elige la tierra",
    "dia": "Qué día lo hiciste",
    "dia_pista": "El día de verdad, que es el que va al cuaderno.",
    "dia_previsto": "Para qué día lo tienes pensado",
    "dia_previsto_pista": "Si todavía no lo sabes, déjalo en blanco: se queda sin día.",
    "hectareas": "Cuántas hectáreas has trabajado",
    "hectareas_previstas": "Cuántas hectáreas piensas trabajar",
    "hectareas_pista": "Si no lo sabes, déjalo en blanco. No se pone un cero.",
    "horas": "Cuántas horas has estado",
    "horas_previstas": "Cuántas horas piensas estar",
    "horas_pista": "Si no lo sabes, déjalo en blanco.",
    "maquina": "Con qué máquina",
    "maquina_pista": "La máquina con la que lo hiciste. Si fue a mano, déjalo sin decir.",
    "sin_maquina": "Sin máquina dicha",
    "insumo": "Qué gastaste del almacén",
    "insumo_pista": "De qué envase sale lo que gastaste. Si no gastaste nada, déjalo sin decir.",
    "insumo_previsto_pista": "Lo que crees que vas a gastar. No se descuenta hasta que lo hagas.",
    "sin_insumo": "No gasté nada",
    "cantidad": "Cuánto",
    "cantidad_pista": "El total gastado, no lo de cada hectárea.",
    "unidad": "En qué se mide",
    "observaciones": "Lo que quieras apuntar",
    "repaso": "Antes de guardar, mira esto",
    "historia_titulo": "Lo que ha pasado en esta tierra",
    "que_hay_hoy": "Qué hay hoy",
    "lo_que_esta_sembrado": "Lo que hay sembrado",
    "variedad": "Variedad",
    "desde_cuando": "Desde",
    "sin_cultivo_declarado": "De esta tierra no consta que haya nada sembrado.",
    "ultima_labor": "La última labor",
    "historial_titulo": "Todo lo que ha pasado",
    "historial_explica": "Sale todo, también lo anulado, con el motivo por el que se anuló. Nada se borra.",
    "historial_vacio": "En esta tierra no hay ningún trabajo apuntado.",
    "revisado": "Corregido después",
    "firmado": "Está firmado: no se puede borrar, solo anular",
    "observaciones_de_campo": "Lo que he visto en el campo",
    "no_consta": "Lo que no consta",
    "sin_tierras": "Para planificar un trabajo hace falta tener una tierra dada de alta.",
    "anadir_tierra": "VER MIS TIERRAS",
    # ── Lo que ha costado una tierra (se añadieron al integrar, 05/10/2026) ──
    #
    # **Estas diez claves no venían en el bloque del ticket y se añadieron al integrarlo**, porque el
    # recorrido que el encargo pide al abrir una tierra es «qué cultivo tiene, qué trabajos se han hecho,
    # qué queda previsto **y qué costes conocidos tiene**»: los trabajos ya salían en el historial y el
    # dinero no. Las cifras las calcula el servidor (`GET /api/gastos/de-una-tierra/<id>`, del T13).
    "costes_titulo": "Lo que ha costado esta tierra",
    "costes_explica": (
        "Lo que consta de esta tierra. Está separado en dos: lo que pone el papel y lo que se repartió "
        "desde las cuentas, que es una estimación. Lo que no se sabe se dice, no se cuenta como cero."
    ),
    "costes_directos": "Lo que pone el papel",
    "costes_repartidos": "Lo repartido desde las cuentas",
    "costes_total": "Lo que se sabe que ha costado",
    "costes_sin_importe": (
        "Hay {cuantos} gasto de esta tierra que no dice lo que costó, así que el total se queda corto."
    ),
    "costes_vacio": "De esta tierra no hay ningún gasto apuntado.",
    "costes_directo_es": "Es un gasto que dice esta tierra.",
    "costes_repartido_es": "Es un trozo que se repartió a esta tierra desde las cuentas.",
    "ver_el_gasto": "VER EL GASTO",
    "cultivos": "Cultivos",
    "sin_cultivos": "No hay ninguna siembra ni plantación apuntada en esta tierra.",
}
```

Dos notas de la casa sobre este bloque, y las dos importan:

1. **No lleva huecos `{}`** (los números van aparte, en su campo: `{codigo, cuantos}`), así que
   `test_cada_mensaje_se_puede_rellenar` no tiene nada que exigirle.
2. **`AGENDA` tiene que entrar en `textos_visibles()`** para que el test de jerga lo mire: es lo mismo que
   le pasó a `TABLA` en el T14, y sin eso las frases salen en la pantalla sin que ningún test las lea.

### 3.4 `backend/app/servicios.py` — **tres líneas** que hacen que anular devuelva lo que salió

Es el único cambio que toca lógica que ya funciona, y es pequeño a propósito. Sin él, un trabajo no puede
gastar del almacén (la puerta de las salidas no acepta `apunte_tipo="labor"`) y anularlo no devolvería
nada (el movimiento seguiría contando):

```python
# en APUNTES_QUE_GASTAN
APUNTES_QUE_GASTAN = ("tratamiento", "fertilizacion", "siembra", "labor")

# en el diccionario `consultas` de estado_de_los_origenes
        # Las labores (T15, 05/10/2026). Es lo que hace que **anular un trabajo devuelva al almacén lo
        # que gastó sin tocar el libro**, igual que un tratamiento o una siembra anulados (A01/A04): el
        # movimiento se queda con su fecha y su autor, y deja de contar.
        "labor": (models.Labor, "anulado"),

# y en su diccionario `codigos`
        "labor": "AL35_el_apunte_esta_anulado",
```

Y un cuarto sitio, `lo_que_gasta_un_apunte`: hoy devuelve `{"existe": False}` para cualquier tipo que no
sea tratamiento, fertilización o siembra. Para un trabajo, la cantidad la dice **el propio trabajo** (el
router la manda al apunte de salida), así que basta con que la puerta sepa que el apunte existe:

```python
    if apunte_tipo == "labor":
        # Un trabajo hecho (T15). La cantidad de lo que gasta la dice su propio apunte de salida —el
        # router la manda—, y aquí se contesta lo que se sabe del trabajo: que existe, si está anulado y
        # de qué día es. **Lo que la labor no sabe es el total de cada insumo** (un insumo sin cantidad
        # no se resta), así que `cantidad` va en `None` y la puerta de las salidas pedirá el total en vez
        # de inventárselo.
        apunte = db.get(models.Labor, apunte_id)
        if apunte is None or apunte.explotacion_id != explotacion_id:
            return {"existe": False}
        return {
            "existe": True,
            "anulado": apunte.anulado,
            "cantidad": None,
            "unidad": None,
            "fecha": apunte.fecha,
            "superficie_ha": apunte.superficie_ha,
            "dosis_por_ha": None,
            "como_se_sabe": "lo_dice_el_apunte_de_salida",
        }
```

> **Y `ORIGENES_DE_UN_MOVIMIENTO` no se toca**: `labor` no entra ahí, igual que no entra `siembra`. Esa
> tupla es lo que acepta la puerta de los movimientos **a mano**, y una persona no puede decir «esto viene
> de un trabajo»: eso lo pone el programa cuando el trabajo descuenta.

### 3.5 `backend/app/main.py` y `backend/app/routers/interfaz.py`

```python
# main.py, con los demás routers
from .routers import trabajos_api
...
app.include_router(trabajos_api.router)

# interfaz.py, dentro de lo que devuelve `/api/interfaz`
        # Los trabajos por tierra (T15, 05/10/2026): la agenda, la ficha de un trabajo y la historia de
        # una tierra. Sin esto, las tres pantallas salen con los botones en blanco.
        "agenda": textos.AGENDA,
```

### 3.6 `backend/web/app.js` — el menú, la lista de pantallas y **las 12 acciones**

Lo que hay que añadir, en orden:

1. **En `PANTALLAS_EN_REACT`**, una sola clave: **`"trabajos"`**. La clave de esa lista es **el nombre del
   fichero** (`web/react/pantallas/trabajos.js`), no el de cada componente: mis tres pantallas viven en un
   fichero, y una clave de más sin su fichero pone roja `test_el_codigo_y_los_ficheros_cuadran`.
2. **El renglón del menú**: el contrato pide «Trabajos» en el menú de despacho (el tercero, después de
   «Tierras y mapa»). Con su acción `trabajos-ver` y su bloque de textos.
3. **En `MODULO_DE_LA_PANTALLA`**: `trabajos: "trabajos"` (y, para los pasos del formulario y la historia
   de la tierra, lo que el coordinador decida: la historia cuelga de «tierras», y el formulario de
   «trabajos»).
4. **Las tres pantallas montadas con `montarEn`** (nunca con `pintar`): la agenda con
   `pantallaDeLosTrabajos`, la ficha con `pantallaDeUnTrabajo` y la historia con `pantallaDeLaTierra`.
   `app.js` prepara sus propiedades (las listas con sus frases ya montadas desde `textos.agenda`, los
   `tipos` desde `textos.trabajos` + `textos.trabajos_de_labor`, los `subtipos` desde los seis aperos, las
   tierras, las máquinas y los envases del almacén).
5. **El manejador de clics**: las doce acciones de abajo. **Once de ellas no existen todavía** (la
   duodécima, `trabajos-ver`, se atiende aquí y solo abre la agenda).

| Acción | Qué tiene que hacer |
|---|---|
| `trabajos-ver` | Abrir la agenda (`GET /api/trabajos`) y montarla |
| `trabajo-planificar` | Abrir la ficha en modo `planificar` (sin identificador) |
| `trabajo-previsto-guardar` | `POST /api/trabajos/previstos` con lo escrito (**no descuenta nada**), y decir que está pensado |
| `trabajo-abrir` | Abrir la ficha de ese plan en modo `reprogramar`, con lo que hay |
| `trabajo-reprogramar` | `POST /api/trabajos/previstos/<id>/reprogramar` con el día nuevo |
| `trabajo-cancelar` | `POST /api/trabajos/previstos/<id>/cancelar` con el motivo |
| `trabajo-hecho` | Abrir la ficha en modo `hecho` con el plan delante (lo que se había pensado, al lado) |
| `trabajo-hecho-guardar` | `POST /api/trabajos/previstos/<id>/hecho`: **aquí es donde nace el trabajo y se descuenta del almacén** |
| `trabajo-corregir` | Abrir la ficha en modo `corregir` con lo que hay apuntado |
| `trabajo-guardar` | `PUT /api/trabajos/<id>` con lo corregido |
| `trabajo-anular` | Abrir la ficha en modo `anular` (solo el motivo) |
| `trabajo-anular-confirmar` | `POST /api/trabajos/<id>/anular` con el motivo |

Y una cosa que **no** hay que hacer: **no borrar ninguna fila**. Lo que se apunta de un trabajo hecho se
corrige o se anula; la pantalla no ofrece borrar porque la puerta no lo hace (salvo el borrado con rastro
que ya existe para el resto del cuaderno, y que en un apunte firmado contesta que no).

### 3.7 `backend/web/react/rutas.js` y `backend/web/service-worker.js`

```js
// rutas.js — en la tabla de pantallas y en el mapa de identificadores
  // T15 (05/10/2026): la agenda de los trabajos y la historia de una tierra. Las dos piden sus datos al
  // servidor al abrir su dirección, así que se pueden enlazar y recargar. La ficha de un trabajo **no
  // tiene dirección**: es un formulario, y uno que al recargar saldría vacío es peor que no tenerla.
  "trabajos",
  "trabajo_tierra",   // #/tierras/<id>/historial
// y en `identificadores`: trabajo_tierra: { id: 12 }

// service-worker.js — en FICHEROS, y la caché a la versión siguiente
  "/react/pantallas/trabajos.js",
```

### 3.8 `docs/REACT.md`

La fila de la tabla de pantallas con `pantallas/trabajos.js` | ✅ En React, y el párrafo de la pantalla con
lo que **no** hace (separar lo previsto de lo hecho; una lluvia no acredita nascencia; los huecos se
enseñan como huecos). Y el recuento de la guía («veintiocho») sube con las pantallas que entren.

### 3.9 Los recuentos de la documentación

`README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md` dicen **3.960** pruebas de Python y **901** de
JavaScript. Medido hoy en el árbol: **4.249 de Python y 951 de JavaScript**, y **eso no es solo mío**: en el
mismo árbol están los ficheros de los otros tickets que van en paralelo (`test_gastos.py` 93 y
`test_extractos.py` 87 de Python, y `tests_js/gastos.test.js`). Lo mío son **70 de Python y 24 de
JavaScript**, contados con la misma expresión que usa el guardián:

```powershell
..\.venv\Scripts\python.exe -m pytest --collect-only -q   # y se suman los recuentos por fichero
node --test "tests_js/*.test.js"                          # 24 son de tests_js/trabajos.test.js
```

---

## 4. Lo que NO he podido comprobar (dicho por mí, antes de que se pregunte)

> **Puesto al día el 07/10/2026.** Este apartado es el registro honesto de lo que su autor no pudo
> comprobar cuando escribió el ticket. **Los tres puntos ya no están así**: el router se ejecuta (77
> pruebas de `test_trabajos.py` pasan y 0 saltan), las pantallas están montadas en `app.js` con dirección y
> menú, y el recorrido se ha andado **en un navegador de verdad** con la explotación de 64 tierras
> (`scripts/comprobar_el_recorrido.py`, 14 comprobaciones, 0 fallos). Se deja el texto original debajo, con
> su fecha, porque cuenta por qué se escribió así; lo que no vale es leerlo hoy como el estado del ticket.

1. **El router no se puede ejecutar.** Está escrito entero y **no se puede ni importar** hasta que el
   coordinador integre las tablas, los esquemas, los textos y las tres líneas de `servicios.py` (§3).
   La prueba del recorrido se salta con la lista exacta de lo que falta, y **se ejecutará sola** en cuanto
   esté: `test_las_puertas_del_router_se_ejecutan_cuando_este_integrado`. **No he ejecutado ni una sola
   llamada HTTP de este ticket**: lo que está probado es la lógica pura y la pantalla (con React
   renderizado a HTML), no el recorrido contra un servidor.
2. **Las tres pantallas no se han visto en un navegador.** No hay dirección ni menú hasta que `app.js` las
   monte, y `app.js` no es mío. Lo que sí está comprobado es que **dibujan** (24 pruebas de React con
   `renderToStaticMarkup`, el mismo camino que usan las demás pantallas migradas) y que **no tocan el
   navegador**. La medición a 390/1024/1440 px y la captura quedan para la integración.
3. **La pantalla no se ha probado con un agricultor delante.** Que «Lo que tengo pensado hacer» y «Lo que he
   hecho» se entiendan como dos cosas distintas, y que «no dice las horas» se lea como un hueco y no como
   un cero, no lo dice ninguna prueba: hace falta la prueba con personas.
4. **No he tocado la base de datos del agricultor** (ni leída) ni he arrancado ningún servidor en el 8000.
   Las pruebas que he corrido usan la base temporal de `conftest.py`.
5. **No he corrido la suite entera** (el encargo lo prohíbe: son ~6 minutos). He corrido mi fichero y los
   **cinco guardianes** que podían verse afectados por ficheros nuevos (§2.2). Puede quedar algún guardián
   que lea los ficheros nuevos y que no haya mirado: los he buscado por los que recorren el árbol
   (`rglob`) y son los cinco de la tabla.
6. **El subtipo de una labor de suelo vive hoy en `detalles`.** El router lo lee de ahí mientras no exista
   la columna (§3.1). Es una concesión al estado actual, no una decisión: el sitio del subtipo es su
   columna, y está propuesta.
7. **Lo que el programa no sabe sigue sin saberse**: la lluvia de cada tierra (T17, bloqueado porque no hay
   fuente elegida) y la nascencia medida (T18). Está declarado en `trabajos.QUE_FALTA` y sale en
   `/api/trabajos/que-falta`, para que nadie lo rellene con lo que le parezca.
8. **Ojo con la copia del commit `698e783`.** Mientras trabajaba, el repositorio recibió un commit con una
   **versión intermedia** de `app/trabajos.py` (aparece como modificado en `git status`, no como nuevo). Lo
   que vale es **lo que está en el árbol de trabajo ahora**: ese fichero, más los cinco que aún no están
   commiteados (`app/routers/trabajos_api.py`, `tests/test_trabajos.py`, `web/react/pantallas/trabajos.js`,
   `tests_js/trabajos.test.js` y este informe).

---

## 5. Ficheros

### Nuevos (los seis del ticket, y ninguno más)

| Fichero | Qué es |
|---|---|
| `backend/app/trabajos.py` | **La lógica pura**: previsto frente a hecho, el historial, el estado derivado, las reglas de corregir y anular, los consumos y los reenvíos. Sin base de datos, sin FastAPI, sin navegador |
| `backend/app/routers/trabajos_api.py` | El router `/api/trabajos`, con sus once puertas y **la lista de lo que le falta para poder ejecutarse**, escrita en el propio fichero |
| `backend/tests/test_trabajos.py` | 70 pruebas (68 en verde y 2 saltadas hasta que se integre): las reglas del encargo, los guardianes de los códigos, de la copia de los textos y del propio informe, y la del recorrido |
| `backend/web/react/pantallas/trabajos.js` | Las tres pantallas (la agenda, la ficha y la historia de una tierra) |
| `backend/tests_js/trabajos.test.js` | 24 pruebas de las tres pantallas, con la copia literal de los textos |
| `docs/T15_TRABAJOS.md` | Este informe |

### No tocados

**Ninguno de los compartidos**: no he escrito en `models.py`, `schemas.py`, `main.py`, `textos.py`,
`servicios.py`, `web/app.js`, `web/react/rutas.js`, `web/service-worker.js` ni en otros ficheros de
pruebas, ni he tocado `backend/cuedigital.db`. Los cambios que hacen falta están en §3, con sus bloques
literales, para que el coordinador los pegue.

---

## 6. Resumen en una pantalla

- **Hecho y verde hoy:** las cuatro reglas del encargo (previsto no gasta, el rodillo no borra la siembra,
  la lluvia no acredita nascencia, anular y corregir no duplican consumos), el historial de una tierra y
  su estado derivado, la corrección y la anulación sin borrar nada, el reenvío del móvil sin duplicar, los
  huecos dichos como huecos y las tres pantallas de React. **68 + 24 pruebas en verde**, y seis mutaciones
  hechas a propósito para comprobar que muerden.
- **Escrito y todavía sin ejecutar:** el router `/api/trabajos`, que necesita dos tablas, cuatro columnas,
  seis esquemas, 82 frases de pantalla, 28 mensajes y tres líneas de `servicios.py` (todo literal en §3).
- **¿Se puede completar hoy el recorrido entero** (planificar → marcar lo hecho → tierras, máquinas, horas
  e insumos → historial y existencias → cuaderno)? **La lógica sí y la pantalla sí; el recorrido contra el
  servidor, no todavía.** Falta la integración del coordinador (§3), que es la que abre las puertas: sin
  ella no hay `/api/trabajos`, ni menú, ni dirección, ni pantalla en el navegador. Y una cosa del recorrido
  que **no** estará al integrarlo: **que lo que se apunta aquí salga en el cuaderno firmado** — eso es
  trabajo del T19 (el cuaderno tiene su propio mapeo, `routers/cuaderno.py`, y hoy lee `labor.tipo`,
  `parcela`, `superficie`, `cultivo` y `equipo_id`, que son los campos que este ticket no cambia).
