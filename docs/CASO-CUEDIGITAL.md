# Caso CUE Digital — cuaderno de campo y gestión de la explotación

> **Qué es este documento.** Un informe corto del proyecto: el problema que resuelve, cómo usa los
> datos oficiales del SIGPAC, cómo está organizado el modelo de datos y qué demuestra. Los números
> están medidos en el repositorio el 10/11/2026; lo que no está hecho se dice en el último apartado.

---

## 1. El problema

Un agricultor de Castilla y León lleva su cuaderno de campo entre papel, la hoja de cálculo y la
memoria. Cuando llega una inspección o hay que cuadrar la PAC, tiene que reconstruir **qué hizo,
dónde y cuándo**, y la información está repartida en papeles que no se hablan entre sí. Además, la
Administración ya pide el cuaderno en formato electrónico y lo va a exigir del todo: el registro de
tratamientos pasa a ser obligatorio en 2027.

La escena para la que se diseña no es una oficina: es **un agricultor de 50 a 70 años, de pie en una
parcela, con el móvil en una mano, el sol de frente y sin cobertura**. Todo se juzga contra esa
escena.

**CUE Digital** reúne el cuaderno de campo y la gestión de la explotación en una sola aplicación:
tierras, trabajos, tratamientos, abonos, gastos, maquinaria y contactos, con la pantalla pensada
para el campo y el cuaderno pensado para la inspección.

## 2. El SIGPAC: de dónde salen los datos de las tierras

El SIGPAC (Sistema de Información Geográfica de Parcelas Agrícolas) es el registro oficial de los
recintos. CUE Digital lo consulta **directamente**, sin copias intermedias:

- **Las tierras se dan de alta con su referencia** (los seis números del papel o los siete con el
  recinto). El programa llama al servicio del FEGA, trae la superficie, el uso, la pendiente, el
  coeficiente de regadío y **la forma del recinto**.
- **La forma se guarda como geometría**: el anillo del recinto se pide al servicio de contornos y se
  guarda como texto WKT. Eso permite dibujar la parcela, calcular su centro y pintarla en el mapa sin
  depender de ninguna imagen.
- **Los mapas** (ortofoto del vuelo y linderos) los sirve el propio programa, no el navegador: así no
  se manda al SIGPAC la petición de cada agricultor ni se depende de que el servicio esté disponible
  desde el móvil.
- **El catálogo de productos** (933 fitosanitarios oficiales) y las listas de usos y provincias se
  usan tal y como los publica el FEGA.

**Lo que el programa no hace, y es lo que más importa:** no inventa un dato del SIGPAC. Si el
servicio no contesta o el recinto no aparece, la tierra se queda sin forma o sin superficie y la
pantalla lo dice («sin el dibujo del mapa», «no consta»), en vez de rellenarlo con algo parecido. Un
dato inventado en un cuaderno oficial no da error al apuntarlo: da error meses después, delante de un
inspector.

## 3. El modelo de datos

**66 tablas** en PostgreSQL 16 (SQLite en local), organizadas por lo que representan. Todas las
tablas de negocio llevan **`explotacion_id`**: es lo que impide que un agricultor vea los datos de
otro, y toda consulta pasa por `obtener_de_la_explotacion()`.

| Grupo | Tablas y qué guardan |
|---|---|
| **La finca y quién entra** | `explotaciones`, `usuarios`, `accesos_a_fincas` (titular y ayudantes, con su papel), `campanas` |
| **Las tierras** | `parcelas` (referencia, municipio, superficie, uso, geometría WKT, centro), `parcela_cultivos` (qué se sembró cada campaña), `grupos_parcelas` |
| **El cuaderno** | `tratamientos` (producto, dosis, plazos de seguridad y reentrada **copiados de la etiqueta el día de la aplicación**), `registros_fertilizacion`, `labores`, `trabajos_previstos` |
| **Lo que rodea al cuaderno** | `productos_fitosanitarios`, `fertilizantes`, `analiticas`, `planes_abonado`, `medidas_preventivas`, `instalaciones` |
| **La explotación** | `maquinas` y sus obligaciones, inspecciones, averías y contadores; `aplicadores`, `asesores`, `equipos_aplicacion` |
| **El dinero** | `ventas_de_cosecha`, `facturas_emitidas`, `cobros`, `cuentas_bancarias`, conciliación de extractos |
| **La confianza** | `auditoria` (quién cambió qué y cuándo), y los apuntes se **anulan con motivo**, no se borran |

