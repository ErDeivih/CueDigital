titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: David aprobó el diseño con ocho correcciones. Ya están aplicadas en la arquitectura y en los 10 artboards, y la investigación de la Junta se ha ampliado con la vía real para importar las tierras (la consulta de recintos por campaña 2023-2026 y el Cuecyl). Todavía no hay implementación de la aplicación: lo siguiente es el armazón nuevo con «Hoy» y «Mis tierras». El corpus de D08 sigue aparcado y no bloquea nada.
estado: en-curso
tarea: correcciones de David aplicadas al diseño y a la arquitectura; investigación de importación ampliada
nivel: 2
siguiente: AGR-2 (armazón nuevo + Hoy + Mis tierras), y después AGR-10, AGR-11 y AGR-12
bloqueado: nada duro; quedan pendientes de terceros las licencias (CIT, IGN), los formatos del expediente y del Cuecyl de años anteriores, y los dos vídeos de referencia de David
fecha: 2026-11-05

## Lo que se ha hecho en esta sesion

1. **Aprobación del diseño, con ocho correcciones** (2026-11-05). Están escritas en
   `ESPECIFICACION.md` y aplicadas en `docs/ARQUITECTURA-DE-PANTALLAS.md` (apartado 0) y en el canvas.
2. **Canvas actualizado: 10 artboards, `check` con 0 problemas.** «Mis tierras» ya no finge que todo
   cabe en una imagen: tierras **agrupadas por municipio** con su total, mapa **por zona**, zoom,
   «ver la tierra entera» y selección lista ↔ mapa ↔ panel, con los **otros años** de cada tierra.
   Nuevas: **alta de tierras** (importar una PAC o a mano), **PAC histórico** (años, evolución
   editable con producción kg/ha y variedad, traer una PAC), **factura de foto** (foto fija + revisión
   campo a campo), **productos y abonos con dosis por hectárea** y total, con **favoritos**. El
   cuaderno de apuntar dice **qué le falta para valer** y que se puede guardar y completar luego.
3. **Doctrina §8 aplicada**: fuera los textos de desarrollador («Ortofoto simulada, sin conexión», la
   sticky «Datos de ejemplo», explicaciones de cálculo y avisos internos). Barrido: 0 textos técnicos,
   0 jerga prohibida, 0 sombras/degradados, 0 emoji; tokens del sistema intactos.
4. **Investigación ampliada** (`docs/INVESTIGACION-AGRICOLA.md`, apartado 9 bis), con URL y fecha
   2026-11-05: la **consulta pública de recintos SIGPAC de la Junta por campaña 2023–2026** (descarga
   a texto/Excel, sin certificado, con uso, superficie, CSP, coeficiente de regadío y región) es la
   vía real para «se añaden solas»; el **Cuecyl `.xlsx`** de cada campaña se puede leer; **no hay
   fichero oficial de la solicitud PAC declarada** (la app la firma con certificado y reimporta el año
   anterior dentro de ella). También: webinars y demos oficiales de la Junta, el formulario **S-X**, y
   los riesgos probados (recintos renombrados/partidos, NIF del propietario, CSP provisional).
5. **D08 sigue aparcado** por decisión de David: no se persigue y no bloquea.

## La última pasada, sobre este mismo HEAD

    Python       5655 recogidas · 5653 superadas, 2 omitidas, 0 fallos
    JavaScript   1228 superadas, 0 fallos

## Lo que sigue abierto

- **AGR-2, lo siguiente**: armazón nuevo + «Hoy» + «Mis tierras», con los estados y a 390/1024/1440.
- **AGR-10/11/12**, ya con el diseño aprobado: histórico y evolución; productos/dosis/favoritos;
  facturas de foto con revisión campo a campo. Y **AGR-13**: la doctrina §8 en los textos nuevos.
- **Pendiente de terceros**: licencia del SHP de CyL (CIT) y de la ortofoto PNOA (IGN); formato de
  «Documentos del expediente» y descarga del Cuecyl de años anteriores; los **dos vídeos** de
  referencia de David sobre el registro de parcelas; valores de los catálogos oficiales.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
