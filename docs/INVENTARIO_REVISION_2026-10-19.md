# Inventario técnico de la revisión del 19/10/2026

Base revisada: `dc0e4a5`. Inventario estático; no equivale a haber verificado cada comportamiento.

| Módulo Python | Líneas | Funciones | Rutas HTTP declaradas |
|---|---:|---:|---:|
| `backend/app/__init__.py` | 1 | 0 | 0 |
| `backend/app/accesos.py` | 231 | 12 | 0 |
| `backend/app/adjuntos.py` | 205 | 7 | 0 |
| `backend/app/bandeja.py` | 777 | 40 | 0 |
| `backend/app/borradores.py` | 643 | 15 | 0 |
| `backend/app/cades.py` | 976 | 28 | 0 |
| `backend/app/catalogos.py` | 1174 | 28 | 0 |
| `backend/app/catalogos_siex.py` | 161 | 9 | 0 |
| `backend/app/certificados.py` | 340 | 14 | 0 |
| `backend/app/contactos.py` | 632 | 20 | 0 |
| `backend/app/correcciones.py` | 369 | 15 | 0 |
| `backend/app/cuaderno_cyl.py` | 816 | 34 | 0 |
| `backend/app/cuaderno_cyl_exportar.py` | 1484 | 30 | 0 |
| `backend/app/database.py` | 1288 | 32 | 0 |
| `backend/app/deps.py` | 122 | 5 | 0 |
| `backend/app/dinero.py` | 429 | 15 | 0 |
| `backend/app/el_formulario.py` | 139 | 4 | 0 |
| `backend/app/estados_de_la_pantalla.py` | 189 | 5 | 0 |
| `backend/app/existencias.py` | 932 | 27 | 0 |
| `backend/app/extractos.py` | 2394 | 65 | 0 |
| `backend/app/facturas.py` | 800 | 28 | 0 |
| `backend/app/firma.py` | 397 | 13 | 0 |
| `backend/app/gastos.py` | 1645 | 44 | 0 |
| `backend/app/geo.py` | 405 | 18 | 0 |
| `backend/app/iuws.py` | 886 | 26 | 0 |
| `backend/app/iuws_cliente.py` | 535 | 16 | 0 |
| `backend/app/iuws_contenido.py` | 749 | 9 | 0 |
| `backend/app/iuws_descriptor.py` | 270 | 14 | 0 |
| `backend/app/iuws_mapeo.py` | 1649 | 23 | 0 |
| `backend/app/la_tabla.py` | 144 | 5 | 0 |
| `backend/app/lectura_evaluada.py` | 179 | 8 | 0 |
| `backend/app/legal.py` | 316 | 24 | 0 |
| `backend/app/lo_que_se_ve.py` | 136 | 7 | 0 |
| `backend/app/main.py` | 282 | 4 | 2 |
| `backend/app/maquinaria.py` | 914 | 18 | 0 |
| `backend/app/models.py` | 4542 | 2 | 0 |
| `backend/app/nitratos_cyl.py` | 60 | 5 | 0 |
| `backend/app/normativa.py` | 152 | 0 | 0 |
| `backend/app/nutrientes.py` | 229 | 5 | 0 |
| `backend/app/ocr.py` | 320 | 12 | 0 |
| `backend/app/pac.py` | 320 | 8 | 0 |
| `backend/app/paneles.py` | 237 | 6 | 0 |
| `backend/app/preferencias.py` | 115 | 5 | 0 |
| `backend/app/reenvios.py` | 123 | 4 | 0 |
| `backend/app/registro_oficial_de_productos.py` | 259 | 11 | 0 |
| `backend/app/reservas.py` | 208 | 7 | 0 |
| `backend/app/routers/__init__.py` | 1 | 0 | 0 |
| `backend/app/routers/almacen_api.py` | 1605 | 29 | 15 |
| `backend/app/routers/analiticas_api.py` | 556 | 17 | 11 |
| `backend/app/routers/bandeja_api.py` | 1390 | 46 | 13 |
| `backend/app/routers/borradores_api.py` | 109 | 3 | 1 |
| `backend/app/routers/buscar_api.py` | 276 | 2 | 1 |
| `backend/app/routers/compras_api.py` | 439 | 6 | 1 |
| `backend/app/routers/contactos_api.py` | 1977 | 51 | 21 |
| `backend/app/routers/cuaderno.py` | 1400 | 38 | 6 |
| `backend/app/routers/cuaderno_cyl_api.py` | 577 | 15 | 6 |
| `backend/app/routers/cuenta.py` | 295 | 9 | 6 |
| `backend/app/routers/documentos_api.py` | 497 | 11 | 8 |
| `backend/app/routers/explotacion.py` | 520 | 15 | 8 |
| `backend/app/routers/extractos_api.py` | 2013 | 44 | 16 |
| `backend/app/routers/facturas_api.py` | 1513 | 38 | 11 |
| `backend/app/routers/fincas_api.py` | 244 | 8 | 5 |
| `backend/app/routers/firmas_api.py` | 481 | 18 | 5 |
| `backend/app/routers/fusion_api.py` | 464 | 7 | 3 |
| `backend/app/routers/gastos_api.py` | 2571 | 57 | 25 |
| `backend/app/routers/interfaz.py` | 449 | 1 | 1 |
| `backend/app/routers/iuws_api.py` | 356 | 9 | 8 |
| `backend/app/routers/maestros.py` | 1372 | 40 | 30 |
| `backend/app/routers/mapa.py` | 310 | 4 | 3 |
| `backend/app/routers/maquinaria_api.py` | 2202 | 64 | 24 |
| `backend/app/routers/medidas_api.py` | 226 | 7 | 5 |
| `backend/app/routers/normativa_api.py` | 61 | 1 | 1 |
| `backend/app/routers/pac_api.py` | 359 | 10 | 5 |
| `backend/app/routers/panel_api.py` | 281 | 4 | 1 |
| `backend/app/routers/parcelas.py` | 1766 | 41 | 23 |
| `backend/app/routers/planes_api.py` | 330 | 16 | 7 |
| `backend/app/routers/registros.py` | 931 | 37 | 22 |
| `backend/app/routers/semillas_api.py` | 1251 | 29 | 12 |
| `backend/app/routers/tareas_api.py` | 223 | 6 | 4 |
| `backend/app/routers/terceros_api.py` | 370 | 9 | 6 |
| `backend/app/routers/trabajos_api.py` | 1551 | 35 | 14 |
| `backend/app/routers/ventas_api.py` | 2499 | 53 | 22 |
| `backend/app/routers/versiones_api.py` | 178 | 7 | 5 |
| `backend/app/saldos.py` | 307 | 7 | 0 |
| `backend/app/schemas.py` | 4439 | 14 | 0 |
| `backend/app/security.py` | 146 | 9 | 0 |
| `backend/app/semillas.py` | 740 | 23 | 0 |
| `backend/app/servicios.py` | 2883 | 71 | 0 |
| `backend/app/servicios_a_terceros.py` | 233 | 9 | 0 |
| `backend/app/sigpac.py` | 1114 | 46 | 0 |
| `backend/app/superficies.py` | 227 | 11 | 0 |
| `backend/app/textos.py` | 9444 | 8 | 0 |
| `backend/app/trabajos.py` | 1516 | 38 | 0 |
| `backend/app/validaciones.py` | 1155 | 21 | 0 |
| `backend/app/ventas.py` | 342 | 8 | 0 |
| `backend/app/versiones_de_recinto.py` | 1378 | 39 | 0 |

