# Escalation del harness — D01 (cola local)

Fecha: 2026-10-30 (sesión `orca_session_id:8731d285-b2a5-4e50-a4cf-a77f587fe701`).

## Contexto exacto

- Run: `run_7247a1424dd1`
- Task: `task_021f054bf00a`
- Dispatch que reprodujo el bloqueo: `ctx_7d21d7748d9f`
- Dispatch actual: `ctx_063b97aec80f`
- HEAD: `d8f64ad537443e8753d6b8b7f650d090db11a132`
- tree_hash: `45ee86ec9a8ba6ed967c9fce39d5b08ec542def468134e07150cf022df493643`
- Rama: `ErDeivih/equipo-ia`

## Reproducción mínima

```
validar --project cuedigital --gate 945b9fd10422
validar --project cuedigital --gate 268c18a0cbc9
```

Salida literal (idéntica en las dos puertas):

```
{"ok": false, "error": "container_cleanup_unknown: comprobar Docker antes de declarar detenido"}
```

## Hechos

- El fallo ocurre **antes** de ejecutar ninguna prueba: no hay salida de `node --test` ni del guion.
- Afecta a **dos puertas distintas**: `945b9fd10422` (`tests_js/_probar-cola.mjs`, D01) y
  `268c18a0cbc9` (suite JavaScript completa).
- Ya hubo un **reintento** con el mismo resultado en el dispatch previo `ctx_7d21d7748d9f`.
- Por tanto es un bloqueo de entorno/limpieza de Docker, no un fallo del producto ni de las pruebas.

## Estado de la puerta

- `945b9fd10422` ya está registrada y apunta a `tests_js/_probar-cola.mjs`
  (cwd `backend`). `registrar_puerta` confirma `already_registered: true`.
- El fichero correcto es `backend/tests_js/_probar-cola.mjs`.
- `docs/revision-2026-10-19/_probar-cola.mjs` es un duplicado sin seguimiento: **no debe commitearse**.

## WIP conservado (sin commit)

```
 M docs/revision-2026-10-19/reproducir-cola.mjs   (+90 / -8)
?? backend/tests_js/_probar-cola.mjs
?? docs/revision-2026-10-19/_probar-cola.mjs      (duplicado, no commitear)
```

## Declaración

- **No** se declara ninguna puerta verde ni roja.
- **No** se cierra D01.
- **No** se declara el contenedor detenido.

Cuando el harness confirme la limpieza de Docker, hay que reejecutar `validar` con los IDs
reales sobre el **mismo** `tree_hash` antes de hablar de cerrar D01.

## Actualización 2026-10-30 — diagnóstico de preparación desplegable

Segundo dispatch que confirma el mismo bloqueo. Datos reales de este intento:

- Run: `run_7247a1424dd1`
- Task: `task_bb63e7fb382d`
- Dispatch: `ctx_6bec9e3eec1f`
- Sesión de trabajo: `orca_session_id:54291153-10d8-483f-aaa8-f04d4c52f7ac`
- HEAD: `d8f64ad537443e8753d6b8b7f650d090db11a132`
- tree_hash del intento: `3f3c7bfb2a1b276fd62d3ef3ba65e5922204473606f0a6287f3f985e0e8a427a`
- Rama: `ErDeivih/equipo-ia`

Se probaron **las cinco puertas** con `validar` y todas devolvieron el mismo error
**antes de ejecutar ninguna prueba**:

```
validar --project cuedigital --gate 268c18a0cbc9   # JS · 1221 pruebas
validar --project cuedigital --gate 35aebefd609d   # Python · 5649 pruebas
validar --project cuedigital --gate 603b7769d50e   # humo
validar --project cuedigital --gate e0053c194309   # recorridos · 188 comprobaciones
validar --project cuedigital --gate 945b9fd10422   # Prueba _probar-cola
```

Salida literal idéntica en las cinco:

```
{"ok": false, "error": "container_cleanup_unknown: comprobar Docker antes de declarar detenido"}
```

No hay salida de `node --test`, de `pytest`, de `andar_el_humo.py` ni de
`verificar_todos_los_recorridos.py`: el fallo es de limpieza del sandbox, no del producto.

## Estado de esta Task

