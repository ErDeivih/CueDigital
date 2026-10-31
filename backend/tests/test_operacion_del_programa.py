"""El documento de operación no se queda atrás (D06).

`docs/OPERACION.md` dice cómo se arranca el programa, qué variables hay que poner en un
servidor expuesto, cómo se copia y se restaura la base, cómo se cierran las sesiones y qué
queda pendiente. Sirve justo el día que hay que hacerlo con prisa, así que no puede
contradecir al código: si un guion cambia de banderas, si se renombra `/health` o si alguien
borra una sección, estos tests se ponen rojos **antes** de que alguien lo lea en el servidor.

**Por qué se comprueba contra los ficheros y no contra una copia:** la copia se queda vieja
sin avisar. Aquí se lee el guion de verdad (`backend/scripts/`) y la aplicación de verdad
(`backend/app/main.py`). Es la misma regla que el resto de guardianes de documentación del
proyecto: si el test lee ficheros y los interpreta, se escribe sencillo (buscar textos
literales) para que no acabe siendo él el que miente.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DOC = RAIZ / "docs" / "OPERACION.md"
README = RAIZ / "README.md"
GUIONES = RAIZ / "backend" / "scripts"


def el_documento() -> str:
    assert DOC.is_file(), (
        "falta docs/OPERACION.md: es el documento que se lee para arrancar, copiar y "
        "restaurar en un servidor (D06), y lo cita backend/scripts/copiar_la_base.py"
    )
    return DOC.read_text(encoding="utf-8")


class TestElDocumentoDeOperacion:
    def test_existe_y_tiene_las_secciones_que_se_buscan(self):
        """Un documento al que le falta un apartado se lee como si estuviera completo."""
        texto = el_documento()
        assert len(texto) > 3000, (
            f"docs/OPERACION.md tiene {len(texto)} caracteres: no puede explicar el arranque, "
            "las variables, las copias, la restauración y lo pendiente"
        )
        for titulo in (
            "# Operar CUE Digital",
            "## 1. Arrancar el programa",
            "## 2. Variables de entorno",
            "## 3. Límites de intentos",
            "## 4. Sesiones: cuánto duran y cómo se cierran",
            "## 5. Copia de seguridad",
            "## 6. Restaurar y deshacer una migración",
            "## 7. Lo que este documento deja pendiente, dicho",
        ):
            assert titulo in texto, f"a docs/OPERACION.md le falta el apartado «{titulo}»"

    def test_el_readme_lleva_a_el(self):
        """Un documento que no está en la tabla de documentación no lo encuentra nadie."""
        texto = README.read_text(encoding="utf-8")
        assert "(docs/OPERACION.md)" in texto, (
            "docs/OPERACION.md no aparece en la tabla «Documentación» de README.md: "
            "quien busca cómo desplegar no lo va a encontrar"
        )

    def test_las_variables_del_secreto_estan_documentadas(self):
        """Sin el secreto, en producción el programa no arranca; tiene que estar dicho."""
        texto = el_documento()
        for variable in (
            "CUEDIGITAL_SECRETO",
            "CUEDIGITAL_SECRETO_ANTERIOR",
            "CUEDIGITAL_ENTORNO",
        ):
            assert variable in texto, (
                f"docs/OPERACION.md no habla de {variable}, que es lo que hace que el programa "
                "arranque o no en un servidor expuesto (backend/app/security.py)"
            )
        # Y lo que se dice sigue siendo verdad en el código: en producción y sin secreto,
        # se lanza en vez de arrancar con uno de mentira.
        security = (RAIZ / "backend" / "app" / "security.py").read_text(encoding="utf-8")
        assert "RuntimeError" in security and "CUEDIGITAL_SECRETO" in security

    def test_los_guiones_que_cita_existen(self):
        """Citar un guion que ya no está es peor que no citarlo: se busca y no aparece."""
        texto = el_documento()
        citados = set(re.findall(r"scripts/([a-z0-9_]+\.py)", texto))
        assert citados, "docs/OPERACION.md no cita ningún guion"
        for nombre in citados:
            assert (GUIONES / nombre).is_file(), (
                f"docs/OPERACION.md manda ejecutar scripts/{nombre}, que no existe"
            )
        # Los cuatro que el documento necesita para decir lo que dice.
        for nombre in (
            "copiar_la_base.py",
            "verificar_la_copia_y_la_restauracion.py",
            "deshacer_la_migracion.py",
            "cambiar_la_clave.py",
        ):
            assert nombre in citados, (
                f"docs/OPERACION.md no cita scripts/{nombre}, que es la única vía para eso"
            )

    def test_las_banderas_que_cita_existen_en_su_guion(self):
        """Una bandera que el documento enseña y el guion no acepta deja al operador a medias."""
        texto = el_documento()
        banderas = {
            "copiar_la_base.py": ("--origen", "--destino", "--comprobar"),
            "deshacer_la_migracion.py": ("--base", "--copia", "--mirar"),
            "cambiar_la_clave.py": ("--correo", "--clave", "--listar"),
        }
        for nombre, esperadas in banderas.items():
            guion = (GUIONES / nombre).read_text(encoding="utf-8")
            for bandera in esperadas:
                assert bandera in texto, (
                    f"docs/OPERACION.md no enseña {bandera} de scripts/{nombre}, que es como "
                    "se hace en la práctica"
                )
                assert f'"{bandera}"' in guion, (
                    f"docs/OPERACION.md manda usar {bandera} y scripts/{nombre} ya no la acepta"
                )

    def test_el_health_que_documenta_es_el_que_hay(self):
        """La comprobación de «está vivo» tiene que ser la dirección de verdad, con sus datos."""
        texto = el_documento()
        assert "GET /health" in texto, (
            "docs/OPERACION.md no dice cómo se comprueba que el servidor está vivo"
        )
        main = (RAIZ / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        assert '@app.get("/health"' in main, (
            "docs/OPERACION.md documenta /health y backend/app/main.py ya no lo sirve"
        )
        for dato in ('"estado"', '"zonas_vulnerables_cargadas"'):
            assert dato in texto and dato in main, (
                f"/health documentado y /health de main.py no coinciden en {dato}"
            )

    def test_lo_que_no_se_cifra_se_dice_en_los_dos_sitios(self):
        """El manifiesto de la copia lo declara en falso, y el documento lo tiene que decir."""
        texto = el_documento()
        assert '"cifrado": false' in texto, (
            "docs/OPERACION.md tiene que decir que la copia no va cifrada: es una decisión de "
            "despliegue y quien la lea no puede suponer que sí"
        )
        guion = (GUIONES / "copiar_la_base.py").read_text(encoding="utf-8")
        assert re.search(r'"cifrado"\s*:\s*False', guion), (
            "docs/OPERACION.md dice que el manifiesto lleva «cifrado: false» y "
            "scripts/copiar_la_base.py ya no lo escribe así"
        )
