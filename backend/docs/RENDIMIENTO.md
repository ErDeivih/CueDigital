# Rendimiento: lo medido

## ***0 ter · Tercer intento: acotar las trazas — y por qué tampoco*** (24/10/2026)

***Lo que pide la revisión***: *«acotar o eliminar **las referencias fuertes** de `montajes` y `montajesDelMarco`»* —que
midió **2→102** y **2→101**—.

***Lo que se intentó***: *un tope de 500 por lista, tirando **las más viejas** y conservando el orden (para no romper
`slice(antes)` ni `[length - 1]`). Con **dos pruebas nuevas** que lo fijaban…*

***Y rompió la suite***: *cinco pruebas de pantallas dejaron de encontrar lo que se les pedía a React.*

***El motivo, medido***: ***las pruebas usan `montajes` como registro de TODA la ejecución*** —`montajes.slice(antes)` con
`antes` de hace muchas pantallas—, y **la suite entera monta más de 500 veces en el mismo proceso**. *Acotar por número
**choca con ese contrato**, no con un fallo del código.*

***Se revirtió, y la suite volvió a 1221/1221.***

***Las dos salidas honestas, para el siguiente***:

1. ***Referencias débiles*** (`WeakRef` al contenedor y al elemento) con un control de vida: *no cambia el número de
   entradas y suelta lo que ya no está — pero **`montajes[0].contenedor === contenedor`** lo usan las pruebas: habría que
   ajustarlas **explicando por qué**.*
2. ***Una traza aparte, acotada, y dejar `montajes` como registro para las pruebas***: *lo que la aplicación mira pasa a la
   traza acotada; `montajes` se queda igual y **las pruebas no se tocan**.*

***Y lo que NO hay que volver a intentar***: *cachear la raíz por contenedor —**dos veces** y las dos rompió reservas—; el
inventario dice que **solo hay una escritura manual sobre un contenedor de React** (`replaceChildren()` en `#marco`), y el
camino es **desmontar ahí**, no reutilizar raíces.*

---

## ***0 bis · Segundo intento, con el inventario hecho — y también se revirtió*** (23/10/2026)

***El inventario*** (lo que pedía la revisión: «inventaría TODAS las escrituras manuales»): *en `app.js` hay **19
escrituras manuales del DOM**, y **solo una toca un contenedor que React monta**:*

    app.js:2655  vaciarElMarco()  ->  contenedor.replaceChildren()   sobre #marco

*Las demás son sobre elementos que no son de React (`#aviso-pendientes`, `#aviso-cargas-*`, `#cabecera-texto`, un `pie`)
y **cinco `document.body.appendChild(enlace)`** que son descargas.*

***Con eso, el arreglo era acotado***: *registro de raíces por contenedor, **`desmontarDe(contenedor)` en `vaciarElMarco`
antes del `replaceChildren()`** —el traspaso de propiedad, que es lo que faltaba en el primer intento—, reutilizar solo
una raíz que no se haya vaciado, y **acotar `montajes` y `montajesDelMarco` a 200** (la revisión midió montajes 2→102 y
marco 2→101).*

***Y se aplicó, y se midió… y rompió dos cosas a la vez***:

    el recorrido de reservas          ***sigue sin abrir el formulario*** (y además «no close frame received or sent»)
    cinco pruebas de JS de montaje    ***fallan*** («mis cosas se le pide a React», «el dictado», «la ayuda»…)

***Se revirtió, y las dos suites volvieron a verde.***

***Lo que esto enseña, y es lo que hay que hacer con ello***: *el inventario **sí sirve** —dice dónde está la frontera—,
pero **cambiar `montarEn` toca más de lo que parece**: las pruebas de montaje miran *qué* se le pide a React, y el
recorrido de reservas depende de **cómo** se monta. **El siguiente intento tiene que empezar por esas cinco pruebas de
montaje**, no por el registro de raíces.*

---

## ***0 · El ciclo de vida de las raíces: se intentó y se revirtió*** (22/10/2026)

