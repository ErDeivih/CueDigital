# Datos de los tests

Aquí van los ficheros que necesitan los tests para trabajar. **Ninguno lleva datos de una persona
de verdad.**

## `cuaderno_cyl_de_ejemplo.xlsx`

Un cuaderno de explotación de Castilla y León (el del **Cuecyl**, la aplicación de la Junta), con
las mismas 25 hojas, las mismas etiquetas y las mismas columnas que el cuaderno oficial, pero con
**una explotación que no existe**: «EXPLOTACIÓN DE EJEMPLO», NIF `12345678Z` (el que se usa en los
ejemplos), provincia y municipio `99` (que no son de ningún sitio) y superficies redondas.

Trae a propósito los casos difíciles, que son los que hay que probar:

| Qué trae | Para qué |
|---|---|
| Una tierra partida en **tres líneas** (barbecho 4,44 ha y dos trozos de avena, 0,46 y 0,13 ha) | Es lo que hace el cuaderno de verdad con un recinto que dentro tiene cultivos distintos |
| Una línea con la casilla de **zona nitratos** en «Sí», otra en «No» y el resto **en blanco** | En blanco es «no lo han declarado», **no** «no está»: es la diferencia entre un dato y un dato inventado |
| Una línea **sin recinto** | No se puede identificar la tierra: tiene que decirse cuál es y no darla de alta |
| `VEZA VELLOSA.VILLANA` | El cuaderno escribe especie y variedad en una casilla, separadas por un punto |
| Una línea **sin secano ni regadío** | Se cuenta y se avisa, en vez de suponer |
| Una nota al pie debajo de la tabla | El lector tiene que parar ahí, no inventarse una parcela con el texto de la nota |
| Las demás 23 hojas **vacías** | En un cuaderno recién descargado también lo están |

Se fabrica con `backend/scripts/hacer_cuaderno_de_ejemplo.py`, que está documentado y se puede
volver a lanzar:

```bash
cd backend
../.venv/Scripts/python.exe scripts/hacer_cuaderno_de_ejemplo.py
```

## Por qué no están aquí los cuadernos de verdad

Los cuadernos reales de un agricultor llevan su nombre, su NIF, su teléfono, su correo y la
situación exacta de sus tierras. Eso es suyo, no del repositorio. El lector
(`backend/app/cuaderno_cyl.py`) se escribió y se comprobó **contra los tres cuadernos oficiales de
verdad** (campañas 2024, 2025 y 2026, 25 hojas cada uno) antes de fabricar este ejemplo, y este
ejemplo reproduce la estructura que se encontró allí.