- **No** se declara ninguna de las cuatro puertas verde ni roja.
- **No** se compara con la línea base (1221 / 5649 / 188 / humo correcto) porque no hubo ejecución.
- **No** hay reparación atribuible que hacer: no existe fallo reproducible del producto.
- **No** se cierra D01 ni se declara el contenedor detenido.
- WIP conservado sin commit: `docs/revision-2026-10-19/reproducir-cola.mjs` (modificado) y
  `backend/tests_js/_probar-cola.mjs` (nuevo). `docs/revision-2026-10-19/_probar-cola.mjs`
  sigue siendo un duplicado sin seguimiento que **no debe commitearse**.

## Actualización 2026-10-30 (tercero) — Task `task_bb63e7fb382d`

Nuevo dispatch confirma el mismo bloqueo antes de ejecutar ninguna prueba.

- Run: `run_7247a1424dd1`
- Task: `task_bb63e7fb382d`
- Dispatch: `ctx_1036bdb0a083`
- Sesión de trabajo: `orca_session_id:79b2b670-f358-410d-956a-9c1344ab2402`
- HEAD: `d8f64ad537443e8753d6b8b7f650d090db11a132`
- tree_hash del intento: `d9143695c50553c9ba23acac18068340a8edc10cd96314c3461ac37d9b882195`
- Rama: `ErDeivih/equipo-ia`

Puertas probadas y salida literal:

```
validar --project cuedigital --gate 22abaf5ed63e   # JS · 1221 pruebas (registrada nueva)
validar --project cuedigital --gate e84038c2909c   # Python · 5649 pruebas (registrada nueva)
validar --project cuedigital --gate 4693eabd9898   # humo (registrada nueva)
validar --project cuedigital --gate cb662e3c458e   # recorridos · 188 comprobaciones (registrada nueva)
validar --project cuedigital --gate 945b9fd10422   # Prueba preexistente
```

Salida literal idéntica en todas:

```
{"ok": false, "error": "container_cleanup_unknown: comprobar Docker antes de declarar detenido"}
```

Registrar puertas sí funciona (`registrar_puerta` devuelve `gate_id`), ejecutar no arranca.
El coordinador confirmó (msg `msg_f66e44e28fe3`) que es un fallo del harness, fuera de
alcance del trabajador y del coordinador, y pidió no declarar verde/rojo y esperar la
limpieza. Se conserva esta actualización como reproducción con marca temporal.

## Actualización 2026-10-30 (cuarto) — reintento `ctx_97962e60395f`

- Run: `run_7247a1424dd1`
- Task: `task_021f054bf00a`
- Dispatch: `ctx_97962e60395f` (retry de `ctx_063b97aec80f`)
- Sesión de trabajo: `orca_session_id:0949a21b-d291-4251-bdef-4182f208592f`
- Handle: `structworker_698f33f9-1acb-424a-ab27-ab7c2e6b61d5`
- HEAD: `d8f64ad537443e8753d6b8b7f650d090db11a132`
- tree_hash: `95235d50f26e8811c3ba5b47ff0b79813e9fb13947db435466dae0e5c6149df9`
- Rama: `ErDeivih/equipo-ia`

Puertas reintentadas y salida literal, idéntica:

```
validar --project cuedigital --gate 945b9fd10422   # _probar-cola (D01)
validar --project cuedigital --gate 22abaf5ed63e   # suite JavaScript completa
{"ok": false, "error": "container_cleanup_unknown: comprobar Docker antes de declarar detenido"}
```

El bloqueo persiste **antes** de ejecutar ninguna prueba: no hay salida de `node --test` ni del
guion. `orca status` está `ready`/`connected`; el fallo es del sandbox/Docker, no del producto.

Estado estático comprobado sin ejecutar (solo lectura): D01 sigue implementado e integrado —
`crearColaPorIntenciones` y migración en `nucleo.js`, turno transaccional (793-785),
`cola_en_indexeddb.js` con `hayIndexedDb`/`abrirLaBase`/`baseDelTurno`/`colaEnIndexedDb`/
`migrarDesde`, y su uso en `app.js` (447, 453, 1016-1018, 1072-1073). Existen las pruebas
`tests_js/cola_por_intenciones.test.js`, `cola_concurrencia.test.js`, `turno_transaccional.test.js`,
`cola_que_se_guarda.test.js`, `cola_el_dueno_del_origen.test.js`, `buzon_de_rechazos.test.js`,
`identidad_de_ejecucion.test.js` y `migracion_conservadora.test.js`.

No se declara ninguna puerta verde ni roja, no se cierra D01 y no se declara el contenedor
detenido. WIP sin commit sin cambios respecto a lo ya anotado.

