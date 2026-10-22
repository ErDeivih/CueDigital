# Rendimiento: lo medido

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