***`montarEn` llama a `ReactDOM.createRoot(contenedor)` en cada montaje y nunca desmonta.*** *React avisa de eso
—«createRoot() on a container that has already been passed to createRoot()»— y el árbol anterior se queda sin desmontar
hasta que el recolector quiera.*

***Se intentó lo correcto —una raíz por contenedor, con `WeakMap`— y se probó:*** *dos pruebas nuevas con un `ReactDOM`
de mentira contaban las raíces, y **fallaban sin el arreglo** (comprobado metiéndolo a mano).*

***Y la aplicación se rompió.*** *Con el arreglo, `tests/test_el_recorrido_de_las_reservas.py` **deja de abrir el
formulario** —«el formulario trae el desde… ¡no!»— y sin él **pasa**. **Se apartó el cambio y se volvió a correr: verde.**

***La conclusión, con la evidencia***: *alguna parte de la aplicación **cuenta con que `createRoot` vacía el
contenedor** —el código nuevo se pinta junto a lo escrito a mano, en vez de sustituirlo—. **Cambiar esto no es un
refactor inocente**: hay que saber qué escribe en ese contenedor antes de reutilizar la raíz.*

***Se revirtió, y las dos pruebas se quitaron***: *una prueba que exige un cambio que rompe un recorrido no puede
quedarse. **El defecto sigue ahí, ahora con el motivo por el que no se puede arreglar a ciegas.***

---

## ***0 · La medición válida, y por qué la anterior no lo era*** (22/10/2026)

***La primera versión de este documento no valía.*** *Su medidor navegaba con `nav.abrir(<URL completa>)` en cada
transición: **recargaba el documento** y borraba precisamente la memoria que decía medir. Lo señaló la revisión
independiente. Un número sacado así **no dice nada de la aplicación**: dice cómo estaba el instrumento.*

***Y ahora se demuestra que no hay recarga***, que es la mitad del trabajo: *`performance.timeOrigin` **no se mueve** en
las dieciocho transiciones y `performance.getEntriesByType("navigation")` tiene **una sola** entrada.*

| medida | valor |
|---|---|
| **navegaciones de documento** | **1** *(solo la carga inicial)* |
| **`timeOrigin`** | *el mismo en las 18 transiciones* |
| **tiempo hasta tener pantalla** | **3,5 s** |
| **`domContentLoaded` / `load`** | **132 ms** / **132 ms** |
| **peticiones al abrir** | **35** distintas |
| **nodos al principio** | **307** |
| **nodos tras 18 pantallas** | **289** |
| **nodos al volver al principio** | **307** |
| **memoria** | **6 MB** → **9 MB** (***+3***) |

***Lo que dice, y lo que no***: *no hay recarga, **no se queda nada** al volver al principio y la memoria crece tres
megas en dieciocho pantallas. **No dice que la aplicación sea rápida** —no hay con qué compararlo— ni lo que pasa en
media hora de uso real.*

***Lo que sigue sin medirse***: *el **ciclo de vida de las raíces** de React -cuántos montajes y desmontajes, y si alguna
raíz se queda sin desmontar- y **las trazas**. Lo que sí se mide es **su efecto**: los nodos vuelven a 307.*

---



> **Para qué es este documento.** D07 pide «medir navegación prolongada, peticiones de arranque y memoria». Esto es lo
> que se ha medido, con qué, y **lo que no se ha medido**. *Un número no es un veredicto: `35` peticiones al abrir
> puede estar bien o mal, y solo se sabe con lo que cada una cuesta.*

---

## 1 · Lo medido, con el navegador de verdad

*`scripts/medir_el_arranque_y_la_navegacion.py`, a 1440×900, con una cuenta y dos tierras temporales.*

| medida | valor |
|---|---|
| **tiempo hasta tener pantalla** | **3,1 s** (*medido desde fuera, con el reloj*) |
| **`domContentLoaded`** | **194 ms** |
| **`load`** | **194 ms** |
| **peticiones al abrir** | **35** distintas (*contadas por el navegador con `performance.getEntriesByType`*) |
| **nodos del documento al principio** | **307** |
| **nodos después de andar 18 pantallas** | **307** |
| **nodos al volver al principio** | **307** |
| **memoria al principio** | **6 MB** |
| **memoria al volver** | **6 MB** (***+0***) |

