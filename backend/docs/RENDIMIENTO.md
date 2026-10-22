# Rendimiento: lo medido

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
