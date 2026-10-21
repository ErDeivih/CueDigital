# CUE Digital: especificación de marca y experiencia

Fecha: 19/10/2026. Complementa `DESIGN.md`, no autoriza reconstruir el producto con otro framework.
Nombre de trabajo conservado: **CUE Digital**. La app ya existe y su lógica de negocio se reutiliza.

## Posicionamiento y carácter

**Promesa de producto:** «Tu tierra. Tus cuentas. Todo en su sitio.»
Debe demostrarse pudiendo pasar de una tierra a sus trabajos, de un trabajo a sus consumos
y de un importe a sus documentos, sin perder explotación ni campaña.

La personalidad es la de una herramienta de campo que sabe llevar un despacho: precisa, sobria,
cercana y franca sobre lo que desconoce. La diferenciación procede de decisiones agrarias útiles:
hectáreas únicas frente a hectáreas trabajadas; plan frente a hecho; dinero pendiente frente a dinero
sin asignar; dato medido frente a estimado; cuenta y finca visibles; original preservado y propuesta revisable.

No añadir tarjetas decorativas, contadores sin origen, gráficas vacías o fotografías de stock para
simular una aplicación de gestión. Tampoco adoptar nombres, iconos, layouts o textos de un competidor
como identidad propia. El estudio de referencias produce decisiones justificadas para una tarea.

## Firma visual aplicada y reglas de continuidad

- Símbolo vectorial en `backend/web/marca.svg`: una C abierta y líneas de cultivo. Geometría propia,
  trazos simples, sin texto de emoji ni dependencia de la tipografía del sistema.
- Firma «CUE Digital» en entrada y menú; nombre instalable, favicon y cabecera usan el mismo símbolo.
  Los textos viven en `textos.MARCA` y la pieza `Marca` solo los representa.
- Paleta existente: verde profundo, blanco de papel y amarillo de señal. No crear otra paleta por módulo.
  El amarillo no indica por sí solo buen/mal resultado. Reservarlo para selección, foco y atención.
- Tipografía del sistema, con las escalas de `DESIGN.md`: no descargar fuentes al abrir la app.
  Cifras tabulares en tablas y cifras con formato español. El sistema de texto sigue siendo legible al sol.
- Bordes y estructura, sin sombras, degradados ni animación ornamental. El escritorio puede ser denso
  sin convertir los controles en objetivos diminutos; mantener 40 px en escritorio y 44 px táctiles como mínimo.
- Marca y precisión no son la misma capa: nunca colocar un sello visual que parezca certificación legal.

Faltan las variantes monocroma/negativa y pruebas de reducción, favicon, iconos PNG 192/512 y máscara,
plantillas de PDF/cabecera/ayuda y guía de uso. Probar fondos, impresión y aplicación instalada.
No anunciar registro de marca antes de verificar OEPM/EUIPO, dominio y posibles conflictos.

## Arquitectura de información objetivo

Los módulos de despacho deben caber en grupos reconocibles. Propuesta para validar, conservando rutas antiguas:

| Grupo | Destinos principales | Acción recurrente |
|---|---|---|
| Finca | Inicio; Tierras y mapa; Campañas | Abrir una tierra |
| Campo | Trabajos; Cultivos; Almacén; Maquinaria | Apuntar lo realizado |
| Gestión | Compras y papeles; Ventas; Cuentas; Personas | Resolver un pendiente |
| Cuaderno | Cuaderno; Preparación PAC; Normativa | Revisar y exportar |
| Cuenta | Ajustes; Ayuda | Cambiar contexto con seguridad |

No crear un segundo menú paralelo. Primero inventariar `MODULOS_DEL_MENU`, las rutas y los enlaces que
ya existen. Tabla de compatibilidad y redirección para cada cambio. «Mis parcelas, productos y máquinas»
puede seguir como acceso antiguo durante la transición, pero no debe ser el concepto que organiza el producto.

En móvil, la acción de campo elegida debe verse antes del resumen. Se conservan los seis botones y su
orden actual hasta una decisión de producto respaldada por uso. El menú permite llegar a gestión cuando
se necesita, pero el agricultor no debe atravesar indicadores para registrar un trabajo.

## Contrato de cada pantalla

Cabecera: título breve, explotación y campaña efectivas, total o estado relevante y una acción principal.
Sección central: el contenido que resuelve la tarea. La ayuda larga se despliega en el lugar de la duda.
Pie o panel: origen, última actualización, vínculos y pendientes que explican los datos.

Una lista identifica cada registro, permite buscar/filtrar, distingue «ninguno» de «no se pudo cargar»
y ofrece abrir la ficha. Una ficha conserva identidad, relaciones, historial, autor/motivo y el camino
de vuelta. Una confirmación dice exactamente qué se guardó y en qué finca, y qué sigue pendiente.

Estados que todo corte debe diseñar y probar:

