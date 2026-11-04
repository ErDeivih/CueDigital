# Alcance nuevo — CueDigital para el agricultor

Escrito el 2026-11-04 por indicación de David. **Manda sobre el alcance anterior en lo que respecta a interfaz y a datos de la Junta de Castilla y León.**

## Qué es

La herramienta digital del agricultor de Castilla y León: **cuaderno de campo digital, PAC y subvenciones**, con las parcelas del SIGPAC dentro, y con una interfaz que se pueda usar de verdad en el campo (móvil), en la oficina (PC) y en el tablet.

David lo dijo así: **lo que había no le gustaba nada**. Se rehace la interfaz, las páginas y las funcionalidades.

## 1. Interfaz

- **PC, tablet y móvil** de verdad, no una web que se encoge.
- Ideas tomadas de **CRM** (ficha, listas, filtros, estados, actividad) y de **apps de campo** (mapa, GPS, foto, funcionamiento sin cobertura).
- Antes de la primera pantalla: **sistema de diseño** (`claude-design-system`) y **artboards** (`claude-design`) para revisar el aspecto con David.
- Los cuatro estados por pantalla: vacío, cargando, error y sin permiso.
- Todo lo que se pueda rellenar en el campo se rellena **con el pulgar**: botones grandes, formularios cortos, mapas.

## 2. Integración con la Junta de Castilla y León

Hay que **investigar cada una con su fuente oficial** antes de implementar:

| Pieza | Qué hace falta saber |
|---|---|
| **SIGPAC** | descarga de recintos/parcelas, formato (SHP/GeoJSON/KML), identificación de recinto, uso y coeficiente |
| **PAC** | modelo de solicitud, superficies, cultivos, regiones, requisitos y ficheros que acepta la administración |
| **Subvenciones** | convocatorias, plazos, documentación, justificación |
| **Cuaderno digital** | el formato y los datos que exige la normativa (tratamientos, siembras, labores, fertilización, fitosanitarios) |
| **Tipos de producto, siembras y trabajos** | catálogos oficiales cuando existan; si no, catálogo propio y lo más cercano posible |

**Regla**: cada integración con la Junta se documenta con la **URL oficial, la fecha de consulta y qué está verificado**. Lo que no se haya podido comprobar se marca como **pendiente**, no se inventa.

## 3. El flujo del agricultor

- **Mis parcelas**: vienen del SIGPAC, con su mapa y sus recintos.
- **Cuaderno de campo**: apuntar una labor, un tratamiento o una siembra **en 30 segundos**, con foto si hace falta.
- **Campaña**: qué se ha hecho en cada parcela, en orden.
- **PAC y subvenciones**: preparar lo que pide la administración y tenerlo listo para presentar.
- **Exportar**: el agricultor tiene que poder sacar lo que le pidan (PDF, Excel, el formato que sea).

## 4. Cómo se trabaja

- **Investigación primero**: qué exige la JCYL, qué permiten sus APIs, cómo lo resuelven los que ya están en el mercado (y qué les falta).
- Rehacer la interfaz **no es reescribir el backend**: se conserva lo que sirva (firma, contratos, datos).
- Usar los plugins y skills instalados: `claude-design-system`, `claude-design`, `claude-dashboard`, `claude-slides` para presentar, `data_profile`/`data_clean`/`data_verify` para los datos.

## 5. Orden de valor

1. **Parcelas SIGPAC** (sin eso no hay nada).
2. **Cuaderno de campo** usable en el móvil.
3. **Campaña** y vista por parcela.
4. **PAC/subvenciones**: preparar la solicitud.
5. **Exportación** en los formatos que pide la administración.

## Reglas

- Sin GitHub Actions. Push selectivo.
- No tocar `.env` ni las fixtures de firma.
- Autorización en el servidor con matriz de roles escrita.
- Nada de datos personales de terceros en el repositorio.
- Toda afirmación sobre normativa o formatos lleva fuente y fecha. Si no está verificado, se dice.
