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
   **Lo que esto mide y lo que no**: *mide **la lista** (las filas de la tabla). **El mapa no se cuenta** —
   recibe el mismo array (`vista.tierras`, una sola vez) y por eso **no puede discrepar**, pero eso es una
   lectura del código, no una medición. **Faltan 1024 y el móvil**, y **falta contar lo que dibuja el mapa**.
3. **Los filtros sobreviven a la recarga** — **MEDIDO**: *el filtro viaja en la dirección (`?q=`) y recargar
   deja a la vista filtrada.* **Falta la selección** (*la tierra elegida, `id=`, y las marcadas*), que también
   está escrita en la dirección pero **no se ha comprobado recargando**.

***Nada de esto está hecho.*** *La tabla y la comprobación de que cada enlace abre lo suyo, sí.*
