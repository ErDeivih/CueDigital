# La revisión con visión: la hoja para quien pueda mirarla

> **Para qué es este documento.** D05 pide una revisión **visual** de las capturas. ***Este modelo no ve imágenes***, así
> que el encargo manda dejarlo **EN_REVISION** hasta que lo mire alguien que sí pueda. Esto es **la hoja de revisión**:
> las capturas que hay, **qué hay que mirar en cada una**, y el resultado que da el revisor. **Convertir un bloqueo en
> una tarea de diez minutos es lo único útil que se puede hacer desde aquí.**

---

## 1 · Por qué está EN_REVISION, con la prueba

*El arnés tiene una herramienta para leer imágenes —`read_image`—, y **la probé** (22/10/2026):*

```
Error: cannot read "…/inicio-1440x900.png" as an image:
model "deepseek-v4-flash-vision-exp" does not declare image input;
switch to an image-capable model to read images
```

***No es una suposición: es lo que contesta el programa.*** *La revisión **no se ha hecho**, y **no se puede hacer aquí**.*

---

## 2 · Las capturas que hay

*En `docs/capturas-de-anchuras/`, **quince**: cinco anchuras por **tres pantallas**.*

| pantalla | anchuras |
|---|---|
| **inicio** | 320 · 390 · 712 · 1024 · 1440 |
| **tierras** | 320 · 390 · 712 · 1024 · 1440 |
| **cuaderno** | 320 · 390 · 712 · 1024 · 1440 |

*(Cada una: `<pantalla>-<ancho>x<alto>.png`.)*

---

## 3 · Qué hay que mirar en cada una

***Lo que ya está medido con instrumentos*** *—para que el revisor no repita trabajo—:*

| lo que dice el encargo | cómo se midió | resultado |
|---|---|---|
| **ningún texto por debajo de 15 px** | *`medir_el_contraste.py`, midiendo el tamaño real* | ✅ |
| **ningún control por debajo de 44×44** | *`medir_el_tacto_y_el_foco.py`, a 390* | ✅ *0 por debajo* |
| **contraste WCAG AA** | *`medir_el_contraste.py`* | ✅ *el peor, 6,3:1; ninguno por debajo de 4,5* |
| **sin desbordamiento horizontal al 200 %** | *`medir_el_zoom_y_lo_que_se_anuncia.py`* | ✅ |
| **el foco se ve con Tab** | *`medir_el_tacto_y_el_foco.py`* | ✅ *`BUTTON solid 3px rgb(13, 43, 24)`* |
| **el móvil con tarjetas, no tabla** | *`verificar_las_anchuras_de_las_tierras.py`* | ✅ *1440: 3 filas · 1024 y 390: 3 tarjetas* |

***Lo que solo se puede juzgar mirando*** —*y es lo que se pide al revisor—:*

### Para cada captura

1. **¿Se entiende qué pantalla es, sin leer el menú?** *¿el título y lo importante están claros y arriba?*
2. **¿La jerarquía es la del diseño?** *¿lo principal es lo más grande, y lo secundario se distingue sin competir?*
3. **¿Hay algo que se corte, se solape o se salga?** *texto partido, botones pisados, tarjetas que se montan.*
4. **¿Queda sitio vacío incómodo o apretado donde no debería?**
5. **¿Parece CueDigital?** *—la marca, la paleta, la tipografía— **o parece un formulario cualquiera**. La especificación
   de marca está en `docs/ESPEC_MARCA_UX_2026-10-19.md`.*
6. **En las de 320 y 390, además**: *¿se lee sin hacer zoom? ¿los botones se alcanzan con el pulgar? ¿el texto no queda
   diminuto aunque cumpla los 15 px?*
7. **Comparando las cinco anchuras de una misma pantalla**: *¿la misma pantalla, más estrecha, o **otra pantalla**?*

---

## 4 · El resultado, para rellenar

*Una tabla por pantalla. **El revisor escribe y firma**; esto es lo que falta para sacar D05 de EN_REVISION.*

| pantalla | 320 | 390 | 712 | 1024 | 1440 | quién | cuándo |
|---|---|---|---|---|---|---|---|
| **inicio** | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | | |
| **tierras** | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | | |
| **cuaderno** | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | | |

*⬜ sin revisar · ✅ conforme · ✍️ con anotación (se escribe debajo qué)*

### Anotaciones

*(Aquí van las que salgan, con la captura a la que se refieren.)*

---

## 5 · Y lo que **no** es esta hoja

***No es una revisión hecha.*** *Es la lista para hacerla. **D05 sigue EN_REVISION**, y seguirá hasta que alguien con
ojos —y con la marca en la cabeza— rellene la tabla de arriba.*

***Y no sustituye a las medidas***: *el contraste, el tacto y el zoom **ya están medidos**; la revisión añade lo que un
instrumento no ve: **si la pantalla se entiende**.*
