
### El recuento de Python: por qué pasó de 4822 a 4824 (13/10/2026)

Lo explicó la revisión del dueño y conviene que quede escrito, porque el número cambió sin que nadie añadiera
pruebas a mano: **`backend/scripts/verificar_el_conflicto_de_una_nota.py` trae dos comprobaciones que pytest
recoge como casos** —la ausencia de BOM y los acentos—, así que la suite pasa de **4822 a 4824** casos recogidos.
Cuando se cuentan, hay que contarlas.

**Y una advertencia sobre cómo se comprueba, que costó un susto**: el guardián del total **se salta cuando se
ejecuta solo una parte de la suite**. Verlo en verde por separado **no** confirma el recuento. La comprobación
buena es la suite entera (o el guion `poner_al_dia_el_recuento_de_pruebas.py`, que la corre dos veces).
**Pendiente**: ese guion cuenta por su cuenta y escribe **4822** —no incluye las dos comprobaciones del guion—,
así que hoy deja los documentos en un número y el runner recoge otro y se queja de su propia salida. Hay que
enseñarle a contar como cuenta el runner.