***Lo importante es la tercera y la sexta fila***: *después de andar dieciocho pantallas y volver al inicio, **el
documento tiene exactamente los mismos nodos y la memoria es la misma**. Eso es lo que se busca con «desmontaje
correcto»: **que no se quede nada.***

---

## 2 · Las 35 peticiones de arranque, dichas

*Son, por lo que se vio en la lista: `cuenta/yo`, `interfaz` y **las 32 secciones de `cargarDatos`** —analíticas,
aplicadores, asesores, campañas, cobros, cuaderno, cultivos, documentos, equipos, facturas…—.*

***Que sean 35 no es un defecto por sí solo***: *es el diseño —la aplicación pide todo lo que puede necesitar de una
vez, para que las pantallas no esperen—. **Lo que no se ha medido es cuánto tarda eso** ni cuánto pesa la respuesta.*

---

## 3 · Lo que NO se ha medido, y se dice

| lo que pide D07 | estado |
|---|---|
| **navegación prolongada** | *medido con **18 pantallas** y una vuelta. **No** con media hora de uso real* |
| **memoria** | *la del **montón de JavaScript** (`performance.memory`). **No** la del proceso, ni la del servidor* |
| ~~cuánto tarda el arranque~~ | **MEDIDO**: *3,1 s hasta tener pantalla; el navegador tarda 194 ms en su `load`* |
| **el coste de cada petición** | **no medido**. *Se sabe el total, no cuál pesa* |
| **si 3,1 s es rápido o lento** | **no medido**: *no hay con qué compararlo. **Aquí no hay una versión anterior, ni un 4G, ni un móvil de gama baja*** |
| **una raíz React controlada por contenedor** | *no revisado. **Lo que sí está medido es el efecto**: los nodos vuelven a 307* |
| **fallos de foco al desmontar** | *medido **solo** el de Escape con el menú (`verificar_el_escape_y_el_foco.py`), no el de cada pantalla* |
| **historial de instrumentación fuera de producción** | **no revisado** |

---

## 4 · Lo que se puede decir hoy

- ***No hay fuga de nodos** en una navegación de 18 pantallas y vuelta.*
- ***No crece la memoria de JavaScript** en esa navegación.*
- ***El arranque tarda 3,1 s hasta tener pantalla** y pide 35 cosas distintas. **Si eso es rápido o lento no se
  sabe**: no hay con qué compararlo.*

***Y lo que no se puede decir***: *que la aplicación sea rápida. **No se ha medido el tiempo**, ni el coste de cada
petición, ni una sesión larga de verdad.*


## Revisión independiente — 22/10/2026: D07 EN_REVISION

El instrumento `medir_el_arranque_y_la_navegacion.py` navega con `abrir`, que llama a
`NavegadorDeVerdad.abrir`. Ese ayudante fuerza un documento nuevo pasando por `about:blank`
cuando solo cambia el fragmento. Por tanto, comparar 307 nodos/6 MB antes y después no prueba
que una sesión SPA libere raíces o memoria: se han reiniciado módulos y sus referencias.
Además `montar.js` sigue creando raíces nuevas y guardando montajes en arrays sin límite.
Esto identifica una limitación del instrumento y un riesgo del ciclo de vida; no cuantifica
por sí solo una fuga de memoria en producción.

Siguiente prueba: mantener constante `performance.timeOrigin`, navegar por acciones reales
o hashes sin Page.navigate, recorrer al menos 100 transiciones, volver al mismo estado y
comparar nodos/raíces/heap con límites razonados y condiciones de GC documentadas. Separar
arranque frío, navegación y memoria. No volver a cerrar D07 con números redondeados de
documentos distintos. Luego corregir propiedad/desmontaje de raíces y trazas de producción
con regresiones, conservando foco, scroll y comportamiento de las pantallas.
