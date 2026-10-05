# T02 / E0 — Auditoría de valores por defecto peligrosos

> **Lo que hace este documento.** Busca, uno por uno, los sitios del programa donde **un dato
> que no se sabe acaba pareciendo un dato que sí se sabe**: autorizado, ecológico, cero
> nutrientes, cero hectáreas, pagado, vigente, sin pendientes, cero existencias.
>
> **Lo que NO hace.** No modifica **ningún** dato. No toca `backend/cuedigital.db` (no se ha
> abierto para leer ni para escribir). No ejecuta servidores, ni `scripts/humo.py`, ni la
> comprobación de navegador.
>
> **Cómo se ha hecho.** Lectura del código y búsquedas automáticas sobre
> `models.py`, `schemas.py`, `routers/*.py`, `servicios.py`, `legal.py`, `validaciones.py`,
> `catalogos.py`, `database.py`, `firma.py`, `cuaderno.py`, `cuaderno_cyl*.py`, `facturas.py`,
> `maestros.py` y `backend/web/**/*.js`: los `default=` de modelos y esquemas, los
> `server_default=`, los `or 0` / `or 0.0` / `or ""` / `or False` / `bool(...)` / `int(...)` /
> `coalesce`, y las sumas sobre listas donde un hueco puede ser `None`.
>
> **Fecha:** lectura del código en su estado actual del repositorio.

> **Estado de los hallazgos (actualizado el 03/10/2026).** Este documento es la **fotografía** de lo que
> estaba mal cuando se hizo la auditoría: sus apartados se leen como el «antes», no como el estado de hoy.
> Lo que ha cambiado desde entonces, con su evidencia medida, está en
> `docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`, apartados 6.1 a 6.4 y 10.2:
>
> * **A1 (producto autorizado sin que nadie lo diga): cerrado.** Tres estados, con `None` = «no comprobado»,
>   que avisa y no bloquea. Los productos **ya guardados** no se reescriben (no hay forma de saber si el «sí»
>   lo escribió el agricultor) y se arreglan desde la pantalla.
> * **A2 (zona de nitratos): cerrado.** Se guarda `None`, en el texto firmado se escribe «no se sabe», y al
>   apuntar un abono sale el aviso `N4_no_se_si_es_zona_de_nitratos`. Los `True`/`False` se escriben igual que
>   siempre, así que **las firmas ya hechas siguen cuadrando** y no se ha subido `VERSION_CANONICA`.
> * **A3 (cuaderno vacío): cerrado** en la ronda anterior.
> * **A4, A5, A6 y A7: cerrados** (ronda 3, 03/10/2026). El tope de los 170 kg ya ve los abonos por grupo (por
>   hectárea, sin inventar repartos, y declarando lo que no se puede atribuir); el plazo de seguridad
>   desconocido es un tercer estado **con aviso** y nunca un permiso para cosechar; la composición que no consta
>   se calcula, se guarda, se exporta y se firma como **«no se sabe»** (con `VERSION_CANONICA` en 1, así que las
>   firmas hechas siguen cuadrando); y la superficie que no se sabe deja de ser 0 ha y **la tierra se puede
>   tratar**, con la del SIGPAC **propuesta** y no escrita.
> * La migración de esquema que hacía falta (SQLite no sabe quitar el `NOT NULL` de una columna ya creada) se
>   hace **al arrancar**, con copia coherente, en una transacción y sin cambiar ningún dato; son **13 columnas**
>   en tres tablas, y se ha **ensayado sobre copias de la copia de seguridad**, con vuelta atrás byte a byte.
>
> **Y los de gravedad media, que es lo que faltaba (medido el 03/10/2026, en el código):**
>
> * **A9 (ceros en el PDF y el CSV del cuaderno): cerrado.** `routers/cuaderno.py` ya no escribe
>   `0,0000 L/ha` ni un hueco con unidad cuando la dosis no se sabe: sale **vacío**. Tiene su prueba
>   (`tests/test_lo_que_no_se_sabe_no_es_cero_en_el_cuaderno.py`), y está **probada contra el defecto**
>   (volviendo a poner el `or 0`, 2 de sus 3 pruebas se ponen en rojo). Ver el apartado 37 del seguimiento.
> * **A10, A11, A12, A13 y A14: abiertos**, con los sitios exactos medidos uno a uno y el arreglo ya
>   decidido en los apartados **40 y 41** de `docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`. El §40 dice línea por
>   línea dónde está cada uno —y **corrige este documento en dos cosas**: A10 son **cinco** entradas y no
>   cuatro (falta `GrupoEntrada`, `schemas.py:376`), y A14 no son tres líneas de `app.js` sino seis, porque
>   el servidor **ya manda** `tierras_sin_superficie` y la pantalla vieja lo tira—; el §41 dice de dónde se
>   copia el arreglo: del vocabulario de tres estados que el ticket T14 dejó ya escrito y probado en
>   `app/maquinaria.py`.

## Cómo se juzga la gravedad

| Gravedad | Qué significa |
|---|---|
| **alta** | El dato falso **sale del programa** (entra en el texto que se firma, en el fichero de la Junta, en el volcado oficial) **o** hace pasar por bueno algo que la ley condiciona (autorización de un producto, zona de nitratos, plazo de seguridad, tope de nitrógeno, «no te falta nada»). |
| **media** | El dato falso se ve en pantalla y puede llevar a una decisión equivocada, pero no sale del programa ni sustituye una comprobación legal. |
| **baja** | Presentación, coherencia o código que hoy no puede llegar a ejecutarse. |

**Una distinción que se usa en todo el informe, y que es la regla de la casa**
(`AGENTS.md` §3.3, `models.py:199`, `legal.py:205-207`): **`None` («no lo sé») no es `False`
(«no») ni `0` («es cero»)**. Un defecto peligroso es exactamente el que convierte el primero en
el segundo.

---

# a) Lo que YA es un fallo

## A1. Un producto queda «autorizado» y «permitido en ecológico» sin que nadie lo diga — **alta**

**Dónde**

- `models.py:373` → `autorizado: Mapped[bool] = mapped_column(Boolean, default=True)`
- `models.py:374` → `permitido_ecologico: Mapped[bool] = mapped_column(Boolean, default=True)`
- `schemas.py:314` → `autorizado: bool = True`
- `schemas.py:315` → `permitido_ecologico: bool = True`
- Consecuencia en las comprobaciones: `validaciones.py:178-179`
  (`if not producto.autorizado:` → bloquea) y `validaciones.py:218-220`
  (`if not producto.permitido_ecologico:` → bloquea, **solo si la finca es ecológica**).
- En la pantalla, el bloque entero de la autorización está marcado **`opcional: true`**
  (`app.js:6465-6476`), y un campo vacío **ni siquiera se manda** (`app.js:6708-6711`:
  `if (valor === undefined) continue; if (valor === "") continue;`).

**Qué dato se inventa.** Que el producto está autorizado y que se puede usar en producción
ecológica.

**En qué caso concreto un agricultor vería un dato falso.** Da de alta «Karate Zeon» escribiendo
solo el nombre, el número de registro y la dosis. El bloque de la autorización está plegado,
pone «opcional» y él lo deja. La ficha queda con `autorizado = True` y
`permitido_ecologico = True`. Si su finca es ecológica (`explotaciones.produccion_ecologica`),
el aviso `V15_no_ecologico` **no salta nunca**, y su cuaderno dice que él dio por permitido un
producto que quizá no lo está. Y si el producto estaba retirado del registro, tampoco salta
`V1_no_autorizado`: el programa lo da por bueno.

