# Los enlaces de las tierras, y por qué hay más de uno

> **Para qué es este documento.** El encargo pide, **antes de mover acciones**, una tabla de enlaces
> antiguos y nuevos. Esto es esa tabla, con lo que **está comprobado en un navegador**, no lo que se supone.
> La comprobación vive en `scripts/verificar_los_enlaces_de_las_tierras.py` y hoy da **5 de 5**.

---

## 1 · Las direcciones que existen, y lo que abre cada una

*Las tres primeras están comprobadas abriéndolas de verdad en un navegador con una cuenta temporal.*

| Dirección | Pantalla | Qué abre (texto medido) |
|---|---|---|
| `#/tierras` | `pantallaMisCosas` | *«Mis parcelas, productos y máquinas»*: **siete secciones** — tierras, productos, abonos, aplicadores, asesores, equipos, instalaciones |
| **`#/tierras/mapa`** | `PantallaTierrasDeLaExplotacion` | *«**Mis tierras, en el mapa y en la tabla**»*: lista + mapa, con filtros, recuentos, selección y detalle |
| `#/mapa` | `pantallaMapa` | *«**Buscar mi tierra en el mapa**»*: la búsqueda en SIGPAC |
| `#/tierra?id=N` | la ficha de una tierra | una tierra concreta |
| `#/tierra_versiones` | las versiones de una tierra | lo que ha sido esa tierra |

### ***Una trampa que costó un intento***

*En `DIRECCION_PROPIA` la pantalla de las tierras completas figura como **`tierras_mapa`** —con guion bajo—,
y **`#/tierras_mapa` no abre nada**: contesta «esa dirección no lleva a ninguna parte». **La dirección de
verdad es `#/tierras/mapa`, con barra.***

*Lo cazó la comprobación, no la lectura del código: **el nombre de la clave interna no es la dirección**.
Queda escrito aquí para que nadie vuelva a probar `#/tierras_mapa`.*

---

## 2 · ***La doble puerta, dicha con precisión***

- **`#/tierras` no es la lista de las tierras**: es «mis cosas», **siete secciones**, y las tierras son una.
  *Redirigirla a la vista completa se llevaría por delante productos, abonos y máquinas.*
- **`#/tierras/mapa` es la vista completa** (lista y mapa juntos, con selección y detalle). **Es la buena.**
- **`#/mapa` no tiene nada que ver**: es la búsqueda en SIGPAC. *Confundirlas sería el error que este
  documento existe para evitar, y la comprobación lo verifica: **las tres pantallas son distintas**.*

***La doble puerta de verdad***: *las tierras se miran **desde «mis cosas»** —la lista de lo que hay dado de
alta— **y desde `#/tierras/mapa`** —con el mapa al lado—. **Las dos son legítimas y no se duplican**: una es
«dar de alta lo que uso», la otra es «ver mis tierras enteras».*

---

## 3 · La tabla de compatibilidad

**Ninguna dirección cambia de significado.**

| Enlace | Qué pasa con él | Por qué |
|---|---|---|
| `#/tierras` | **se queda** como «mis cosas», con sus siete secciones | *es la puerta del menú y no solo de las tierras* |
| `#/tierras/mapa` | **se queda** como la vista completa | *es la canónica de las tierras* |
| `#/mapa` | **se queda** como la búsqueda en SIGPAC | *es otra función; redirigirla perdería el alta de recintos* |
| `#/tierra?id=N` · `#/tierra_versiones` | **se quedan** | *una ficha y su historia se enlazan y se recargan* |
| `#/tierras_mapa` | **no se usa**: no abre nada | *no hay nada que conservar; se documenta para no reintentarlo* |

**Los puentes que ya existen**:

```
#/tierras/mapa  --t06-volver-->         #/tierras        (volver a la lista de lo que uso)
#/tierras/mapa  --t06-abrir-en-el-mapa--> #/tierras/mapa (abrir una tierra en el mapa)
```

---

## 4 · Lo que falta, y es el trabajo que viene

1. ~~Un puente desde «mis cosas» a la vista completa~~ — **HECHO** (21/10/2026): *la sección de las tierras
   lleva **«VER MIS TIERRAS EN EL MAPA»**, y al pulsarlo se llega a `#/tierras/mapa` **con la campaña y la
   finca en la dirección** (`#/tierras/mapa?campana=2026&finca=1`), que es el «enlace permanente al
   contexto» del contrato. **Comprobado pulsándolo en un navegador** (`5 → 8` comprobaciones, `0` fallos).*
   *Antes **no había ninguna puerta**: la pantalla solo se alcanzaba escribiendo la dirección a mano.*