| Estado | Qué muestra | Qué permite |
|---|---|---|
| Cargando | Tarea que está esperando | Evitar envíos repetidos, conservar lo ya escrito |
| Primera vez | Qué se puede hacer y para qué | Crear el primer registro |
| Filtro sin resultados | Filtros efectivos y total | Quitar filtros |
| Fallo de consulta | Qué dato no llegó, sin convertirlo en cero | Reintentar sin perder contexto |
| Sin permiso | Alcance de acceso, sin filtrar los datos ocultos | Volver a una sección permitida |
| Sin cobertura | Qué está disponible localmente y su antigüedad | Registrar solo cuando pueda persistirse con dueño |
| Pendiente de envío | Cuántos son, fecha y estado de cada uno | Recuperar, corregir y resolver el rechazo |
| Conflicto | Registro actual y cambios propios | Elegir, recalcular o guardar una revisión |
| Desconocido | Qué falta y a quién corresponde comprobarlo | Completar o continuar con limitación explícita |

No usar un toast que desaparece para un rechazo, un conflicto o un documento importante.
Los errores de campo llevan foco y se relacionan con `aria-describedby`/`aria-invalid`.
Al cambiar pantalla el foco llega a un título útil; al cerrar un diálogo vuelve al control que lo abrió.

## Tierras y mapa: corte de diseño D04

Objetivo escritorio: en 1440×900 deben verse título, contexto, búsqueda, filtros activos y varias tierras
sin desplazar la página a través de todas las opciones posibles. Barra de filtros compacta con
«Más filtros»; grupos plegables; etiquetas removibles con recuento N de M.

Tabla y mapa comparten filtro y selección por ID. La selección no depende de la posición de la fila.
Si una tierra no tiene forma, aparece en la lista de pendientes, nunca como un polígono inventado.
Mostrar superficie de la tierra, oficial y trabajada con nombres diferentes. Abrir una ficha y volver
restaura búsqueda, orden, scroll y selección; recargar reproduce la misma vista.

En móvil: búsqueda y filtros activos primero, tarjetas breves con nombre, cultivo, ubicación y último
hecho; la acción que abre el mapa no obliga a recorrer una tabla de escritorio. Las opciones de filtro
no deben ocupar la primera pantalla completa. Probar 320, 390, 712, 1024 y 1440 px.

La ficha canónica tiene resumen, historia, cultivos, trabajo, documentos, costes autorizados y PAC.
No crear fichas diferentes para la misma tierra dependiendo del módulo desde el que se llega.

## Economía y documentos: cortes de diseño D04/D05

Cada número importante debe enlazar al conjunto que lo explica, con los mismos filtros y fecha de corte.
No mostrar como ingreso una previsión, como gasto una recepción, ni como deuda un saldo a favor.
El pendiente de una factura se explica por sus aplicaciones, no por una suma global de la explotación.

La ficha de compra ya tiene facturado, recibido, pagado y pendiente: se reutiliza como patrón.
Factura, albarán, lote, gasto y movimiento bancario conservan su diferencia y sus enlaces.
Escritorio: números alineados, cabeceras estables, orden por valores, acciones en una columna que no se
superponga a las cifras. Móvil: resumen y acción principal, después relaciones/historia.

Una lectura OCR enseña original y propuesta; lo desconocido sigue vacío. La revisión no inventa un
proveedor ni una categoría. Rectificar conserva ambos documentos y explica la relación.

## PAC y confianza

«Preparación PAC» es una ayuda para comparar y revisar, no una presentación ni una garantía.
La pantalla separa campaña de origen, campaña objetivo, hipótesis y hechos. La versión exportada
es exactamente la evaluación guardada y tiene identidad inequívoca, fecha, fuente y pendientes.
Si cambió la base desde la evaluación, se informa y se ofrece recalcular; no se sustituye en silencio.

No usar verde global de «cumple» cuando falta una regla aplicable o un dato. Prohibido sumar porcentajes
con denominadores distintos o excluir tierras sin cultivo para mejorar artificialmente el resultado.

## Cómo aceptar el diseño

Cada entrega incluye capturas **nuevas y vistas**, registro del contexto/datos ficticios, recorrido
con teclado, comprobación de contraste y zoom 200 %, foco, nombres accesibles, 0 desbordamientos de
página y controles táctiles válidos. Un contenedor de tabla con scroll horizontal puede ser deliberado;
una acción inaccesible fuera de la página no lo es.

Con tres agricultores autorizados, medir al menos: encontrar una tierra entre 64; planificar y registrar
sin confundirlos; corregir sin duplicar existencias; explicar un pendiente de factura; salir/volver sin
perder borrador; resolver un apunte sin cobertura; entender qué limita una evaluación PAC.
Anotar éxito, ayudas necesarias y errores graves. La satisfacción estética no sustituye esas tareas.

El revisor visual debe poder ver imágenes. Si DeepSeek no acepta imágenes, debe entregar capturas y
medidas a un revisor con visión y mantener el ticket en revisión hasta recibir el resultado.