**Por qué es alta y no media.** No es un hueco en una pantalla: es la ausencia de un dato
convirtiéndose en un **permiso**. El comentario de `app.js:6466-6468` dice literalmente que sin
esos campos «el programa daba por bueno que todo producto está autorizado, que se puede usar en
ecológico y que no tiene autorización excepcional caducada, sin preguntarlo». Se añadieron los
campos, **pero el defecto permissivo se quedó**.

---

## A2. `en_zona_vulnerable`: «no lo sé» se guarda como «no», y entra en el documento que se firma — **alta**

**Dónde**

- `servicios.py:100-102`:
  ```python
  # None significa "no lo sabemos". Se guarda False y la aplicación sigue
  # avisando mientras no se cargue el listado oficial de zonas vulnerables.
  en_zona_vulnerable=bool(parcela.zona_vulnerable_nitratos) if parcela else False,
  ```
- `servicios.py:158` (el mismo patrón en el abono):
  `en_zona_vulnerable=bool(parcela.zona_vulnerable_nitratos) if parcela else False,`
- Los modelos: `models.py:598` y `models.py:899`, los dos `Boolean, default=False`.
- **Y entra en lo que se firma**: `firma.py:282` (`"En zona de nitratos":
  tratamiento.en_zona_vulnerable`) y `firma.py:310` (el mismo campo en el abono). El comentario de
  `firma.py:274-277` dice que esos campos forman parte del registro firmado y que cambiarlos
  después hace que la huella deje de cuadrar — o sea, que **una vez firmado, ese `False` ya no se
  puede corregir sin volver a firmar**.
- Las reglas que dependen de esto: `validaciones.py:391-401` (aviso de zona de nitratos) y
  `validaciones.py:455` (`_reglas_de_nitratos` sale sin hacer nada si la parcela no está en zona).

**Qué dato se inventa.** Que la aplicación se hizo **fuera** de zona vulnerable a nitratos.

**En qué caso concreto un agricultor vería un dato falso.** El listado oficial de zonas
vulnerables no está cargado, o la tierra está en un municipio del que no consta el código INE.
En ese caso `parcela.zona_vulnerable_nitratos` vale `None` a propósito (`models.py:207-208`, y
está bien puesto: es el único booleano de tres estados del modelo). El agricultor apunta un
abono con purín. En el texto canónico del cuaderno —el que se firma— aparece
**«En zona de nitratos: False»**, y ni el aviso de los 170 kg (`validaciones.py:391-401`) ni las
reglas de la Orden MAV/398/2022 (`validaciones.py:448-520`) se ejecutan.

**Por qué es alta.** El propio comentario reconoce que se guarda `False` sabiendo que no se sabe.
Y el destino de ese `False` no es una pantalla: es el documento firmado y, en su día, el volcado
a la Junta.

---

## A3. «Lo tienes todo apuntado y sin nada pendiente» sobre un cuaderno vacío — **alta**

**Dónde**

- `cuaderno.py:724-729`:
  ```python
  return {
      "campana": campana.anio,
      "esta_completo": not pendientes,
      "pendientes": pendientes,
      "mensaje": textos.mensaje("A8_todo_en_orden") if not pendientes else None,
  }
  ```
- El texto del servidor: `textos.py:615` →
  `"A8_todo_en_orden": "Lo tienes todo apuntado y sin nada pendiente. Así da gusto."`
  **(este mensaje hoy no lo enseña ninguna pantalla: `app.js` no lee `faltantes.mensaje`; se
  enseña en `GET /api/avisos`, que tampoco tiene pantalla — ver T01 §3.2).**
- Lo que comprueba son **cuatro** cosas: tierra sin cultivo declarado (`cuaderno.py:678-688`),
  tratamiento sin justificación (`691-699`), tratamiento sin dosis (`700-708`) y tratamiento sin
  aplicador o sin máquina (`714-722`). **Ninguna de las cuatro mira una tierra sin apuntar, un
  abono sin composición, un producto sin plazo de seguridad ni una máquina sin ITEAF.**
- **Y las frases que sí se ven las compone el cliente por su cuenta**, con el mismo resultado:
  - «No te falta nada por apuntar» — `textos.py:940` (`pendientes_ninguno`), montado en
    `app.js:1523-1526` y pintado en `react/pantallas/mi_cuaderno.js:403`.
  - «Lo tienes todo apuntado.» — `textos.py:931` (`falta_vacio`), montado en `app.js:1519` y
    pintado en `react/pantallas/mi_cuaderno.js:156`.
  - «No te falta nada: el cuaderno está al día.» — `textos.py:3831` (el otro `falta_vacio`, el
    del panel), montado en `app.js:1094` y pintado en `react/piezas/panel_de_mando.js:87`.
  Ninguna de las tres depende de que el servidor haya contestado: salen siempre que
  `pendientes` esté vacío. `estado.faltantes` es `null` también cuando la llamada ha fallado
  (`app.js:3644`, `.catch(() => null)`), aunque ahí sí hay una guarda para el resumen
  (`app.js:1520-1525`).
- El mismo patrón, sin pantalla hoy, en `maestros.py:1189-1192`
  (`{"tipo": "todo_bien", "mensaje": textos.mensaje("A8_todo_en_orden")}` cuando la lista de
  avisos queda vacía).

**Qué dato se inventa.** Que el cuaderno está completo.

**En qué caso concreto un agricultor vería un dato falso.** Acaba de darse de alta. Tiene cero
tierras y cero apuntes. Las cuatro comprobaciones no tienen nada que mirar y devuelven una lista
vacía (`esta_completo: true`), así que en su pantalla «mi cuaderno» lee **«No te falta nada por
apuntar»**, y en el panel de mando **«No te falta nada: el cuaderno está al día»**. Un cuaderno
que no tiene ni una tierra no está completo: está vacío.

**Por qué es alta.** Es el caso más puro de «el silencio se lee como un visto bueno», y es el
que el propio contrato prohíbe: «Evitar una pantalla bonita sobre cifras aún inexistentes»
(`CONTRATO_IMPLEMENTACION_CRM.md` §7, línea 384) y «Ninguno debe dar un verde ficticio» (§12,
línea 513). Aquí el programa no dice «no he podido comprobar»: dice «está todo bien».

---

## A4. El tope de 170 kg de nitrógeno no ve los abonos apuntados por grupo — **alta**

**Dónde**

- `servicios.py:469-470` y `servicios.py:495-496`, en las dos funciones que alimentan la
  comprobación:
  ```python
  if parcela_id is None:
      return 0.0
  ```
  (`nitrogeno_organico_en_la_parcela`, `servicios.py:453-484`;
  `nitrogeno_aplicado_en_la_parcela`, `servicios.py:487-507`)
- El llamante les pasa **`datos.parcela_id`**, que es `None` cuando el abono es de un grupo de
  tierras: `registros.py:369-374` y `registros.py:375-380`.
- Y el total se compone con el hueco como cero: `validaciones.py:466`
  (`total = (organico_n_ha or 0.0) + nuevo`), y el aviso que saldría dice «ya 0,0»
  (`validaciones.py:475`, `validaciones.py:509`).

**Qué dato se inventa.** Que en esa tierra no se ha echado **nada** de nitrógeno orgánico.

