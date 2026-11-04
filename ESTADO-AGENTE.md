titulo: CueDigital — la herramienta del agricultor de Castilla y León
estado: en-curso
tarea: alcance nuevo — investigación, arquitectura de pantallas y primer paquete visual (para aprobar)
nivel: 2
siguiente: esperando la aprobación de David (AGR-1); después, armazón nuevo + Hoy + Mis parcelas
bloqueado: aprobación del aspecto y de la arquitectura (AGR-1, nivel 3); y el corpus de D08 (material de David)
fecha: 2026-11-04

## Lo que se ha hecho en esta sesion

1. **Alcance nuevo leído y asumido**: `ALCANCE-AGRICOLA.md` manda. El producto pasa a ser la
   herramienta del agricultor de Castilla y León (cuaderno, PAC y subvenciones, parcelas del SIGPAC),
   con interfaz nueva para PC, tableta y móvil. No se reescribe el backend.
2. **Investigación oficial** (`docs/INVESTIGACION-AGRICOLA.md`): cuatro líneas independientes —
   SIGPAC, PAC/subvenciones, cuaderno digital y competencia— con **URL y fecha en cada afirmación** y
   lo pendiente marcado. Seis hallazgos que cambian el plan, entre ellos: el SIGPAC se puede traer
   entero (GeoPackage por provincia, CC BY 4.0 con uso comercial); **la PAC no se presenta desde un
   fichero** (se cumplimenta y firma en la app de la Junta, sin API pública localizada); y el mínimo
   legal de un tratamiento son **11 datos**, de los que 8 no se pueden deducir.
3. **Arquitectura de pantallas** (`docs/ARQUITECTURA-DE-PANTALLAS.md`): navegación (5 destinos en
   móvil, barra lateral en PC), **11 pantallas P0** con contenido, acciones, los cuatro estados y de
   qué datos viven, los flujos (alta desde SIGPAC, apunte en 30 s, campaña, PAC) y las fases de
   entrega. **Para que David la apruebe antes de implementar.**
4. **Primer paquete visual**: sistema de diseño `designs/cue-agricola-design-system/` (paleta de día y
   noche con **contraste AA calculado y anotado**, tipografía del sistema para funcionar sin red,
   espaciado, radios y objetivos táctiles de 48 px) y canvas de artboards en `designs/cue-agricola/`
   (mis parcelas, Hoy, apuntar, ficha de parcela, PAC…) con datos de ejemplo ficticios.
5. **D08 no se persigue**: quedó decidido y el corpus pendiente de material de David (30 facturas con
   permiso). Anotado, sin tocarlo.

## La última pasada, sobre este mismo HEAD

    Python       5655 recogidas · 5653 superadas, 2 omitidas, 0 fallos
    JavaScript   1228 superadas, 0 fallos

## Lo que sigue abierto

- **AGR-1, esperando a David**: aprobar (o corregir) la arquitectura y el aspecto. Las preguntas
  exactas están en el apartado 9 de `docs/ARQUITECTURA-DE-PANTALLAS.md`.
- Sin esa aprobación **no se implementa** la interfaz; mientras, se pueden hacer AGR-3 (traer parcelas
  del SIGPAC en lote) y AGR-4 (correcciones documentales), que no dependen del aspecto.
- **Preguntas a la administración** (AGR-7): licencia del SHP de CyL (CIT), campañas históricas y
  cupos (FEGA), licencia PNOA (IGN) y especificación del `.xlsx` del Cuecyl (Junta/FEGA).
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