2. **La lista con el mismo conjunto** — **MEDIDO a 1440×900** (21/10/2026): *con tres tierras dadas de alta
   por la puerta, la vista enseña **3 filas**; con `?q=TIERRA`, **2**; y al recargar, **2**.*
   **Lo que esto mide y lo que no**: *mide **la lista** (las filas de la tabla) y, desde el 22/10/2026,
   **también el mapa**: con una tierra **con forma** (WKT) y tres sin ella, la lista tiene **4 filas** y el
   mapa dibuja **1 polígono** — `#/pantalla svg polygon` —, *así que **no inventa las que no tienen forma**,
   que es la parte del código que decía «sin ninguna forma que enseñar no se dibuja un cuadro»*.
   **Lo que sigue sin medirse**: *que el polígono dibujado sea **el mismo** que su fila (mismo `data-id`)* —
   las dos pintan el mismo array, pero eso es lectura del código.*
   **En las tres anchuras sí está medido** (`scripts/verificar_las_anchuras_de_las_tierras.py`):
   **3 filas a 1440, 3 a 1024 y 3 a 390**, y **2 con `?q=TIERRA`** en las tres.
   ***Y ya no es un hallazgo***: *desde el 22/10/2026 **el móvil tiene tarjetas** — la tabla pasa a
   `solo-escritorio` y al lado hay tarjetas en `solo-movil`, con las mismas tierras y los mismos `data-accion`.
   **Medido**: 1440 → **3 filas**; 1024 y 390 → **3 tarjetas**. Ver «La aceptación grande», abajo.*
3. **Los filtros y la selección sobreviven a la recarga** — **MEDIDO** (21/10/2026): *el filtro viaja en la
   dirección (`?q=`) y recargar deja la vista filtrada; y `?id=N` deja **elegida esa tierra** —la fila lleva
   `tabla-fila-elegida`— **también después de recargar**. **Falta la selección múltiple** (`marcadas=`), que
   está escrita en la dirección pero **no se ha comprobado recargando**.

## 5 · Lo que queda de D04

| | |
|---|---|
| ✅ **la tabla de enlaces**, con cada dirección abierta | *5 comprobaciones* |
| ✅ **el puente** de la lista a la vista completa | *3, pulsándolo* |
| ✅ **el mismo conjunto** en la lista y el mapa *(4 filas / 1 polígono con forma)* | *6* |
| ✅ **filtro, selección y marcadas** sobreviven a la recarga | *4* |
| ✅ **las tres anchuras** (1440, 1024, 390), con y sin filtro | *6* |
| ✅ ***el móvil, con tarjetas*** *(el encargo: «en móvil: tarjetas útiles»)* | **hecho** — *1440: 3 filas · 1024 y 390: 3 tarjetas* |
| ⏳ *que el polígono y su fila lleven el mismo `data-id`* | *lectura del código, no medición* |

**Total medido en navegador**: **18 comprobaciones, 0 fallos** (`scripts/verificar_los_enlaces_de_las_tierras.py`
y `scripts/verificar_las_anchuras_de_las_tierras.py`).

---

## 5 · La aceptación grande, medida (22/10/2026)

*`scripts/verificar_la_aceptacion_de_las_tierras.py`. **Con 64 tierras de verdad**, dadas de alta por la puerta.*

| el encargo pide | medido |
|---|---|
| **aceptar con 64 tierras** | **64** ✅ |
| **una búsqueda que devuelve 8** | `?q=VEGA` → **8 filas** ✅ |
| **un filtro cruzado** | *Medina (16) ∩ VEGA (8) = **2*** ✅ — *un subconjunto de los dos* |
| **una tierra sin geometría** | ✅ *56 de las 64 no tienen forma, y se ven en la lista* |
| **un polígono con agujero** | ✅ *se dibuja; el mapa pinta **10 polígonos** de 64 tierras (8 cuadrados + el del agujero, que son dos anillos)* |
| **selección múltiple** | ✅ *(ya medido: `?marcadas=` sobrevive a la recarga)* |
| **enlace directo y recarga** | ✅ *recargar la misma dirección deja lo mismo* |
| **Atrás/Adelante** | ✅ *Atrás no rompe la pantalla* |

    Comprobaciones: 8   Fallos: 0

### ***Y lo que el encargo pide y NO está***

***«Exportación filtrada»*** — **HECHA** (22/10/2026): *el botón **«EXPORTAR LO QUE SE VE»** está en la barra de
acciones, y **se exporta lo que se ve**, con los filtros puestos.*

| | |
|---|---|
| *con `?q=VEGA` -8 tierras- se pulsa el botón* | *descarga `tierras-2026-10-22.csv`* |
| *el fichero* | ***9 líneas*** *(la cabecera y las 8)* |
| *y lleva las que se ven* | ***sin colarse las de fuera del filtro*** |

***Y se hace **en la pantalla**, no en el servidor***: *el filtro vive en `filtrarLasTierras`, y llevarlo a una puerta
nueva sería tener el mismo filtro en dos sitios que se pueden separar.* *El CSV va con punto y coma y con su marca de
orden de bytes, para que las tildes salgan bien en la hoja de cálculo.*

***Y «volver de la ficha con el scroll conservado»***: *los **filtros** sí vuelven —van en la dirección—; **el scroll**,
no se ha medido.*