**En qué caso concreto un agricultor vería un dato falso.** El agricultor tiene siete tierras de
trigo agrupadas en la unidad de cultivo «Los trigos» (`grupos_parcelas`, `parcelas.py:1038`).
Abona el grupo entero con purín: el apunte se guarda con `grupo_id` y **sin** `parcela_id`
(es lo que manda la pantalla: `app.js:11285-11287`, al elegir grupo se olvida la parcela). Ese
nitrógeno **no cuenta para el tope**. Abona por grupo tres veces en el año y el programa le dice
que lleva 0 kg/ha de estiércol: la regla de los 170 kg nunca salta.

**Por qué es alta.** Es un límite legal de la Orden MAV/398/2022 (`catalogos.limite_de_estiercol_kg_n_ha`,
`catalogos.py:1069`) que el programa **cree** estar comprobando y no comprueba. Y el comentario
de `models.py` y `validaciones.py:150-154` deja claro que el caso del grupo ya dio un susto
parecido una vez (la superficie del grupo); este es el mismo agujero, en los nutrientes.

**Lo que sí está bien resuelto y conviene no romper**: la superficie del grupo **sí** se
comprueba (`validaciones.py:155-170` y `375-389`), y el nitrógeno del **plan** se compara por
parcela con `plan.parcela_id` (`servicios.py:244-251`).

---

## A5. Un plazo de seguridad que no se sabe se trata como «no hay plazo» — **alta**

**Dónde**

- `validaciones.py:762-770`:
  ```python
  for tratamiento in tratamientos:
      if getattr(tratamiento, "anulado", False):
          continue
      plazo = tratamiento.plazo_seguridad_dias
      if plazo is None and tratamiento.producto_id:
          producto = producto_por_id.get(tratamiento.producto_id)
          plazo = getattr(producto, "plazo_seguridad_dias", None)
      if plazo is None:
          continue
  ```
- Y el respaldo **no actúa** desde el endpoint que comprueba la cosecha:
  `registros.py:665-690` llama `validaciones.validar_cosecha(fecha_cosecha=datos.fecha,
  tratamientos=tratamientos)` **sin pasar `producto_por_id`**, así que el diccionario queda vacío
  (`validaciones.py:760`) y el respaldo por producto nunca encuentra nada.
- El apunte hereda el plazo del producto al guardarse, y si el producto no lo tiene queda `None`:
  `servicios.py:39-41` y `servicios.py:82`. El campo del producto es opcional y por defecto
  `None` (`models.py:366`, `schemas.py:307`).
- El aviso informativo tampoco sale: `validaciones.py:313-320` (`plazo_de_espera` devuelve `None`)
  y `validaciones.py:292-300` (el aviso `V8_dias_de_espera` solo se añade `if plazo is not None`).

**Qué dato se inventa.** Que se puede cosechar.

**En qué caso concreto un agricultor vería un dato falso.** Da de alta un insecticida sin rellenar
el plazo de seguridad (es opcional, no lo pide nadie). Trata el 10 de mayo. El 11 de mayo registra
la cosecha: `validar_cosecha` recorre los tratamientos, encuentra el de ayer, ve que su plazo es
`None` y **pasa al siguiente**. No hay aviso, no hay bloqueo, no hay «no lo he podido comprobar».
El agricultor cosecha con residuos por encima del límite y su cuaderno no dice ni una palabra.

**Por qué es alta.** El plazo de seguridad es la comprobación que el propio `validaciones.py:744-746`
llama «la regla que más disgustos evita». Un hueco aquí no es un dato que falte: es una cosecha
perdida.

---

## A6. Un abono sin composición declarada son «cero nutrientes», y eso entra en el documento firmado — **alta**

**Dónde**

- `models.py:389-391` → `riqueza_n`, `riqueza_p`, `riqueza_k`: `Float` **no nulo** con
  `default=0.0`.
- `schemas.py:353-355` → los mismos tres con `default=0.0`.
- `servicios.py:123-125` → si no hay ficha de abono, las tres riquezas son `0.0`; y
  `servicios.py:144-149` calcula con ellas las unidades fertilizantes, que también son no nulas
  con `default=0.0` (`models.py:880-885`).
- **Al documento firmado**: `firma.py:300-307`
  (`"Nitrógeno (%)": registro.riqueza_n`, `"Fósforo (%)"`, `"Potasio (%)"`,
  `"Nitrógeno aportado (kg/ha)": registro.uf_n_ha`, y los de P y K).
- Y a la suma que alimenta el plan: `servicios.py:483` y `servicios.py:506`
  (`total += registro.uf_n_ha or 0.0`).
- El comentario de `models.py:872-873` reconoce la intención («copia de la riqueza en el momento
  del registro») pero el defecto de partida es un cero, no un «no lo sé».

**Qué dato se inventa.** Que ese abono **no aporta** nitrógeno, fósforo ni potasio.

**En qué caso concreto un agricultor vería un dato falso.** Apunta «estiércol de la nave» sin
ficha de abono en el catálogo (el campo `fertilizante_id` es opcional, `schemas.py:592`), o el
abono se ha creado desde una factura sin composición (`facturas_api.py:475-479`). En el texto que
se firma del cuaderno aparece **«Nitrógeno (%) 0»** y **«Nitrógeno aportado (kg/ha) 0»**. En el
plan de abono, el nitrógeno aplicado de ese año sale 0. Y `organic_n_ha` y `total_n_ha` siguen
valiendo lo que valían, así que las reglas de nitratos comparan contra una cifra que no incluye
ese abono.

**Nota sobre la pantalla.** El formulario de abono **sí** marca las tres riquezas como
obligatorias (`app.js:6238-6240`), pero **la API no** (`schemas.py:353`), y el abono también se
crea desde la factura. Es decir: la puerta está cerrada en un sitio y abierta en dos.

---

## A7. Una superficie que no se sabe se convierte en 0 hectáreas, y la tierra deja de poder tratarse — **alta**

**Dónde**

- `cuaderno_cyl_api.py:288-289` — al **importar el cuaderno de la Junta**:
  ```python
  # La superficie que se cultiva y se trata. La del recinto entero va aparte.
  superficie_ha=linea.superficie_cultivada_ha or 0.0,
  ```
  (Justo debajo, `superficie_sigpac_ha=linea.superficie_sigpac_ha`, que **sí** se queda en `None`:
  el mismo objeto, dos criterios distintos.)
- `parcelas.py:194` — al **traer una tierra del SIGPAC**:
  `superficie_ha=recinto.superficie or 0.0`. Y el recinto puede no traerla:
  `sigpac.py:532` (`superficie: float | None = None`) y `sigpac.py:606`
  (`superficie=numero("superficie")`, que devuelve `None` si el servicio no la manda).
- El modelo: `models.py:193` (`Float, default=0.0`). La entrada a mano: `schemas.py:132`
  (`superficie_ha: float = Field(ge=0)` — obligatoria, pero **0 pasa el filtro**).
- **Y lo que rompe**: `validaciones.py:132-133` (`V22_sin_superficie`, bloquea un tratamiento sin
  superficie) y `validaciones.py:135-148` (`V4_superficie_excedida`: con
  `parcela.superficie_ha == 0`, cualquier superficie mayor que 0,0001 ha **bloquea**). Lo mismo en
  el abono: `validaciones.py:361-372` (`F2_superficie_excedida`).
- Los resúmenes heredan el cero: `cuaderno_cyl.py:374-380` (`hectareas_declaradas`,
  `sum(... or 0.0 ...)`), `fincas_api.py:58-62` (`coalesce(sum(...), 0.0)`).

