# Fuente oficial: municipios de Castilla y León

`diccionario2025.xlsx` es la **copia literal** del diccionario del INE
«Relación de municipios y sus códigos por comunidades autónomas y provincias»:

- Dirección: https://www.ine.es/daco/daco42/codmun/diccionario2025.xlsx
- Descargado el: 2026-09-24
- SHA-256: `5cf83d5b9c68b4c39650b2f38cd60d817a2c9f90acc618b603e8c17ebd12ad07`

De ahí sale `data/municipios_cyl.csv`, que es lo que lee la aplicación para poder
elegir el municipio **por su nombre** en vez de escribir códigos. El CSV se rehace
con `python scripts/bajar_municipios_ine.py` y se puede rehacer sin internet con
`--sin-descarga`, que usa esta copia.

El código de cinco cifras es el de siempre: **dos de provincia y tres de municipio**.
Son 2248 municipios en las nueve provincias de la comunidad.
