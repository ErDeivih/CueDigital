"""Regresiones de la revisión en Linux, sobre archivos y datos temporales."""

import datetime as dt
from pathlib import Path
import re
import subprocess

from sqlalchemy import create_engine, select
from sqlalchemy.schema import CreateTable

from app import database, models, textos
from scripts import navegador_cdp


def test_el_cliente_lee_el_contexto_del_token_real_del_servidor():
    from app.security import crear_token

    # Acoplar ambos extremos: el token de producción es carga.firma, no un JWT.
    resultado = subprocess.run(
        ["node", "--input-type=module", "-e", """
            import assert from 'node:assert/strict';
            import { sesionDelToken } from './nucleo.js';
            let token = '';
            for await (const trozo of process.stdin) token += trozo;
            assert.equal(sesionDelToken(token), '32:47');
        """],
        input=crear_token(32, 47), text=True, capture_output=True, timeout=15,
        cwd=Path(__file__).resolve().parents[1] / "web",
    )
    assert resultado.returncode == 0, resultado.stderr


def test_migrar_una_venta_antigua_conserva_la_fila_y_repara_la_clave(tmp_path):
    motor = create_engine(f"sqlite:///{tmp_path / 'antigua.db'}")
    try:
        models.Base.metadata.create_all(motor)
        tabla = models.VentaDeCosecha.__table__
        ddl = str(CreateTable(tabla).compile(dialect=motor.dialect))
        antiguo, quitadas = re.subn(
            r",\s*FOREIGN KEY\(contacto_id\) REFERENCES contactos \(id\)", "", ddl
        )
        assert quitadas == 1, "la reproducción debe quitar solo la clave que faltaba"
        with motor.begin() as c:
            c.exec_driver_sql("DROP TABLE ventas_de_cosecha")
            c.exec_driver_sql(antiguo)
            c.execute(models.Explotacion.__table__.insert().values(id=1, nombre="Prueba", nif="00000000T"))
            c.execute(models.Campana.__table__.insert().values(
                id=1, explotacion_id=1, anio=2026,
                fecha_inicio=dt.date(2026, 1, 1), fecha_fin=dt.date(2026, 12, 31),
            ))
            c.execute(tabla.insert().values(
                id=99, explotacion_id=1, campana_id=1, fecha=dt.date(2026, 6, 1),
                producto="Trigo de prueba", cantidad=50,
                creado_en=dt.datetime(2026, 6, 1), actualizado_en=dt.datetime(2026, 6, 1),
            ))
        assert database.las_claves_ajenas_que_faltan(motor, tabla.name) == {"contacto_id"}
        assert tabla.name in database.reconstruir_para_que_nazcan_las_claves_ajenas(motor)
        assert database.las_claves_ajenas_que_faltan(motor, tabla.name) == set()
        with motor.connect() as c:
            fila = c.execute(select(tabla).where(tabla.c.id == 99)).mappings().one()
            assert (fila["producto"], fila["cantidad"]) == ("Trigo de prueba", 50)
        assert list(tmp_path.glob("antigua.db.antes-de-migrar-*"))
        assert database.reconstruir_para_que_nazcan_las_claves_ajenas(motor) == []
    finally:
        motor.dispose()


def test_el_navegador_del_path_se_encuentra_sin_ruta_de_windows(monkeypatch):
    monkeypatch.setattr(navegador_cdp, "NAVEGADORES", [])
    monkeypatch.setattr(navegador_cdp.shutil, "which", lambda nombre: "/opt/chromium" if nombre == "chromium" else None)
    assert navegador_cdp.el_navegador() == "/opt/chromium"


def test_la_marca_de_la_interfaz_y_la_instalacion_coinciden(cliente):
    assert cliente.get("/api/interfaz").json()["marca"] == textos.MARCA
    manifest = cliente.get("/manifest.webmanifest").json()
    assert manifest["name"] == manifest["short_name"] == textos.MARCA["nombre"]
    assert "orientation" not in manifest, "el escritorio y el mapa admiten paisaje"
    assert textos.MARCA["lema"] in textos.textos_visibles()
    icono = cliente.get(manifest["icons"][0]["src"])
    assert icono.status_code == 200 and "image/svg+xml" in icono.headers["content-type"]
    assert "<svg" in icono.text and "<text" not in icono.text, "el símbolo no depende de un emoji"