**Qué dato se inventa.** Que la tierra **tiene cero hectáreas**.

**En qué caso concreto un agricultor vería un dato falso.** Trae su cuaderno de la Junta
(`app.js:5442`) o una tierra del SIGPAC y la columna «Superficie Cultivada» viene en blanco
—pasa de verdad: la plantilla de la Junta dejó la casilla vacía en varias tierras—. La tierra
queda dada de alta con **0,00 ha**. Al día siguiente intenta apuntar un tratamiento y el programa
le contesta que **se pasa de la superficie de la parcela**. La tierra existe, se ve en la lista,
y es inutilizable: no puede tratarla ni abonarla.

**Por qué es alta.** Es a la vez un dato falso visible («0,00 ha») y una **puerta que se cierra**:
el agricultor no puede meter el dato que falta desde ninguna pantalla, porque `superficie_ha` sí
se puede corregir, pero él no sabe que el problema es un cero que puso el programa.

---

## A8. El gasto de producto cuenta como cero lo que no se apuntó — **media-alta**

**Dónde**

- `servicios.py:43-45` — la cantidad total de un tratamiento solo se calcula si hay dosis **y**
  superficie:
  ```python
  cantidad_total = None
  if datos.dosis is not None and datos.superficie_tratada_ha:
      cantidad_total = legal.cantidad_total(datos.dosis, datos.superficie_tratada_ha)
  ```
- `servicios.py:640-645` — y la suma de lo gastado **omite los `None`**:
  ```python
  total = sum(
      tratamiento.cantidad_total
      for tratamiento in tratamientos
      if tratamiento.cantidad_total is not None
  )
  return round(total, 4), len(tratamientos)
  ```
  Fíjate en el detalle: devuelve el total de los que se pudieron sumar **y el número de todos**,
  así que la pantalla puede decir «2 apuntes» y haber sumado uno.
- Lo que se enseña: `GET /api/productos/cesta/situacion` (`maestros.py:280-331`) y la cesta del
  almacén (`app.js:3641`).

**Qué dato se inventa.** Que se ha echado menos producto del que se echó, y por tanto que
**queda más del que queda**.

**En qué caso concreto un agricultor vería un dato falso.** Dos tratamientos del mismo producto.
En uno el agricultor no apuntó la dosis (el campo no bloquea y lo puede rellenar mañana). La cesta
dice «quedan 5 L» cuando en realidad quedan 2. Compra o deja de comprar con esa cifra delante.

**Nota.** El resto de la cesta está **muy bien hecho** y sirve de modelo: `lo_que_queda_de_un_producto`
(`servicios.py:775-795`) devuelve `None` cuando no se puede restar, y el endpoint cuenta
`sin_cantidad` y `sin_poder_comparar` (`maestros.py:324-325`). Lo que falta es aplicar ese mismo
criterio dentro de `lo_gastado_de_un_producto`.

---

## A9. Sumas que tratan lo ausente como cero — **media**

**Dónde y qué se inventa**

| Fichero:línea | Qué suma | Qué se inventa |
|---|---|---|
| `cuaderno.py:807-808` | PDF del cuaderno: `f"{legal.formatea_numero(t.dosis or 0, 4)} {t.unidad_dosis}"` y `legal.formatea_numero(t.cantidad_total or 0, 4)` | El cuaderno **impreso** dice «0» en la dosis y en la cantidad de un tratamiento donde no hay dato. |
| `cuaderno.py:1070-1071` | Lo mismo en el CSV | Igual, en el volcado de texto. |
| `facturas.py:237-242` (`suman_las_lineas`) | `sum(linea.importe or 0.0 for linea in self.lineas)` | Una línea cuyo importe **no se leyó** suma cero, así que la comprobación «las líneas suman la base» puede dar por buena una factura a la que le falta una cifra. |
| `facturas.py:762-767` | El aviso que se le enseña al agricultor usa la misma suma | Dice «las líneas suman X y la base dice Y» sin decir que **un importe no se leyó**: el agricultor no sabe que le falta un número, cree que el papel cuadra mal. |
| `cuaderno_cyl.py:374-380` y `382-384` | `sum(linea.superficie_cultivada_ha or 0.0 ...)` y `sum(linea.superficie_sigpac_ha or 0.0 ...)` | Las hectáreas declaradas y las del SIGPAC del cuaderno importado (mismo patrón que A7). |
| `fincas_api.py:58-62` | `select(func.coalesce(func.sum(models.Parcela.superficie_ha), 0.0))` | Una finca **sin ninguna tierra** enseña «0 ha». Está documentado como intencionado (`schemas.py:1139-1143`), pero se lee igual que una finca de 0 ha. |
| `cuaderno_cyl_exportar.py:279` | `return int(db.scalar(consulta) or 0)` | Es un contador de filas: aquí el cero es correcto. **Sin hallazgo.** |

**Caso concreto (el de la factura).** Sube la foto de una factura de dos líneas. El lector lee bien
la primera (100,00 €) y de la segunda no saca el importe. La base imponible del papel son 250,00 €.
El aviso dice: «Las líneas suman 100,00 y la base imponible del papel dice 250,00. Puede faltar
alguna línea por leer.» El agricultor repasa la foto, ve las dos líneas y no entiende nada: lo que
falta no es una línea, es **un número**. Y si por casualidad las dos cifras coincidieran, el
programa diría que cuadra.

---

## A10. `sistema = "secano"` por defecto: lo que no se sabe se declara de secano — **media**

**Dónde**

- Modelos: `models.py:203` (parcela), `models.py:263` (cultivo de la parcela), `models.py:305`
  (grupo).
- Esquemas: `schemas.py:135` (`ParcelaEntrada`), `schemas.py:268` (`CultivoEntrada`),
  `schemas.py:281` (`GrupoEntrada`), `schemas.py:205` (`VariasParcelasDesdeSigpac`).
- El importador del cuaderno de la Junta: `cuaderno_cyl_api.py:296`
  (`sistema=linea.sistema or "secano"`), **y ahí el propio esquema dice lo contrario**:
  `schemas.py:1366-1367` documenta el campo del papel como
  `# secano | regadio | "" (el papel no lo dice)`.
- El cliente: `app.js:5651`, `5774`, `5896`, `6022` (`m.sistema || "secano"`,
  `sistema: m.sistema || "secano"`, `b.sistema || "secano"`), `app.js:8749` y `app.js:8795`.

**Qué dato se inventa.** Que la tierra es de **secano**.

**En qué caso concreto un agricultor vería un dato falso.** Tiene una tierra de regadío y no toca
el botón «secano/regadío» al darla de alta (viene marcado «secano» por defecto). Se declara de
secano. Y el sistema decide **qué columna del anexo III de la Orden MAV/398/2022 se compara**:
`validaciones.py:505-518` usa `cultivo.sistema` para elegir el límite, y el aviso dice
«sin riego» o «con riego». Un regadío apuntado como secano se compara contra el límite que no es.

---

## A11. `titularidad = "propia"` por defecto: la máquina de otro queda como tuya — **media**

**Dónde.** `models.py:491` (`titularidad: Mapped[str] = mapped_column(String(20), default="propia")`),
`schemas.py:418` (`titularidad: str = "propia"`).

**Qué dato se inventa.** Que la máquina es del titular y que va inscrita en el ROMA.