Escalation enviada al Run: `msg_f26f332a7db8` (thread de `run_7247a1424dd1`), con la
reproducción mínima (dos gate IDs, `tree_hash 95235d50`, salida literal y `orca status`
`ready`). Cuarto intento de `validar` (`945b9fd10422`) inmediatamente antes del cierre:
mismo `container_cleanup_unknown`, sin ejecutar `node --test`. El turno se cierra como
**bloqueado por harness**, no como suite del producto en rojo.

Comprobación estática de coherencia del guion (sin ejecutarlo): `nucleo.js` exporta
`crearColaPorIntenciones` (379) y `pedirElTurnoTransaccional` (757); `baseDelTurno`
(`cola_en_indexeddb.js:69`) ofrece `transaccion(clave, cambia)` y resuelve
`{anterior, nuevo}`, que es exactamente lo que usa el doble `unaBaseTransaccional()` del
guion; el doble síncrono también respeta `undefined` = no escribe. No se detecta
desajuste entre guion, dobles y API real.

Registro de puertas verificado con `registrar_puerta` (idempotente, no altera nada):

- `945b9fd10422` → `tests_js/_probar-cola.mjs` (gate de D01).
- `22abaf5ed63e` → `tests_js/_probar-js.mjs` (suite JavaScript completa), **no** apunta a
  `_probar-cola.mjs`; se deja como está para no cambiar el significado de la puerta.
- El duplicado `docs/revision-2026-10-19/_probar-cola.mjs` **no** se registra ni se añade
  al CI: queda sin seguimiento para que lo retire el coordinador.

## Acción pendiente

Cuando el harness confirme la limpieza de Docker, reejecutar los cinco IDs sobre el
`tree_hash` vigente y consumir `{ok, results, tree_hash}`. Solo entonces se podrá comparar
con la línea base y, si hay rojo real, repararlo de forma atribuible.

## Actualización 2026-10-30 (quinto) — Task `task_bb63e7fb382d`, dispatch `ctx_1830dc5d7998`

- Run: `run_7247a1424dd1`
- Task: `task_bb63e7fb382d`
- Dispatch: `ctx_1830dc5d7998`
- Sesión de trabajo: `orca_session_id:a5396a6d-bf14-4abb-b0d8-4b6f3e1ea9ef`
- HEAD: `d8f64ad537443e8753d6b8b7f650d090db11a132`
- tree_hash de este intento: `78c8c2e1d95abd641e622f7e27aa2206a843a652ad4981a26a706afce2dbd7b9`
- Rama: `ErDeivih/equipo-ia`

Puertas canónicas probadas una a una y salida literal idéntica en las cuatro:

```
validar --project cuedigital --gate 268c18a0cbc9   # JS · 1221 pruebas
validar --project cuedigital --gate 35aebefd609d   # Python · 5649 pruebas
validar --project cuedigital --gate 603b7769d50e   # humo
validar --project cuedigital --gate e0053c194309   # recorridos · 188 comprobaciones
{"ok": false, "error": "container_cleanup_unknown: comprobar Docker antes de declarar detenido"}
```

El fallo ocurre **antes** de ejecutar ninguna prueba: no hay stdout de `node --test`, de
`pytest`, de `andar_el_humo.py` ni de `verificar_todos_los_recorridos.py`. `orca status`
está `ready`/`connected` y el bloqueo persiste pese a ello, así que no es un fallo del
producto ni una línea base incumplida (1221 / 5649 / 188 / humo correcto).

## Estado de esta Task

- **Ninguna prueba ejecutada.**
- **Ninguna** de las cuatro puertas se declara verde ni roja.
- **No** hay reparación atribuible: no existe fallo reproducible del producto.
- **No** se registran puertas equivalentes nuevas ni se duplican `_probar-*.mjs`; siguen
  vigentes `945b9fd10422` → `backend/tests_js/_probar-cola.mjs` y las cuatro canónicas.
- WIP conservado sin commit: `docs/revision-2026-10-19/reproducir-cola.mjs` (modificado) y
  `backend/tests_js/_probar-cola.mjs` (nuevo). `docs/revision-2026-10-19/_probar-cola.mjs`
  es un duplicado sin seguimiento que **no debe commitearse**.
- Pendiente: reejecutar `validar` con esos IDs sobre el mismo `tree_hash` cuando el harness
  confirme Docker limpio. La escalación del harness queda registrada con esta reproducción.