Dos decisiones que se notan en el modelo:

1. **La etiqueta se copia al apunte.** Si mañana cambia la ficha de un producto, el apunte histórico
   no puede cambiar con ella: el cuaderno tiene que decir lo que decía la etiqueta ese día.
2. **Lo que no se sabe es `None`, no `0`.** Una superficie desconocida no es cero hectáreas; una zona
   de nitratos sin listado no es «no». La diferencia es la que hace que un dato sea verdad o mentira.

**368 rutas de API** sirven ese modelo: desde el alta de una tierra y el apunte de un tratamiento
hasta el volcado oficial a la Junta, la firma del cuaderno y la lectura del cuaderno digital de la
Junta (Cuecyl) por las **etiquetas** de sus hojas, no por coordenadas fijas.

## 4. Qué demuestra

| Competencia | Evidencia |
|---|---|
| **Producto, no maqueta** | 27 pantallas en React sin compilar, 368 rutas y 66 tablas; se usa con el móvil en la mano. |
| **Datos oficiales** | Alta de tierras por referencia del SIGPAC, con su forma y su superficie; catálogo de 933 productos; cuaderno de la Junta leído y volcado oficial preparado. |
| **Geodatos** | La forma se guarda en WKT, se dibuja sin depender de imágenes de terceros, y el mapa se pide al SIGPAC por recinto y por punto. |
| **Calidad medida** | **6.161 pruebas de Python y 1.322 de JavaScript** en verde, con guardianes que impiden que los números de la documentación se queden viejos. |
| **Interfaz de campo** | Medido con Chrome a 360, 390, 768 y 1024 px: **0 desbordes, 0 controles por debajo de 44 px**, tablas y modales que caben. |
| **Cuaderno guiado** | La ficha de cada tierra dice **qué toca hacer y a partir de cuándo** («podrás cosechar a partir del 22/11»), con aviso cuando el plazo está a punto de terminar. Sale de los plazos apuntados, no de una suposición. |
| **Seguridad** | La app con datos reales **no es pública**: se entra solo por la red privada de Tailscale. Lo que se enseña es una **demo estática con datos ficticios**, con CSP, `referrer` y sin alta de cuentas. |
| **Despliegue** | Imagen Docker (usuario sin privilegios, HEALTHCHECK), PostgreSQL, Caddy y Tailscale, con la demo estática aparte en GitHub Pages. |

**Números, 10/11/2026:** 66 tablas · 368 rutas · 27 pantallas · 6.161 pruebas de Python · 1.322 de
JavaScript · 5 tierras de ejemplo con su forma real en el entorno privado · 5 tierras **inventadas**
en la demo pública.

## 5. Lo que no está hecho (dicho sin adornos)

- **El volcado oficial a la Junta** está implementado y probado contra el anexo del FEGA, pero **no se
  ha enviado nada real**: depende de que la Junta dé de alta el acceso.
- **El registro de la explotación no está completo**: faltan catálogos que la Administración no
  publica y el código de la DGC.
- **PSD2** (conciliación bancaria automática) está parado por presupuesto.
- **La app no tiene direcciones por pantalla**: no se puede compartir un enlace a una tierra ni volver
  a la misma pantalla al recargar.
- Los **textos de la interfaz** tienen una lista de mejoras pendiente (barra de acciones fija al
  apuntar, cabecera de grupo que diga qué no consta, ayuda de los códigos del SIGPAC).

## 6. Dónde mirar

- **Demo pública (datos ficticios):** <https://erdeivih.github.io/cuedigital-demo/>
- **Seguridad y qué se expone:** [`SEGURIDAD.md`](SEGURIDAD.md)
- **Despliegue:** [`DESPLIEGUE.md`](DESPLIEGUE.md)
- **Servicios del SIGPAC que se usan:** [`SERVICIOS_DEL_SIGPAC.md`](SERVICIOS_DEL_SIGPAC.md)
- **Lo que pide la Junta y falta:** [`LO_QUE_PIDE_LA_JUNTA.md`](LO_QUE_PIDE_LA_JUNTA.md)
- **Ficha de portfolio:** [`PORTFOLIO.md`](../PORTFOLIO.md)