**En qué caso concreto un agricultor vería un dato falso.** Da de alta el pulverizador de la
empresa de servicios que le hace los tratamientos (que es el caso que el propio código describe en
`models.py:474-481`: tres pestañas, «maquinaria propia», «maquinaria ajena» y «equipos NO ROMA»).
Sin tocar el campo, la máquina queda como **propia** y con ITEAF, en la lista equivocada del
cuaderno de la Junta, y su `fecha_proxima_iteaf` se lee como una obligación suya.

---

## A12. `masa_agua_cerca` y `captacion_consumo_humano`: un «no» que nadie ha dicho — **media**

**Dónde.** `models.py:205-206` (`Boolean, default=False`), `schemas.py:137-138`
(`= False`). Y en la pantalla se ofrecen como un simple sí/no, **sin la opción «no lo sé»**:
`app.js:6178-6182` los declara `tipo: "si_no"`, mientras que la zona de nitratos —que es de la
misma familia y sí tiene tres estados— usa `tipo: "si_no_no_se"` (`app.js:6186`). La diferencia
entre los dos tipos está en `app.js:6574-6582`.

**Qué dato se inventa.** Que no hay masa de agua cerca y que no hay captación para consumo humano.

**En qué caso concreto un agricultor vería un dato falso.** Da de alta una tierra junto a una balsa
o a un arroyo y no toca las dos casillas. Su cuaderno dice que no hay agua cerca. Son dos datos
que la Orden MAV/398/2022 usa para las restricciones de abonado, así que el «no» por defecto
aligera las reglas que le aplican.

**Contraste:** la zona de nitratos **sí** está bien resuelta (`models.py:208` con
`default=None`, `app.js:6186` con las tres opciones), y `cuaderno_cyl.py` escribe en su comentario
de `AGENTS.md` que «en blanco es “no lo sé”». Es la excepción, no la regla.

---

## A13. `produccion_ecologica = False` por defecto apaga la comprobación ecológica — **media**

**Dónde.** `models.py:65` (`Boolean, default=False`), `schemas.py:36` (`= False`). La puerta que
abre: `validaciones.py:217-220`
```python
if explotacion is not None and getattr(explotacion, "produccion_ecologica", False):
    if not producto.permitido_ecologico:
        avisos.append(_aviso("V15_no_ecologico", "producto_id", True))
```

**Qué dato se inventa.** Que la finca **no** es de producción ecológica.

**En qué caso concreto un agricultor vería un dato falso.** Es agricultor ecológico y al darse de
alta no marca la casilla (o marca la finca a mano y no la toca). A partir de ahí, el programa
**deja de comprobar** que los productos que apunta se puedan usar en ecológico. No es que le diga
un dato falso: es que deja de avisarle de algo que la ley le exige, y él cree que el programa lo
vigila porque la sección de ecológico existe.

---

## A14. En el cliente (JavaScript), el hueco se convierte en 0 — **media** (con un caso **alta**)

**Hallazgo estrella: el `null` que el servidor se cuida de no inventar, el cliente lo inventa.**

- El servidor devuelve `cuantos_cosas`, `apuntes`, `tierras_con_cultivo` y `otras_cosas` como
  **`None`** cuando no los ha contado, con el motivo escrito: «un cero sería mentira»
  (`schemas.py:95-112`).
- Y el cliente los convierte en 0: `app.js:9118` (`anio_numero: Number(campana.anio) || 0`),
  `app.js:9125` (`Number(campana.apuntes) || 0`), `app.js:9169`
  (`const total = Number(campana.cuantas_cosas) || 0`), `app.js:9175-9177`
  (`Number(apuntes) || 0`, `Number(campana.tierras_con_cultivo) || 0`,
  `Number(campana.otras_cosas) || 0`).
- **Caso concreto**: la pantalla de campañas (`web/react/pantallas/campanas.js`) enseña el número
  de apuntes del año. Cuando el servidor contesta `null` —porque esa ruta no los cuenta,
  `explotacion.py:145-157`—, la pantalla dice **«0 apuntes en el cuaderno»** sobre un año que puede
  estar lleno. Es exactamente lo que `schemas.py:97-100` quiso evitar.

**Otros huecos que el cliente rellena con 0**

| Fichero:línea | Qué rellena | Caso |
|---|---|---|
| `app.js:3028` | `formateaNumero(aNumero(b.superficie_tratada_ha) || 0, 2)` | El resumen del tratamiento **antes de guardar** dice «0 ha» donde el agricultor no ha puesto superficie. |
| `app.js:3282` | `formateaNumero(aNumero(b.superficie_ha) || 0, 2)` | Igual en el resumen del abono. |
| `app.js:6792` | `superficie_ha: parcela.superficie_ha || 0` | Al tratar una tierra, la superficie que se manda es 0 si la tierra no la tiene (encadena con A7). |
| `app.js:8590` | `superficie_ha: Number(parcela.superficie_ha) || 0` | Igual al abonar. |
| `app.js:1008`, `app.js:1480`, `app.js:9968` | `venta.kilos \|\| 0` | Las ventas **en unidades** (lechugas) no pesan: `VentaSalida.kilos` es `None` (`schemas.py:774-777`). El total que se enseña es un total de kilos que **excluye** esas ventas sin decirlo en esa línea. (`InformeDeVentas.hay_unidades` sí lo dice, `schemas.py:797`, pero el resumen de pantalla no.) |
| `app.js:2785` | `unidad_dosis: (producto && producto.unidad_dosis) \|\| "L/ha"` | Sin producto elegido, la dosis viaja como «L/ha». |
| `app.js:10133` | `unidad: b.unidad \|\| "kg"` | Una venta sin unidad se apunta como kilos. |
| `app.js:1641` | `(junta && junta.hojas_con_datos) \|\| 0` | El cuaderno de la Junta sin datos dice «0 hojas». |
| `app.js:1004`, `app.js:6999`, `app.js:7159` | `Number(parcela.superficie_ha) \|\| 0` en sumas | Total de hectáreas de una finca contando las tierras sin superficie como 0 (mismo patrón que `fincas_api.py:58-62`). |

**Un caso que NO es un fallo, para que quede dicho**: `app.js:8023-8032`
(`sumaCompleta`) devuelve **`null`** —y la pantalla pinta «—»— cuando a alguna factura le falta una
cifra: «la suma de las demás NO es el total del año». Ese es el patrón bueno, y está a siete mil
líneas de los que no lo hacen.

---

## A15. `dias_hasta(...) or 0` en los avisos: hoy no se puede ejecutar — **baja**

**Dónde.** `maestros.py:1040`, `maestros.py:1070` y `maestros.py:1115`:
`"urgente": (legal.dias_hasta(aplicador.fecha_caducidad_carne, referencia) or 0) <= 7`.

**Qué pasaría.** Un `None` (fecha que no existe) se convierte en 0, y `0 <= 7` es verdadero: el
aviso saldría marcado como **urgente** sin fecha. **Pero hoy no puede pasar**: las tres líneas
están dentro de un `if legal.caduca_pronto(...)`, y `legal.caduca_pronto` devuelve `False` cuando
la fecha es `None` (`legal.py:104-109`). Es código muerto, no un dato falso. Se apunta aquí
porque el día que alguien reordene ese `if`, el `or 0` pasa a mentir en la dirección más
incómoda (avisar de urgencia por algo que no se sabe).

**Relacionado, y también sin uso**: `legal.esta_vigente` (`legal.py:91-95`) dice «sin fecha, se
considera no vigente» — es el criterio conservador correcto — y **no la llama nadie**: se ha
buscado en todo `backend/app/**` y su única aparición es su propia definición.

---

# b) Lo que es solo una oportunidad de claridad

