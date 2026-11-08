titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital ha probado el GeoPackage REAL con un cliente de cuatro parcelas de Salamanca (4/4 contornos, WKT idéntico y mapas con ortofoto) y ha cerrado el fallo de la tierra apuntada solo con la referencia, que antes se quedaba sin dibujo. El cuaderno guiado avisa de lo que bloquea el envío y pone lo urgente primero, con la interfaz móvil auditada sin solapamientos. PSD2 queda documentado para que David decida: precios publicados y desconocidos, la licencia propia descartada por 50.000 € de capital y ninguna contratación.
estado: en-curso
tarea: cliente real pintado con el GeoPackage, alta por referencia arreglada, cuaderno con aviso de bloqueos, móvil auditado y PSD2 revisado para decidir
nivel: 2
siguiente: política de limpieza de la caché del GeoPackage; cola sin cobertura; PAC de años anteriores y pantallas propias de PAC y gastos
bloqueado: PSD2 (nivel 3, sin presupuesto y sin gasto aprobado); y siguen pendientes de terceros las licencias (CIT, IGN) y los formatos del expediente y del Cuecyl antiguo
fecha: 2026-11-08

## Lo que se ha hecho en esta ronda

1. **GeoPackage real con un cliente de verdad**: cuatro parcelas de Salamanca con referencias sacadas
   del fichero real (El Prado, El Alto, La Vega y **Las Eras**, esta última dada de alta **solo con la
   referencia**). `POST /api/sigpac/cache/37/contornos` → **4/4 actualizadas, 0 sin códigos**, geometría
   **idéntica** al WKT del lector, y **cuatro mapas** con ortofoto del IGN (0,6–1,3 s por mapa) en
   `docs/capturas-nuevo/cliente-contornos.png`; variante sin red con el contorno dibujado por el
   programa. El contorno de las cuatro se genera en **0,046 s**. **Y dentro de la app, en móvil**: el
   mapa real aplicado a una tierra se ve en su ficha con ortofoto y contorno
   (`cliente-real-ficha-390/360.png`) y en la ventana del SIGPAC con el recinto real
   (`cliente-real-sigpac-390.png`), con la imagen cargada comprobada. Y **las cuatro parcelas del
   cliente**, dadas de alta solo con su referencia, se ven una a una con su contorno y su ortofoto
   (`cliente-real-1..4-390.png`); el índice de capturas está en `docs/capturas-nuevo/LEEME.md`.
2. **Fallo cerrado (hallado por esa prueba)**: una tierra creada con **solo `ref_sigpac`** guardaba los
   códigos en blanco y el GeoPackage no la reconocía. Ahora:
   - al guardar, `_completar_los_codigos_con_la_referencia` rellena `codigo_ine`, polígono, parcela y
     recinto **solo si faltan** y no bloquea si la referencia no se entiende;
   - al leer, `codigos_de_una_parcela` usa la referencia **también para las tierras ya guardadas**, sin
     migración.
   Antes: `sin_codigos`; ahora: `actualizadas` y WKT idéntico. **7 pruebas nuevas** del alta por
   referencia y 3 del geopackage.
3. **Cuaderno guiado con avisos claros**: tarjeta «Hay K cosas que impiden presentar el cuaderno»
   (8 reales, singular/plural), botón **«Empezar por lo que bloquea»**, los bloqueantes **primero en
   cada sección** (orden estable) y «Faltan N y aquí se ven M» si el servidor cuenta más de las que
   lista. Medido en Chrome: 358/328 px, 0 desborde, botón 56 px y centro alcanzable.
4. **Móvil auditado y con capturas limpias**: 10 vistas a 390×844 y 360×640, **0 px de desborde, 0
   botones <44 px y 0 centros tapados** (cada control se lleva al centro y se comprueba con
   `elementFromPoint`); **20 capturas** de todas las vistas y **3 más** del contorno real dentro de la
   app en `docs/capturas-nuevo/` (`movil-*.png` y `cliente-real-*.png`), con Hoy, Tierras, ficha,
   apuntar, calendario, trabajos, productos, cuaderno, facturas y la ventana del SIGPAC. Al cambiar de
   pantalla el scroll vuelve arriba (antes una vista heredaba el scroll de la anterior y los primeros
   botones quedaban bajo la cabecera fija).
5. **PSD2 documentado para decidir, sin contratar nada** (`docs/PSD2-AGREGADORES.md`, revisión
   08/11/2026):
   - **Ningún agregador grande publica precio de producción** (Enable Banking, Powens, Tink,
     GoCardless, TrueLayer, Salt Edge: presupuesto).
   - **Lo único publicado**: sandbox de BBVA **0 €** y **openbanking.io 3 €/mes con 1 cuenta + 1 €/mes
     por cuenta** (2 cuentas = 48 €/año antes de IVA), pero **su licencia y cobertura española no están
     verificadas**: no se usa sin DPA y por escrito.
   - **Licencia propia (AISP) descartada**: **50.000 € de capital inicial** (art. 7 PSD2) más
     certificados eIDAS (2.000–10.000 €/año, estimación de tercero) y auditoría.
   - **Tres caminos**: seguir con el extracto por fichero (0 €), agregador AISP (presupuesto) o
     licencia propia (descartada). **Criterio de parada**: si el anual supera el coste de seguir a mano
     (0 €), no se contrata. **David decide**; no hay código de PSD2.
6. **Limpieza**: solo se levanta el uvicorn temporal de las verificaciones y se apaga; no queda ningún
   proceso de CueDigital escuchando.

## La última pasada, sobre este mismo HEAD

    Python       5930 recogidas · 5928 superadas, 2 omitidas, 0 fallos
    JavaScript   1309 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, móvil 390/360, ficha, apuntar (4 pestañas guardando),
    calendario, filtros, facturas, cuaderno con aviso, productos, ventana del SIGPAC con recintos
    tocables y contornos reales de Salamanca                                  0 fallos
    cliente real con el GeoPackage de Salamanca                       4/4 contornos, 4 mapas
    capturas móviles                       20 (390 y 360) + 4 del cliente en la app + 3 de ficha/SIGPAC + 2 del montaje

## Lo que sigue abierto

- **Política de limpieza de la caché** del GeoPackage (ZIP 600 MB + `.gpkg` 1.070 MB por provincia).
- **Cola sin cobertura** del apunte y **cosecha comercializada** en la app nueva.
- **PAC de años anteriores** y recintos por campaña de la Junta; pantallas propias de PAC y gastos.
- **PSD2**: esperar los presupuestos y la decisión de David; sin código hasta contrato.
- **Referencia del visor (6 números) sin recinto**: decidir si se elige el único trozo; hoy se declara
  `sin_codigos` con su motivo.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
