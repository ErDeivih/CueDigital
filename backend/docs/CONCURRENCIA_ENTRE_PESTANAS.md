# La concurrencia entre pestañas: reproducida, y qué hace falta

> **Para qué es este documento.** La revisión del 23/10 reproduce **tres defectos** con su propio diagnóstico. Esto
> recoge **la salida exacta**, **por qué la solución que hay no puede funcionar** —la mía incluida— y **el diseño** que
> sí puede, con su criterio de aceptación. *Lo que **no** hay aquí es un arreglo: **esto es el porqué y el cómo**, para no
> volver a intentar lo que ya sabemos que no funciona.*

---

## 1 · La salida, tal cual

```
node docs/revision-2026-10-19/reproducir-cola.mjs --concurrencia
{
  "apuntar":        { "esperados": ["A", "B"], "conservados": ["A"] },   ← B perdido
  "quitar":         { "esperados": ["B"],      "conservados": [] },       ← B borrado
  "turno_simultaneo": { "A": true, "B": true }                            ← los dos con el turno
}
exit code 1
```

---

## 2 · Por qué **releer no arregla nada** (y por qué mi arreglo no bastó)

*El diagnóstico envuelve el almacén así:*

```js
getItem(k) {
  const anterior = base.getItem(k);          // se lee ANTES de que el otro escriba
  … el otro escribe …
  return anterior;                           // ← y se devuelve el valor VIEJO
}
```

***La interferencia no ocurre entre mi lectura y mi escritura: ocurre dentro de la lectura, y lo que se devuelve es
lo de antes.*** *Por eso **da igual releer**: la segunda lectura también puede ser vieja. **Leer-modificar-escribir no
es transaccional, y ningún número de lecturas lo convierte en transaccional** — es exactamente lo que dice la
revisión: «releer por segunda vez un array no hace transaccional leer/modificar/escribir».*

*Mi arreglo del 22/10 —releer justo antes de escribir— **solo cubría una intercalación en la primera lectura**, que es
lo que probaban mis pruebas. **Con la intercalación en la última lectura, pierde.***

---

## 3 · El diseño que sí puede

***La regla***: *que **no haya** leer-modificar-escribir sobre estado compartido. Dos piezas:*

### 3.1 · Conservación: **una clave por intención**

| operación | hoy | como tiene que ser |
|---|---|---|
| **apuntar** | *leer el array, añadir, escribir el array* | **`put` de su propio registro** — *no se lee nada* |
| **confirmar / quitar** | *leer, filtrar, escribir* | **`delete` de su propio registro** — *no se lee nada* |
| **apartar (rechazo)** | *leer rechazados, añadir, escribir* | **`put` de su propio registro de rechazo** |
| **recuperar** | *leer, mover, escribir* | **una transacción** que borra uno y escribe el otro |

***Y el listado, de un índice que se reconstruye***: *con **IndexedDB** se recorre un `objectStore` **dentro de una
transacción**; con `localStorage` hay que enumerar claves, que es lo que el almacén del diagnóstico **no** ofrece —
por eso la preferencia de la revisión es IndexedDB y no un truco sobre `localStorage`.*

### 3.2 · El turno: exclusión **dentro de una transacción**

*Con IndexedDB, `pedirElTurno` es una transacción `readwrite` sobre el registro del turno: **leer y escribir dentro de
la misma transacción** es atómico y **ninguna otra pestaña puede intercalarse**. Con Web Locks sería equivalente, pero
hay que **adaptar a los consumidores a la espera** y **decidir qué pasa si no existe** — la revisión lo advierte: «no
prometer exclusión con un fallback al mismo read/modify/write».*

***Sin IndexedDB*** *(navegador antiguo): se degrada con honestidad —**sin turno no se vacía** y se dice— o con una
exclusión por escritura-y-verificación con desempate determinista, **que hay que demostrar**, no suponer.*

### 3.3 · La identidad: **dos, y separadas**

***El defecto***: *`sessionStorage` **se copia al abrir una ventana con `opener`**. Comprobado en Chromium: **padre e hija
tienen el mismo `cuedigital.procesador`**. Así que mi «procesador = pestaña» **no distingue** padre de hija, y las dos
piden el turno como si fueran la misma.*

| identidad | para qué | dónde vive |
|---|---|---|
| **de ejecución** | *distinguir **esta** pestaña de cualquier otra, incluida una abierta con `opener`* | *en memoria, generada al arrancar — **no** en `sessionStorage`* |
| **persistente** | *que una **recarga** de la misma pestaña siga siendo la misma* | *en `sessionStorage` (o el almacén que toque), **aparte** de la de ejecución* |

### 3.4 · La migración, sin perder nada

- *cada pendiente que ya está en `cuedigital.pendientes` pasa a su registro **con su `id_local`, su cuenta, sus datos y su
  `clave_de_reenvio`**;*
- ***no se borra el origen hasta comprobar que el destino está***;
- ***un JSON corrupto se conserva*** *para poder recuperarlo: **no se convierte en cola vacía** que la siguiente escritura
  sobrescribe.*

---

## 4 · El criterio de aceptación (de la revisión)

*Dos pestañas reales · barreras de intercalación **tras la última lectura** · `apuntar`/`apuntar` y `apuntar`/`quitar` ·
ventanas con `opener` · recarga · cierre · caducidad mientras un POST está pendiente · almacenamiento lleno ·
retorno del dueño.*

***Cada intención queda pendiente, rechazada recuperable o confirmada. Ninguna desaparece.*** *Y el servidor desduplica
los reintentos por `clave_de_reenvio`.*

***Las respuestas tardías 200/422 de A ya pasan la revisión del cableado real: eso se conserva.***

---

## 5 · El estado, al 23/10 (después de tres pasos)

| pieza | estado |
|---|---|
| **conservación en el navegador** | **hecha** — *una clave por intención, sin leer para escribir; migración al arrancar y al leer; **enchufada** en `app.js`* |
| **el turno** | **hecho** — *`pedirElTurnoTransaccional` sobre una transacción, **probado contra el IndexedDB de Chromium**: dos adquisiciones a la vez y **gana una**; **enchufado** en `mandarPendientes` cuando hay IndexedDB* |
| **identidad de ejecución** | **hecha** — *en memoria, separada de la persistente, que se copia con `opener`* |
| **el recorrido de la cola** | ⚠️ ***8 de 9***: *lee la clave vieja (`cuedigital.pendientes`), y la cola ahora guarda **una clave por intención**. **Hay que adaptar sus dos lecturas** —como ya se hizo en `tests_js/interfaz.test.js` con el ayudante `losPendientes`—; el resto del recorrido pasa* |
| **las pruebas de aceptación** | **sin hacer** — *dos pestañas reales, `opener`, recarga, cierre, caducidad con un POST pendiente, almacenamiento lleno, retorno del dueño* |

***Y lo que no se promete***: *sin IndexedDB, la aplicación **usa el turno de siempre y no dice** que vacía una sola
pestaña.*

## 5 · Lo que este documento **no** es

***No es el arreglo.*** *Es el porqué, el cómo y el criterio — para que el siguiente intento no sea otro re-leer, que ya
sabemos que no funciona.*