Estos no son fallos: son sitios donde el programa podría decir **más** sin cambiar ningún dato.

**B1. `GET /api/avisos` existe, funciona y no tiene pantalla** (`maestros.py:1019-1195`). Toda la
lógica de caducidades (carné, ITEAF, producto, autorización excepcional) y del contraste del
número de registro contra el listado oficial del MAPA (`maestros.py:1145-1187`), con sus textos
ya escritos en `textos.py`. Y cuando no hay nada que avisar, devuelve
`{"tipo": "todo_bien", "mensaje": textos.mensaje("A8_todo_en_orden")}`
(`maestros.py:1189-1192`) — el mismo «todo en orden» de A3, pero aquí sobre una lista que **solo
mira lo que existe**: una finca sin máquinas, sin productos y sin aplicadores recibe el «así da
gusto». Es un hallazgo de A3 en potencia; hoy es solo una oportunidad porque **no hay ninguna
pantalla que lo llame** (verificado: «avisos» y «todo_bien» no aparecen en ningún fichero de
`backend/web/`).

**B2. La lista de «lo que falta» mira cuatro cosas** (`cuaderno.py:678-722`: tierra sin cultivo,
tratamiento sin justificación, sin dosis, sin aplicador o máquina). No mira: una tierra con 0 ha
(A7), un abono sin composición (A6), un producto sin plazo de seguridad (A5), un equipo sin ITEAF,
una tierra sin referencia del SIGPAC, ni un apunte sin superficie. Ampliarla es la forma más
barata de que A3 deje de poder pasar.

**B3. Dos esquemas declarados y sin usar.** `MedidaEntrada` (`schemas.py:813-818`) y
`AvisoGeneral` (`schemas.py:1179-1182`): se han buscado en todo `backend/app/**` y solo aparecen
en su propia definición. El primero lleva un `aplicada: bool = True` que, si alguien lo usara
alguna vez, sería un defecto del mismo tipo que A1.

**B4. `Parcela.superficie_sigpac_ha` no tiene puerta.** Está en el modelo (`models.py:200`), sale
en `ParcelaSalida` (`schemas.py:229`) y **no está en ninguna entrada ni aparece en la web**. Solo
la pueden rellenar el SIGPAC (`parcelas.py:202`) y el importador del cuaderno de la Junta
(`cuaderno_cyl_api.py:291`). Si el agricultor la tiene en el papel y quiere escribirla, no puede.

**B5. Los defectos de unidad afirman una unidad** (`"L/ha"` en `models.py:365` y `559`;
`"L"` en `models.py:370`; `"kg"` en `models.py:836` y `schemas.py:748`). No son peligrosos por sí
solos —el programa **sí** detecta después que dos unidades no se pueden comparar:
`legal.se_pueden_comparar` (`legal.py:217-226`) y `servicios.py:758`—, pero una ficha de producto
creada sin tocar la unidad dice «L/ha» aunque el producto se dosifique en kg/ha.

**B6. Un dato que el volcado oficial sí distingue bien, y conviene no estropear.** El cuaderno de
la Junta declara por su nombre lo que no puede escribir:
`cuaderno_cyl_exportar.py:110-118` («una hoja en blanco, porque parece rellena y está mal») y
`cuaderno_cyl_api.py:503-504` («lo que no esté puesto sale **en blanco** (no con un cero ni con un
dato inventado)»). Y el cuaderno propio tiene el mismo criterio en `schemas.py:97-100`. Ese es el
listón: **el día que se arreglen A6 y A7 hay que mantener esta misma regla en el PDF y en el CSV**,
que hoy la incumplen con `or 0` (A9).

**B7. Un contraste que hay que conservar tal cual**: `cuaderno_cyl.py:295-299` explica que la
casilla de zona de nitratos «en blanco no se sabe (nunca “no está”, que sería inventarse una
comprobación)», y el esquema lo declara como `True / False / None` (`schemas.py:1368-1369`). Es la
regla bien aplicada. El problema no es el criterio del proyecto: es que `servicios.py:102` y
`servicios.py:158` lo incumplen al guardar el apunte.

---

# Lo que NO se ha podido comprobar

1. **No se ha abierto la base de datos real** (`backend/cuedigital.db`) ni para leer. **No se sabe
   cuántas filas hay con cada uno de estos valores.** Ni cuántos productos están guardados con
   `autorizado = True` sin que nadie lo haya mirado, ni cuántas parcelas tienen
   `superficie_ha = 0`, ni cuántos apuntes tienen `en_zona_vulnerable = False` con la parcela en
   `None`. Sin esos conteos no se puede decir el alcance real de cada hallazgo, solo que el camino
   existe.
2. **No se ha arrancado el servidor ni la prueba de humo**, así que ninguno de los casos se ha
   reproducido en ejecución: están deducidos del código.
3. **No se ha mirado ninguna pantalla en un navegador.** Lo que se dice de la interfaz sale de
   leer `app.js` y `web/react/**`, no de verlo.
4. **No se ha verificado el impacto en el volcado oficial (IUWS).** `iuws_mapeo.py` (1.649 líneas)
   y `iuws_contenido.py` (749) mapean campo a campo qué sale de dónde; **no se ha comprobado** si
   `en_zona_vulnerable`, las riquezas o la superficie de la parcela llegan al sobre que se manda a
   la Junta. Lo único comprobado es que `en_zona_vulnerable` y las riquezas entran en el texto
   canónico que se firma (`firma.py:282`, `310`, `300-307`).
5. **No se ha comprobado si los tests existentes ya cubren alguno de estos casos** con el
   comportamiento actual. Hay 2.892 pruebas de Python y 643 de JavaScript (`AGENTS.md` §2) y no se
   han ejecutado: **cualquier cambio de un defecto puede tener un test que lo esté dando por
   bueno**, y hay que mirarlo antes de tocar nada.
6. **No se ha comprobado el efecto del `and_`/`or_` de `lo_aplicado_contra_el_plan`**
   (`servicios.py:244-261`) en el caso del plan de un grupo: se ha leído que solo filtra por
   parcela cuando `plan.parcela_id` no es nulo, pero **no se ha probado** qué devuelve con un plan
   de grupo.

---

# Plan de migración sin inventar históricos

## Regla que gobierna todo el plan

> **Un dato que no se sabe se queda como no se sabe, y se dice que no se sabe.**
> No se convierte en `False`, ni en `0`, ni en «secano», ni en «autorizado».

Y una regla de método, que es del contrato (§9) y de `AGENTS.md` §3.9:

> **Añadir columnas no es migrar datos.** `database.py:79-125` (`asegurar_columnas`) añade las
> columnas que falten con el valor por defecto de Python, y **no toca las filas que ya existen**:
> cambiar el defecto de un campo en el modelo **no cambia ni un dato guardado**. Y SQLite no sabe
> cambiar la nulabilidad de una columna que ya está creada (`database.py:109-117`): para eso hace
> falta una migración de verdad, con copia y ensayo.

## 1. Lo que se puede rellenar con evidencia (y con qué evidencia)

