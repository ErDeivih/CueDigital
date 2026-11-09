"""**La dirección de la base en la forma que entiende SQLAlchemy** (09/11/2026).

EL FALLO QUE CIERRA ESTE TEST
=============================

Render, Neon, Supabase y casi cualquier proveedor de PostgreSQL entregan la dirección
de conexión como `postgres://usuario:clave@host/base` o `postgresql://...`. SQLAlchemy 2
**no acepta esos dos nombres de esquema**: necesita el driver explícito
(`postgresql+psycopg://`). Con la dirección tal cual, el programa no arranca en el
servidor de verdad y el error no dice nada de la causa: dice que no encuentra el
dialecto `postgres`, y quien lo lee está copiando y pegando una dirección del panel del
proveedor.

Se comprueba **sin servidor y sin base**: solo la función que decide la dirección, que
es lo que se rompe. Las direcciones que ya traen driver (`+psycopg`, `+asyncpg`) y la de
SQLite se quedan como están, que es lo que usan los tests y el desarrollo.
"""

from __future__ import annotations

import pytest

from app import database

POSTGRES_SIN_DRIVER = (
    ("postgres://cuedigital:clave@host:5432/cuedigital", "postgresql+psycopg://cuedigital:clave@host:5432/cuedigital"),
    ("postgresql://cuedigital:clave@host:5432/cuedigital", "postgresql+psycopg://cuedigital:clave@host:5432/cuedigital"),
    ("postgres://usuario@host/base?sslmode=require", "postgresql+psycopg://usuario@host/base?sslmode=require"),
)

YA_VALIDAS = (
    "postgresql+psycopg://cuedigital:clave@host:5432/cuedigital",
    "postgresql+asyncpg://cuedigital:clave@host:5432/cuedigital",
    "sqlite:///./cuedigital.db",
    "sqlite://",
)


@pytest.mark.parametrize(("cruda", "esperada"), POSTGRES_SIN_DRIVER)
def test_una_direccion_de_proveedor_lleva_el_driver_de_psycopg(cruda, esperada):
    """La dirección que da el panel del proveedor se usa sin editarla a mano."""
    assert database._normalizar_url(cruda) == esperada


@pytest.mark.parametrize("url", YA_VALIDAS)
def test_una_direccion_que_ya_lleva_driver_no_se_toca(url):
    """SQLite y las que ya traen driver se quedan como están: no se reescribe lo que vale."""
    assert database._normalizar_url(url) == url


def test_url_base_datos_normaliza_lo_que_viene_del_entorno(monkeypatch):
    """Por donde entra de verdad: la variable de entorno del servidor."""
    monkeypatch.setenv(
        "CUEDIGITAL_DATABASE_URL", "postgres://cuedigital:clave@host:5432/cuedigital"
    )
    assert database.url_base_datos() == (
        "postgresql+psycopg://cuedigital:clave@host:5432/cuedigital"
    )


def test_sin_variable_sigue_siendo_sqlite(monkeypatch):
    """El desarrollo y los tests no cambian: sin variable, SQLite."""
    monkeypatch.delenv("CUEDIGITAL_DATABASE_URL", raising=False)
    assert database.url_base_datos() == database.URL_POR_DEFECTO
