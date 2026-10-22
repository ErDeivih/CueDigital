# La revisión visual de D05, y su estado

> **Estado: EN_REVISION.** *Las capturas están hechas y las medidas sin vista, también. **La revisión con visión
> no se ha podido hacer**: el modelo de esta sesión **no acepta imágenes** — contesta «does not declare image
> input» —, y el encargo dice, con estas palabras: «si el modelo no ve imágenes, mantener **EN_REVISION** hasta que
> un revisor que sí las vea emita resultado».*

---

## 1 · Lo que sí está hecho

### Las capturas, de las cinco anchuras que pide el encargo

*Sacadas de la aplicación de verdad, con **una cuenta y unos datos temporales**: tres tierras con forma, para que las
pantallas no salgan vacías. En `docs/capturas-de-anchuras/`, tres pantallas por anchura —**inicio**, **tierras**
(`#/tierras/mapa`) y **cuaderno**—:*

    320x700 · 390x844 · 712x900 · 1024x768 · 1440x900

*El guion que las saca: `scripts/capturar_las_anchuras.py`.*

### Lo que se mide sin ver (`scripts/medir_el_tacto_y_el_foco.py`)

| medida | móvil (390) | ordenador (1440) |
|---|---|---|
| **controles táctiles** | **0 por debajo de 44×44** en inicio y tierras | *algunos de 40 px de alto — es un ratón, no un dedo* |
| **el foco se ve** | **sí**: `outline: 3px solid` con el **tabulador** | ídem |
| **lo que se pulsa, con el teclado** | *se llega tabulando* | ídem |

***Y un falso negativo, cazado y corregido***: *la primera versión de la comprobación del foco decía «no se ve»,
porque enfocaba **con código** (`.focus()`) y el CSS usa **`:focus-visible`** — que **no se activa así**. *Con el
**tabulador**, el contorno aparece: `BUTTON solid 3px rgb(13, 43, 24)`.* **La aplicación estaba bien; la medición
estaba mal.**

---

## 2 · Lo que NO está hecho, y no se puede dar por bueno

**La revisión con visión**: *contraste real de cada texto sobre su fondo, jerarquía, si algo «se ve bien» a 320 px,
si los estados de error y vacío se distinguen a simple vista.*

*No la he hecho. **No la puedo hacer** con este modelo.*

**Cómo cerrarla**: *abrir `docs/capturas-de-anchuras/` —quince imágenes— y revisarlas; o pasar un revisor con
visión sobre ellas. **Hasta entonces, D05 no está cerrado.**

---

## 3 · Y lo que el encargo pide además, que sigue pendiente

- **el zoom al 200 %**;
- **Escape y foco de regreso** (*que al cerrar algo el foco vuelva a donde estaba*);
- **lector de pantalla** (*que los `aria-live` y las etiquetas se anuncien como toca*);
- **contraste medido** (*no a ojo: con la relación calculada sobre los colores reales*);
- y **los cuatro recorridos completos** de D05: *tierra → trabajo → consumo; compra → recepción → lote → gasto →
  pago; venta → factura → cobro parcial → pendiente; papel → propuesta → confirmación/rectificación*, **cada total
  abriendo sus registros por ID**.

***Nada de eso está hecho.** Este documento dice lo que hay y lo que falta, sin redondear.*
