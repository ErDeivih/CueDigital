# Traspaso: dónde está cada cosa, qué está probado y qué no

> **Para quien siga.** *La app existe en este repositorio, en la rama `integracion/cloud-estabilizacion-2026-10-21`. **No
> se empieza otra, no se reaplica ningún ZIP, no se cambia de framework y no se fusiona `main` ni `principal`.***
>
> ***Lo que hay aquí es lo que se ha hecho en esta tanda; lo que no, se dice.***

---

## 1 · Lo que está en verde, sobre el mismo HEAD

```
Python       5645 · 100 % sin una sola F
JavaScript   1212 · exit code 0
humo         «RESULTADO: todo correcto»
15 recorridos 188 comprobaciones · 0 fallos
```

*Con servidor, base, adjuntos y perfil de navegador **temporales**.*

---

## 2 · D01 — la conservación entre pestañas

### Lo hecho, y **cómo se sabe**

| pieza | dónde | cómo se comprueba |
|---|---|---|
| **una clave por intención** (apuntar y quitar **no leen**) | `nucleo.js` → `crearColaPorIntenciones` | `tests_js/cola_por_intenciones.test.js` — **6 pruebas**, con el otro escribiendo **antes** de que llegue la mía |
| **migración** sin perder `id_local`, cuenta, datos ni `clave_de_reenvio`; **sin borrar el origen hasta comprobar**; **corrupto conservado** | igual, `migrarDesde` / `migrarSiHaceFalta` | *las mismas 6 pruebas* |
| **enchufe en la app** (y migración al arrancar) | `app.js` | *la suite entera de JS* |
| **identidad de ejecución**, separada de la persistente (que se copia con `opener`) | `nucleo.js` → `identidadDeEjecucion`, `duenoDelTurno` | `tests_js/identidad_de_ejecucion.test.js` — 4 pruebas |
| **turno transaccional** (exclusión de verdad) | `nucleo.js` + `web/cola_en_indexeddb.js` | `tests_js/turno_transaccional.test.js` (6) **y** `scripts/verificar_la_cola_en_indexeddb.py` — **en Chromium**: dos a la vez y **gana una** |
| **el turno en la app**, por transacción cuando hay IndexedDB | `app.js` → `mandarPendientes` | *el recorrido de la cola, 9/9* |
| **los rechazos, uno por clave** (R1), **enchufado en las dos orillas** y con migración de la lista vieja | `nucleo.js` → `crearBuzonDeRechazos` · `app.js` → `vaciarLaCola({ buzon: cola.rechazos })` y `pintarAvisoPendientes` | `tests_js/buzon_de_rechazos.test.js` — **11 pruebas**, 6 de ellas de la migración · `tests_js/interfaz.test.js` — *la del enchufe: se guarda en una clave propia y **la pantalla lo lee de ahí*** · el recorrido de la cola, **9/9** con el instrumento leyendo las dos formas |
| **el instrumento de la revisión**, reparado y apuntando al camino real | `docs/revision-2026-10-19/reproducir-cola.mjs` + `reproducciones.txt` | *los siete casos vuelven a correr* · `--concurrencia` informa por separado **camino real** (conserva las dos intenciones), **cola de array** (sigue perdiendo; ya no enchufada) y **turno sin IndexedDB** (sin exclusión, declarado) · salida completa en `reproducciones.txt` |

***Lo último, con fecha*** *(04/11/2026)*: *los rechazos dejan de escribirse en el array compartido —donde dos a la vez
**se pisaban**— y pasan a un buzón de **una clave por rechazo**. La pantalla los lee de ahí, no de la lista. Lo que
quedara en las listas viejas **se migra al arrancar**: se comprueba que está, y solo entonces se borra el origen; un
JSON corrupto **se conserva**; y si el origen cambia entre la comprobación y el borrado —una pestaña vieja
escribiendo— **no se borra**. El motivo y la reversibilidad están en `/DECISIONES.md`.*

### ***Lo que falta, y es lo que impide cerrar D01***

***La aceptación de dos pestañas reales***, punto por punto de la revisión: *apuntar/apuntar y apuntar/quitar con **barrera
tras la última lectura**, **ventanas con `opener`**, recarga, cierre, **caducidad mientras un POST está pendiente**,
**almacenamiento lleno** y **retorno del dueño**.*

***Y por qué no está***: *`scripts/navegador_cdp.py` maneja **un solo destino** — `_orden` no lleva `sessionId`. **Con eso
no se pueden manejar dos pestañas a la vez.*** *Está especificado en `CONCURRENCIA_ENTRE_PESTANAS.md`: `Target.createTarget`
(o `window.open`, que además **es la que comparte `sessionStorage`**), `Target.attachToTarget` con `flatten: true`, y
**`sessionId` en cada `_orden`**.*