| Campo | ¿Hay evidencia en el sistema? | Qué se puede hacer |
|---|---|---|
| **`tratamientos.en_zona_vulnerable` y `fertilizaciones.en_zona_vulnerable`** (A2) | **Sí, parcial.** `parcela.zona_vulnerable_nitratos` es `True`/`False`/`None` y el apunte apunta a su parcela. | Recalcular **solo cuando `parcela.zona_vulnerable_nitratos` es exactamente `True` o `False`**, y dejar el apunte en «no comprobado» cuando es `None`. **Nunca poner `False` por defecto.** Ojo: cambia la huella firmada, así que hay que decidir si los cuadernos ya firmados se quedan como están (recomendado: **sí**, y que la re-firma quede como firma nueva, `models.py:1023-1026`). |
| **`parcelas.superficie_ha = 0` con `superficie_sigpac_ha` conocida** (A7) | **No sirve como evidencia directa.** Son magnitudes distintas a propósito (`models.py:195-199`: la del recinto entero y la cultivada). | **No copiar.** Marcar la tierra como «superficie pendiente de comprobar» y dar la pantalla que la pida. Copiar el SIGPAC a la cultivada sería inventar. |
| **`parcelas.superficie_ha = 0` con `ref_sigpac`** | **Sí, y es la evidencia buena**: se puede volver a preguntar al SIGPAC por el recinto (`sigpac.pedir_recinto`, `parcelas.py:553`). | Volver a preguntar y, si el recinto trae `superficie`, **proponerla** al agricultor para que la confirme. Proponer, no escribir. |
| **`productos_fitosanitarios.autorizado` y `permitido_ecologico`** (A1) | **No.** No hay nada guardado que diga si alguien comprobó el registro. | **No se puede rellenar.** Ver el punto 2. |
| **`fertilizantes.riqueza_*` y las `uf_*` de los abonos** (A6) | **No.** `lineas_de_factura` no tiene columnas de N/P/K (`models.py:1203-1235`), así que ni la factura trae la composición. | **No se puede rellenar.** El abono de verdad (el que se echó) tiene una composición que solo está en la etiqueta. |
| **`explotaciones.produccion_ecologica`** (A13) | **Indicio, no prueba.** Un papel en `documentos_anexos` con `carpeta`/`tipo` de ecológico, o un `ProductoFitosanitario.permitido_ecologico` a falso. | **No rellenar automáticamente.** Como mucho, **preguntar** al agricultor en la pantalla de la finca y dejar que lo marque él. |
| **`parcelas.sistema`** (A10) | **Indicio parcial**: `ParcelaCultivo.sistema` de la campaña, o el `sistema` del grupo. | Se puede **proponer** cuando la parcela y su cultivo del año dicen lo mismo. Si no coinciden, no se toca. |
| **`equipos_aplicacion.titularidad`** (A11) | **No.** No hay dato del que deducir de quién es la máquina. | **No se puede rellenar.** Preguntar. |
| **`parcelas.masa_agua_cerca` y `captacion_consumo_humano`** (A12) | **No.** | **No se puede rellenar.** Preguntar. |
| **`ventas_de_cosecha.tipo`** (A12-bis) | **Indicio**: hay `comprador` o no lo hay. | No sirve: una venta directa también tiene comprador. **No rellenar.** |
| **`tratamientos.en_zona_vulnerable` de apuntes de un grupo** | **No.** Un apunte con `grupo_id` y sin `parcela_id` puede tocar tierras en zonas distintas. | Se queda **«no comprobado»** y hay que decirlo en la pantalla y en el cuaderno. |
| Las `uf_*` de un abono con `riqueza_* = 0` | Ninguna. | **No se pueden recalcular**: `uf = kg/ha × riqueza / 100` (`legal.py:54-65`), y si la riqueza es 0 el resultado es 0. Recalcular con una riqueza inventada sería peor. |

## 2. Lo que debe quedarse como «desconocido / pendiente de comprobar»

Todo esto se queda **como está** (no se inventa) y **se declara**:

- **La autorización de cada producto del catálogo** (A1). Para cada fila existente, `autorizado` y
  `permitido_ecologico` no son un dato: son un defecto del programa. La marca honesta es
  «**no comprobado**», que es un tercer estado, no un `True`.
- **La condición ecológica de la explotación** (A13) mientras el agricultor no la declare.
- **La composición (N-P-K) de los abonos ya apuntados** (A6) sin ficha con riqueza.
- **La zona de nitratos de las tierras cuyo municipio no está en el listado** (`models.py:208`,
  que ya está bien) y de los apuntes hechos en ellas (A2).
- **La superficie cultivada de las tierras traídas sin superficie** (A7).
- **El plazo de seguridad de los productos que no lo traen** (A5), y por tanto los tratamientos
  hechos con ellos.
- **Las tres titularidades, las dos casillas de agua y el tipo de venta** ya guardados (A11, A12).
- **Los históricos firmados**: una firma es la prueba de lo que había
  (`models.py:1023-1030`). **No se reescribe un cuaderno firmado.** Si un `en_zona_vulnerable`
  viejo era un `False` inventado, se queda, y lo que se arregla es lo de adelante. Esto es
  coherente con `models.py:1024-1026` («si el cuaderno cambia después de firmarlo, lo que se hace
  es firmarlo otra vez, y quedan las dos»).
- **Y el índice anterior del cuaderno**: `GET /api/cuaderno/falta` con `esta_completo: true` sobre
  un cuaderno vacío (A3) — lo que se cambia es la frase, no un dato.

## 3. Qué pruebas harían falta ANTES de tocar nada

Ninguna de estas pruebas escribe en la base real: van sobre la suite (`backend/tests/`, que usa su
propia base, `AGENTS.md` §3.10).

**Pruebas que describen el comportamiento de hoy (para saber qué se está cambiando):**

1. Un producto creado **sin tocar el bloque de la autorización** se guarda con
   `autorizado = True` y `permitido_ecologico = True`, y `V15_no_ecologico` no salta en una finca
   ecológica. *(Reproduce A1.)*
2. Un tratamiento sobre una parcela con `zona_vulnerable_nitratos = None` se guarda con
   `en_zona_vulnerable = False`, y ese `False` aparece en el texto canónico de la firma. *(A2.)*
3. Con cero tierras y cero apuntes, `GET /api/cuaderno/falta` devuelve `esta_completo: true` y el
   mensaje `A8_todo_en_orden`. *(A3.)*
4. Un abono apuntado con `grupo_id` y sin `parcela_id` no cuenta para
   `nitrogeno_organico_en_la_parcela`, y las reglas `N1` de los 170 kg no saltan. *(A4.)*
5. Un tratamiento con un producto **sin** `plazo_seguridad_dias`, cosechado al día siguiente,
   **no** produce `V9_no_puedes_cosechar` ni ningún aviso. *(A5.)*
6. Importar una línea del cuaderno de la Junta sin superficie cultivada deja la tierra con
   `superficie_ha == 0` y **bloquea** el tratamiento siguiente con `V4_superficie_excedida`.
   *(A7.)*
7. `GET /api/productos/cesta/situacion` con dos tratamientos del mismo producto donde a uno le
   falta `cantidad_total`: el gastado suma solo el que tiene cantidad. *(A8.)*
8. `web/react/pantallas/campanas.js` recibe `apuntes: null` y enseña **0**. *(A14.)*

Estas ocho pruebas se escriben **primero**, se comprueba que pasan (describen lo que hay) y son el
contrato de lo que cambia. **Ninguna se borra después**: se actualizan diciendo por qué el
comportamiento nuevo es el bueno, como manda `AGENTS.md` §1.

**Pruebas de contrato para el comportamiento nuevo:**

9. `GET /api/cuaderno/falta` **no puede** devolver `esta_completo: true` cuando no hay ninguna
   tierra apuntada (o cuando hay menos de las que se declaran). El vacío tiene su propio mensaje,
   distinto del «todo en orden».
