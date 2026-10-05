"""Cambiar la clave desde el ordenador: que sirva de verdad y que no toque nada más.

Este guion es la respuesta a «me he olvidado de la clave» en un programa **que no manda correos**
(es un programa que vive en el ordenador del agricultor). Si esto no funcionara, se quedaría fuera de
su propio cuaderno, así que se prueba con cuidado:

1. Que **cambia la clave** de la cuenta que se le dice (y que la vieja deja de valer).
2. Que **no toca ninguna otra cuenta**.
3. Que **no cambia nada** cuando algo está mal: una clave corta, un correo que no existe o dos claves
   que no coinciden. Y que lo dice.
4. Que al listar **no enseña la clave ni su huella**.

Ninguno de estos tests toca la base de datos de verdad: cada uno se hace la suya en una carpeta
temporal.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import select

from app import database, models, security
from scripts import cambiar_la_clave


@pytest.fixture
def base_de_prueba(monkeypatch, tmp_path):
    """Una base de datos vacía y aislada, con dos cuentas dentro."""
    fichero = tmp_path / "cuenta.db"
    monkeypatch.setenv("CUEDIGITAL_DATABASE_URL", f"sqlite:///{fichero.as_posix()}")
    monkeypatch.setenv("CUEDIGITAL_ENTORNO", "pruebas")
    monkeypatch.setenv("CUEDIGITAL_ITERACIONES_PBKDF2", "1000")

    motor = database.crear_engine()
    models.Base.metadata.create_all(motor)
    with database.SessionLocal(bind=motor) as sesion:
        # Un usuario siempre cuelga de una explotación (`explotacion_id` no puede estar vacío), así
        # que la finca se crea primero.
        finca = models.Explotacion(nombre="La finca de prueba", nif="70922320A")
        sesion.add(finca)
        sesion.flush()
        for correo, nombre in (("david@ejemplo.test", "David"), ("otro@ejemplo.test", "Otro")):
            sesion.add(
                models.Usuario(
                    correo=correo,
                    nombre=nombre,
                    clave_hash=security.hash_clave("la-de-siempre"),
                    explotacion_id=finca.id,
                )
            )
        sesion.commit()
    return motor


def _clave_guardada(motor, correo: str) -> str:
    with database.SessionLocal(bind=motor) as sesion:
        usuario = sesion.scalar(select(models.Usuario).where(models.Usuario.correo == correo))
        return usuario.clave_hash


def _ejecuta(monkeypatch, *argumentos: str, tecleado: list[str] | None = None) -> int:
    monkeypatch.setattr("sys.argv", ["cambiar_la_clave.py", *argumentos])
    if tecleado is not None:
        respuestas = iter(tecleado)
        monkeypatch.setattr(cambiar_la_clave.getpass, "getpass", lambda _texto="": next(respuestas))
    return cambiar_la_clave.main()


class TestCuandoVaBien:
    def test_cambia_la_clave_de_la_cuenta(self, base_de_prueba, monkeypatch, capsys):
        assert _ejecuta(monkeypatch, "--correo", "david@ejemplo.test", "--clave", "la-nueva-2026") == 0

        guardada = _clave_guardada(base_de_prueba, "david@ejemplo.test")
        assert security.verificar_clave("la-nueva-2026", guardada), "la clave nueva no vale"
        assert not security.verificar_clave("la-de-siempre", guardada), "la clave vieja sigue valiendo"
        assert "la-nueva-2026" not in capsys.readouterr().out, "la clave ha salido por pantalla"

    def test_la_clave_se_puede_teclear_sin_dejarla_en_el_historial(self, base_de_prueba, monkeypatch):
        # Sin `--clave`, se pide dos veces y sin enseñarla: así no acaba en el historial de la consola
        # ni en una captura de pantalla.
        assert _ejecuta(
            monkeypatch,
            "--correo",
            "david@ejemplo.test",
            tecleado=["tecleada-a-mano", "tecleada-a-mano"],
        ) == 0
        assert security.verificar_clave(
            "tecleada-a-mano", _clave_guardada(base_de_prueba, "david@ejemplo.test")
        )

    def test_no_toca_las_demas_cuentas(self, base_de_prueba, monkeypatch):
        antes = _clave_guardada(base_de_prueba, "otro@ejemplo.test")
        _ejecuta(monkeypatch, "--correo", "david@ejemplo.test", "--clave", "otra-clave-larga")
        assert _clave_guardada(base_de_prueba, "otro@ejemplo.test") == antes

    def test_el_correo_se_acepta_con_mayusculas(self, base_de_prueba, monkeypatch):
        """Un correo escrito con mayúsculas es el mismo correo: no es motivo para no dejar entrar."""
        assert _ejecuta(monkeypatch, "--correo", "DAVID@EJEMPLO.TEST", "--clave", "con-mayusculas") == 0


class TestCuandoAlgoEstaMal:
    def test_una_clave_corta_se_rechaza_y_no_cambia_nada(self, base_de_prueba, monkeypatch, capsys):
        antes = _clave_guardada(base_de_prueba, "david@ejemplo.test")
        assert _ejecuta(monkeypatch, "--correo", "david@ejemplo.test", "--clave", "corta") == 1
        assert _clave_guardada(base_de_prueba, "david@ejemplo.test") == antes
        assert "al menos 8 caracteres" in capsys.readouterr().out

    def test_un_correo_que_no_existe_no_cambia_nada(self, base_de_prueba, monkeypatch, capsys):
        antes = _clave_guardada(base_de_prueba, "david@ejemplo.test")
        assert _ejecuta(monkeypatch, "--correo", "nadie@ejemplo.test", "--clave", "una-clave-larga") == 1
        assert _clave_guardada(base_de_prueba, "david@ejemplo.test") == antes
        salida = capsys.readouterr().out
        assert "No hay ninguna cuenta" in salida
        assert "No se ha tocado nada" in salida

    def test_si_las_dos_claves_no_coinciden_no_cambia_nada(self, base_de_prueba, monkeypatch, capsys):
        antes = _clave_guardada(base_de_prueba, "david@ejemplo.test")
        assert _ejecuta(
            monkeypatch, "--correo", "david@ejemplo.test", tecleado=["una-cosa", "otra-cosa"]
        ) == 1
        assert _clave_guardada(base_de_prueba, "david@ejemplo.test") == antes
        assert "no son iguales" in capsys.readouterr().out


class TestListarLasCuentas:
    def test_listar_enseña_las_cuentas_y_ninguna_clave(self, base_de_prueba, monkeypatch, capsys):
        assert _ejecuta(monkeypatch, "--listar") == 0
        salida = capsys.readouterr().out
        assert "david@ejemplo.test" in salida
        assert "David" in salida
        assert "otro@ejemplo.test" in salida
        # Ni la clave ni su huella: la huella tampoco, que para eso está guardada.
        assert "pbkdf2" not in salida
        assert security.hash_clave.__name__ not in salida

    def test_sin_correo_enseña_las_cuentas_en_vez_de_no_hacer_nada(self, base_de_prueba, monkeypatch, capsys):
        """Quien se ha olvidado de la clave tampoco se acuerda del correo: se le enseñan."""
        assert _ejecuta(monkeypatch) == 0
        assert "david@ejemplo.test" in capsys.readouterr().out


class TestSinBaseDeDatos:
    def test_si_no_hay_fichero_lo_dice_y_no_revienta(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv(
            "CUEDIGITAL_DATABASE_URL", f"sqlite:///{(tmp_path / 'no_existe.db').as_posix()}"
        )
        assert _ejecuta(monkeypatch, "--listar") == 1
        salida = capsys.readouterr().out
        assert "No encuentro la base de datos" in salida
        assert "CUEDIGITAL_DATABASE_URL" in salida