Totales: 96 módulos, 84741 líneas Python, 1818 funciones y 357 declaraciones de rutas.

| Frontend propio | Líneas |
|---|---:|
| `backend/web/app.js` | 24686 |
| `backend/web/estilos.css` | 2868 |
| `backend/web/index.html` | 62 |
| `backend/web/manifest.webmanifest` | 19 |
| `backend/web/nucleo.js` | 651 |
| `backend/web/react/acciones.js` | 157 |
| `backend/web/react/componentes.js` | 476 |
| `backend/web/react/montar.js` | 150 |
| `backend/web/react/pantallas/analiticas.js` | 188 |
| `backend/web/react/pantallas/asistente.js` | 144 |
| `backend/web/react/pantallas/ayuda.js` | 210 |
| `backend/web/react/pantallas/bancos.js` | 1156 |
| `backend/web/react/pantallas/bandeja.js` | 1097 |
| `backend/web/react/pantallas/borrador.js` | 126 |
| `backend/web/react/pantallas/buscar.js` | 105 |
| `backend/web/react/pantallas/campanas.js` | 140 |
| `backend/web/react/pantallas/cesta.js` | 175 |
| `backend/web/react/pantallas/cobro_nuevo.js` | 165 |
| `backend/web/react/pantallas/cobros.js` | 216 |
| `backend/web/react/pantallas/compra.js` | 249 |
| `backend/web/react/pantallas/contactos.js` | 957 |
| `backend/web/react/pantallas/cuaderno_de_la_junta.js` | 182 |
| `backend/web/react/pantallas/cultivos.js` | 193 |
| `backend/web/react/pantallas/decir_cultivo.js` | 208 |
| `backend/web/react/pantallas/dictado.js` | 96 |
| `backend/web/react/pantallas/documentos.js` | 163 |
| `backend/web/react/pantallas/enganchar_la_factura.js` | 191 |
| `backend/web/react/pantallas/entrar.js` | 186 |
| `backend/web/react/pantallas/factura_emitida.js` | 183 |
| `backend/web/react/pantallas/facturar_entregas.js` | 149 |
| `backend/web/react/pantallas/facturas.js` | 196 |
| `backend/web/react/pantallas/facturas_emitidas.js` | 114 |
| `backend/web/react/pantallas/firmar.js` | 114 |
| `backend/web/react/pantallas/fusion.js` | 196 |
| `backend/web/react/pantallas/gastos.js` | 866 |
| `backend/web/react/pantallas/grupos.js` | 125 |
| `backend/web/react/pantallas/hecho.js` | 218 |
| `backend/web/react/pantallas/inicio.js` | 332 |
| `backend/web/react/pantallas/interpretacion_factura.js` | 230 |
| `backend/web/react/pantallas/libro_del_almacen.js` | 372 |
| `backend/web/react/pantallas/mapa.js` | 184 |
| `backend/web/react/pantallas/maquinaria.js` | 976 |
| `backend/web/react/pantallas/medidas.js` | 146 |
| `backend/web/react/pantallas/mi_cuaderno.js` | 444 |
| `backend/web/react/pantallas/mis_cosas.js` | 217 |
| `backend/web/react/pantallas/mis_datos.js` | 165 |
| `backend/web/react/pantallas/movimiento_de_almacen.js` | 159 |
| `backend/web/react/pantallas/normativa.js` | 58 |
| `backend/web/react/pantallas/nueva_factura.js` | 78 |
| `backend/web/react/pantallas/nuevo_albaran.js` | 258 |
| `backend/web/react/pantallas/nuevo_documento.js` | 210 |
| `backend/web/react/pantallas/pac.js` | 97 |
| `backend/web/react/pantallas/planes.js` | 155 |
| `backend/web/react/pantallas/quien_entra.js` | 220 |
| `backend/web/react/pantallas/recepcion.js` | 195 |
| `backend/web/react/pantallas/revision_de_contactos.js` | 243 |
| `backend/web/react/pantallas/sacar_de_un_lote.js` | 241 |
| `backend/web/react/pantallas/semillas.js` | 446 |
| `backend/web/react/pantallas/siembras.js` | 397 |
| `backend/web/react/pantallas/tareas.js` | 157 |
| `backend/web/react/pantallas/tierra_versiones.js` | 343 |
| `backend/web/react/pantallas/tierras_mapa.js` | 775 |
| `backend/web/react/pantallas/trabajos.js` | 1005 |
| `backend/web/react/pantallas/trabajos_a_terceros.js` | 184 |
| `backend/web/react/pantallas/traer_del_sigpac.js` | 222 |
| `backend/web/react/pantallas/venta_ajuste.js` | 203 |
| `backend/web/react/pantallas/venta_importe.js` | 126 |
| `backend/web/react/pantallas/ventas.js` | 234 |
| `backend/web/react/piezas/acciones_de_una_ficha.js` | 66 |
| `backend/web/react/piezas/ayuda_de_un_campo.js` | 51 |
| `backend/web/react/piezas/campo.js` | 169 |
| `backend/web/react/piezas/campo_de_un_importe.js` | 85 |
| `backend/web/react/piezas/campos_del_maestro.js` | 122 |
| `backend/web/react/piezas/confirmacion.js` | 163 |
| `backend/web/react/piezas/lista_para_elegir.js` | 153 |
| `backend/web/react/piezas/marco.js` | 360 |
| `backend/web/react/piezas/panel_de_mando.js` | 251 |
| `backend/web/react/piezas/resumen_del_apunte.js` | 82 |
| `backend/web/react/piezas/tabla.js` | 240 |
| `backend/web/react/piezas/tarjeta.js` | 167 |
| `backend/web/react/rutas.js` | 568 |
| `backend/web/service-worker.js` | 472 |