10. Un apunte nunca se guarda con `en_zona_vulnerable = False` si
    `parcela.zona_vulnerable_nitratos is None`. Los tres valores (`True`/`False`/«no comprobado»)
    tienen que poder distinguirse **en la respuesta de la API**, no solo en la base.
11. Un abono por grupo **cuenta** para el tope de nitrógeno; si por lo que sea no se puede contar,
    el programa lo dice y no calla.
12. Cosechar con un tratamiento cuyo plazo es desconocido produce **un aviso que dice que no se ha
    podido comprobar** (tercer estado, no «bien» ni «mal»; la regla está escrita en `AGENTS.md`,
    receta «Comprobar algo que viene de fuera», punto 2: «Hay tres finales, no dos: bien, mal, y no
    lo he podido comprobar»).
13. Una tierra con `superficie_ha == 0` **no** se puede dar por buena en silencio: al intentar
    apuntar algo en ella, el mensaje dice que falta la superficie y ofrece la pantalla que la
    arregla (regla de `AGENTS.md` §5: «no dejes al agricultor sin salida»).
14. `GET /api/analiticas/validar`, `GET /api/planes/validar` y `GET /api/medidas/validar` sin vale
    de sesión: **hoy pasan** (ver T01 §2.3). Se escribe la prueba del estado actual y se decide si
    se cierran.
15. Una prueba de la huella: cambiar cualquiera de estos campos **después** de firmar tiene que
    hacer que la firma deje de cuadrar (`firma.py` lo garantiza, `models.py:1028-1030`). Es lo que
    impide que la "corrección" de un histórico firmado pase inadvertida.

**Pruebas de la migración (sobre una copia, nunca la real):**

16. **Conteo antes y después**, campo por campo y tabla por tabla: cuántas filas cambian, cuántas
    se quedan en «no comprobado» y cuántas no se pueden tocar. Si un número no cuadra, la
    migración se para.
17. **Ida y vuelta**: aplicar la migración sobre la copia, comprobar el resultado, y comprobar que
    la vuelta atrás deja la copia byte a byte como estaba (comparando el fichero o su huella).
18. **La suite entera en verde antes y después**, y `scripts/humo.py` contra un servidor de
    prueba con su base aparte (`AGENTS.md` §2).

## 4. Orden propuesto (de menos riesgo a más)

1. **Primero las pantallas y los esquemas, sin tocar datos.** Añadir la opción «no lo sé» donde
   falta (A12), quitar el `or 0` del cliente (A14) y de los resúmenes antes de guardar
   (`app.js:3028`, `3282`), y que el vacío del cuaderno tenga su propia frase (A3). Nada de esto
   cambia un dato guardado y todo se ve en pantalla.
2. **Cerrar las puertas de entrada.** Hacer que los defectos dejen de afirmar: `autorizado` y
   `permitido_ecologico` pasan a tres estados (`None` = «no comprobado»); las riquezas de un abono
   dejan de tener `0.0` por defecto; `sistema`, `titularidad`, `masa_agua_cerca` y
   `captacion_consumo_humano` dejan de tener valor por defecto. Y las comprobaciones que dependían
   del defecto permissivo pasan a **avisar cuando no se sabe** en vez de callar. Esto afecta a
   filas nuevas; las viejas siguen como están hasta el paso 4.
3. **Arreglar las cuentas que hoy callan para el lado malo**: el tope de nitrógeno con grupos
   (A4), el plazo de seguridad desconocido (A5), el gasto de producto (A8) y los `or 0` del PDF y
   del CSV (A9). Son cambios de lógica, con sus pruebas, y no tocan la base.
4. **La migración de datos, al final, con copia y con ensayo.** Solo para las dos cosas que tienen
   evidencia: `en_zona_vulnerable` (solo donde la parcela dice `True` o `False`) y
   `superficie_ha` (preguntando al SIGPAC y proponiendo, no escribiendo). Todo lo demás se queda
   como «no comprobado» y se declara. **Antes**: copia de `backend/cuedigital.db` **y** de la
   carpeta de adjuntos (`CUEDIGITAL_ADJUNTOS`, `AGENTS.md` §3.10), ensayo de restauración, y
   conteos antes/después. **Nunca** sobre la base del agricultor sin copia previa.
5. **Y decirlo en la documentación y en la pantalla**, no solo en un comentario: qué campos están
   «pendientes de comprobar», cuántos son y desde qué fecha. Es la misma regla que ya se aplicó en
   el IUWS (`iuws.QUE_FALTA`, `iuws_api.py:79` y `125-135`): lo que no se sabe, se nombra, se
   cuenta y se dice de quién depende.

---

## Resumen de los hallazgos

| # | Qué se inventa | Dónde | Gravedad |
|---|---|---|---|
| A1 | Producto autorizado y permitido en ecológico | `models.py:373-374`, `schemas.py:314-315` | **alta** |
| A2 | «No está en zona de nitratos», y va al documento firmado | `servicios.py:102`, `servicios.py:158`, `firma.py:282`, `firma.py:310` | **alta** |
| A3 | «No te falta nada» sobre un cuaderno vacío | `cuaderno.py:724-729`, `textos.py:615`, `textos.py:931/940/3831` | **alta** |
| A4 | Cero nitrógeno en los abonos por grupo | `servicios.py:469-470`, `servicios.py:495-496`, `registros.py:369-380` | **alta** |
| A5 | «Se puede cosechar» cuando no hay plazo | `validaciones.py:769-770`, `registros.py:665-690` | **alta** |
| A6 | Cero nutrientes (N-P-K) y va al documento firmado | `models.py:389-391`, `schemas.py:353-355`, `firma.py:300-307` | **alta** |
| A7 | Cero hectáreas (y la tierra deja de poder tratarse) | `cuaderno_cyl_api.py:289`, `parcelas.py:194`, `models.py:193` | **alta** |
| A8 | El gasto de producto omite lo que no tiene cantidad | `servicios.py:43-45`, `servicios.py:640-645` | media-alta |
| A9 | Ceros en el PDF, el CSV y las cuentas de factura | `cuaderno.py:807-808`, `1070-1071`, `facturas.py:241`, `763` | media |
| A10 | «Secano» | `models.py:203/263/305`, `cuaderno_cyl_api.py:296`, `app.js:5651` | media |
| A11 | La máquina de otro queda como propia y con ITEAF | `models.py:491`, `schemas.py:418` | media |
| A12 | «No hay agua cerca» / «no hay captación» | `models.py:205-206`, `app.js:6180-6182` | media |
| A13 | La finca no es ecológica (apaga la comprobación) | `models.py:65`, `validaciones.py:217-220` | media |
| A14 | El `null` del servidor se convierte en 0 en la pantalla | `app.js:9118`, `9125`, `9169-9177`, `3028`, `3282`, `1008`… | media (**alta** en el caso de los apuntes de la campaña) |
| A15 | «Urgente» sin fecha — código que hoy no se ejecuta | `maestros.py:1040`, `1070`, `1115` | baja |

**Oportunidades de claridad**: B1 (`/api/avisos` sin pantalla y con «todo bien»), B2 (la lista de
«lo que falta» mira cuatro cosas), B3 (dos esquemas sin usar), B4 (`superficie_sigpac_ha` sin
puerta), B5 (las unidades por defecto), B6 (el criterio del volcado oficial, que hay que mantener),
B7 (el criterio de la zona de nitratos en el cuaderno de la Junta, que hay que recuperar en el
apunte).