***El atajo que no toca el arnés compartido***: *abrir la segunda pestaña por el **endpoint HTTP de CDP** (`PUT
/json/new?<url>`) y hablarle con un cliente mínimo aparte.*

---

## 3 · D04/D05 — cerrado y medido

| lo que pide la revisión | medida |
|---|---|
| **a 320×700 una primera tarjeta sin bajar** | ***dentro*** *(antes: **fuera, top=742**)* |
| **a 390×844** | ***dentro*** |
| **el botón del nombre, con el suelo** | ***106×44*** a 390 y ***88×48*** a 320, **letra 18** |
| **a 1024 el acceso a columnas y acciones** | *la tabla **desborda (1070 de 721)** y **se recorre con el teclado*** (`tabIndex=0`, `role=region`, con su nombre) |
| **tres / 64 tierras, filtro, vacío** | `scripts/verificar_los_estados_de_las_tierras.py` — **6/6**, con las capturas en `docs/capturas-de-anchuras/estados/` |

***Lo que se movió, y por qué se puede***: *«marcar todas», «desmarcar todas» y el recuento pasan **detrás de los
resultados**; la explicación y el «agrupar», también. **La selección no se toca** —las casillas están en cada tarjeta—,
**ni la búsqueda ni los filtros activos**.*

***Lo que NO cubre este instrumento***: *el **estado de fallo**. Lo cubre `verificar_los_estados_de_fallo.py`, con el proxy
que falla una ruta.*

---

## 4 · D07 — abierto, con el inventario hecho

***El inventario*** *(lo que la revisión pide primero)*: *en `app.js` hay **19 escrituras manuales del DOM** y **solo una
toca un contenedor que React monta**: `vaciarElMarco()` → `contenedor.replaceChildren()` sobre `#marco`.*

***Y de ahí sale la regla***: *antes de vaciar un contenedor de React, **desmontar su raíz**.*

***Se intentó dos veces y las dos se revirtió***, con los números en `RENDIMIENTO.md`:

1. *cachear una raíz por contenedor → **rompió reservas** (sin desmontar al vaciar)*;
2. *cachear **y** desmontar en `vaciarElMarco()` → **rompió reservas y cinco pruebas de montaje** a la vez.*

***El tercero tiene que empezar por esas cinco pruebas de montaje*** —*«mis cosas se le pide a React», «el dictado», «la
ayuda»…—, **no** por el registro de raíces, que es lo que se tocó las dos veces.*

***Y sigue pendiente*** *el registro de **raíces creadas/desmontadas/activas**, acotar `montajes` y `montajesDelMarco`
(la revisión midió **2→102** y **2→101**), y **100 transiciones con `timeOrigin` constante e identidad de pantalla**.*

---

## 5 · Un riesgo que hay que atajar antes de un piloto

***La suite de Python es intermitente.*** *Cinco pruebas de recorrido distintas han fallado **en algún momento** bajo la
suite entera y **las cinco pasan corridas solas**; la suite **también ha pasado limpia**.*

***Descartado con medidas***: *el `timeout` del `subprocess` (**900 s**), que estén rotas (pasan solas) y que lo rompa un
cambio de esta tanda (fallaron antes y después, en pruebas distintas).

***Localizado***: *la prueba solo mira `returncode == 0` y **«Fallos: 0»** en la salida; cuando falla, **es el guion el que
cuenta un fallo** —una pantalla que no se asentó bajo carga—, **no un plazo agotado**.*

***Una suite que falla al azar deja de creerse***, y eso es peor que no tenerla.

---

## 6 · Las tres cosas que yo haría, en este orden

1. **El arnés de dos destinos** (`sessionId` en `_orden`, o la segunda pestaña por `PUT /json/new`) y **la aceptación de
   D01** de la revisión. *Es lo que impide decir que D01 está cerrado.*
2. **D07**, empezando por las **cinco pruebas de montaje**.
3. **La estabilización de los recorridos**.

***Y la pasada completa al final***: *`pytest`, `node --test`, `andar_el_humo.py` y
`verificar_todos_los_recorridos.py`, sobre el mismo HEAD.*

---

## 7 · Lo que este documento no es

***No es un cierre.*** *D01 no está cerrado —le falta su prueba—, D07 está abierto, y la suite tiene una intermitencia
localizada pero no arreglada.* **Lo que sí es**: *el mapa de qué está probado, con qué, y qué no; para que el siguiente no
empiece por donde ya sabemos que se rompe.*
