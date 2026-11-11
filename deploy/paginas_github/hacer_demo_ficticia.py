"""Convierte la demo estática en **datos ficticios** (10/11/2026).

## Por qué

Los coordinadores avisaron: la demo pública llevaba **las parcelas reales de un cliente**. No puede
ser. La app privada ya no está publicada (solo se entra por la red de Tailscale), y la demo de
GitHub Pages se queda **solo con tierras inventadas**, que es lo que se puede enseñar en un
portfolio.

## Qué hace

Coge el `datos.json` que sacó del servidor y **le cambia todo lo que identifica al cliente**:

- el nombre de la finca y la cuenta;
- las cinco tierras: nombre, referencia, municipio, provincia, superficies, centro y forma (se
  inventan unos rectángulos, no se reaprovecha ni un vértice del cliente);
- las búsquedas del SIGPAC (el alta por referencia de la demo sigue funcionando con las
  referencias inventadas);
- los apuntes y el calendario, que se dejan vacíos.

No inventa ninguna persona: la cuenta es «Cuenta de ejemplo» y la finca «Finca de ejemplo
(ficticia)». Lo que se conserva es el vocabulario de la pantalla (`interfaz`), que es texto de la
aplicación, no de nadie.

Uso:

    python deploy/paginas_github/hacer_demo_ficticia.py
"""

from __future__ import annotations

import json
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[2]
DEMO = RAIZ / "deploy" / "paginas_github" / "demo" / "datos.json"

MUNICIPIO = "Villa de Ejemplo"
PROVINCIA = "Valladolid"
FINCA = "Finca de ejemplo (ficticia)"
CUENTA = {"nombre": "Cuenta de ejemplo", "correo": "demo@cuedigital.local"}

# Cinco tierras inventadas: nombre, referencia (provincia 47 real, municipio 99 inventado),
# superficie y el sitio donde se dibujan (un punto y un lado del rectángulo, en grados).
TIERRAS = (
    ("El Llano", "47-99-0-0-901-1-1", 4.20, -4.7200, 41.6500, 0.0040),
    ("La Fuente", "47-99-0-0-901-2-1", 3.10, -4.7400, 41.6600, 0.0035),
    ("Los Olmos", "47-99-0-0-902-1-1", 2.50, -4.7000, 41.6400, 0.0030),
    ("La Dehesa", "47-99-0-0-902-2-2", 1.80, -4.7600, 41.6550, 0.0025),
    ("El Barbecho", "47-99-0-0-903-1-1", 0.90, -4.7100, 41.6650, 0.0020),
)

# El uso del SIGPAC con su nombre largo, para que la ficha no salga con un código suelto.
USOS = (("TA", "TIERRAS ARABLES"), ("TA", "TIERRAS ARABLES"), ("PR", "PASTO ARBUSTIVO"),
        ("PR", "PASTO ARBUSTIVO"), ("TA", "TIERRAS ARABLES"))


def el_anillo(lon: float, lat: float, lado: float) -> list[list[float]]:
    """Un rectángulo cerrado alrededor de un punto: la forma de la tierra inventada."""
    return [
        [lon, lat],
        [lon + lado, lat],
        [lon + lado, lat + lado * 0.7],
        [lon, lat + lado * 0.7],
        [lon, lat],
    ]


def el_centro(anillo: list[list[float]]) -> list[float]:
    xs = [punto[0] for punto in anillo]
    ys = [punto[1] for punto in anillo]
    return [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2]


def main() -> int:
    datos = json.loads(DEMO.read_text(encoding="utf-8"))

    tierras = []
    for indice, (alias, referencia, superficie, lon, lat, lado) in enumerate(TIERRAS):
        anillo = el_anillo(lon, lat, lado)
        uso, uso_largo = USOS[indice]
        tierras.append(
            {
                "id": indice + 1,
                "alias": alias,
                "municipio": MUNICIPIO,
                "provincia": PROVINCIA,
                "superficie_ha": superficie,
                "superficie_sigpac_ha": superficie,
                "uso_sigpac": uso,
                "coef_regadio": None,
                "region": None,
                "admisibilidad": None,
                "centro": el_centro(anillo),
                "anillo": anillo,
                "cultivo": None,
                "otros_anios": [],
                "_uso_largo": uso_largo,
            }
        )

    cajas = [punto for tierra in tierras for punto in tierra["anillo"]]
    bbox = [
        min(punto[0] for punto in cajas),
        min(punto[1] for punto in cajas),
        max(punto[0] for punto in cajas),
        max(punto[1] for punto in cajas),
    ]
    hectareas = round(sum(tierra["superficie_ha"] for tierra in tierras), 2)

    # Las tierras y sus fichas
    datos["tierras"]["tierras"] = [
        {clave: valor for clave, valor in tierra.items() if clave != "_uso_largo"} for tierra in tierras
    ]
    datos["tierras"]["municipios"] = [
        {"nombre": MUNICIPIO, "n": len(tierras), "ha": hectareas, "bbox": bbox}
    ]
    datos["tierras"]["totales"] = {"n": len(tierras), "ha": hectareas, "municipios": 1}
    datos["tierras"]["campana"] = {"id": 1, "anio": 2026}
    datos["tierras"]["finca"] = {"nombre": FINCA, "municipio": MUNICIPIO, "provincia": PROVINCIA}

    for tierra in tierras:
        datos[f"tierra_{tierra['id']}"] = {
            "tierra": {clave: valor for clave, valor in tierra.items() if clave != "_uso_largo"},
            "trabajo_de_hoy": [],
            "historial": [],
            "guia": [{"codigo": "cultivo", "fecha": None, "estado": "sin-fecha", "dias": None}],
            "resumen": {
                "n_apuntes": 0,
                "primera_fecha": None,
                "ultima_fecha": None,
                "kg_ha_ultima_cosecha": None,
            },
        }

    # La portada y la cuenta
    plantilla_textos = (datos.get("busquedas") or {}).values()
    textos_de_la_busqueda = next(iter(plantilla_textos), {}).get("textos") if plantilla_textos else None
    datos["hoy"] = {
        "finca": {"nombre": FINCA, "municipio": MUNICIPIO, "provincia": PROVINCIA},
        "campana": {"id": 1, "anio": 2026},
        "cuenta": dict(CUENTA),
        "tierras": {"n": len(tierras), "ha": hectareas},
        # **Ocho apuntes ficticios** (CU-I1, 11/11/2026): la pantalla de «Hoy» no puede enseñar una
        # finca vacía. Son inventados, con las tierras inventadas y productos de ejemplo.
        "ultimos": [
            {"tipo": "tratamiento", "fecha": "2026-11-08", "tierra": "El Llano", "titulo": "Herbicida de ejemplo"},
            {"tipo": "tratamiento", "fecha": "2026-11-07", "tierra": "La Fuente", "titulo": "Insecticida de ejemplo"},
            {"tipo": "fertilizacion", "fecha": "2026-11-05", "tierra": "Los Olmos", "titulo": "Abono de ejemplo"},
            {"tipo": "labor", "fecha": "2026-11-04", "tierra": "La Dehesa", "titulo": "Preparación del terreno"},
            {"tipo": "tratamiento", "fecha": "2026-11-02", "tierra": "El Barbecho", "titulo": "Fungicida de ejemplo"},
            {"tipo": "fertilizacion", "fecha": "2026-10-29", "tierra": "El Llano", "titulo": "Abono de cobertera"},
            {"tipo": "labor", "fecha": "2026-10-27", "tierra": "La Fuente", "titulo": "Siembra"},
            {"tipo": "labor", "fecha": "2026-10-24", "tierra": "Los Olmos", "titulo": "Pase de grada"},
        ],
    }
    datos["cuenta"] = {
        "usuario_id": 1,
        "explotacion_id": 1,
        "nombre": CUENTA["nombre"],
        "correo": CUENTA["correo"],
        "explotacion": {"nombre": FINCA, "municipio": MUNICIPIO, "provincia": PROVINCIA},
    }

    # La búsqueda del SIGPAC, con las referencias inventadas (para que el alta de la demo funcione)
    datos["busquedas"] = {}
    for indice, (alias, referencia, superficie, lon, lat, lado) in enumerate(TIERRAS):
        parcelaria = referencia.rsplit("-", 1)[0]
        recintos = []
        for trozo in (1, 2):
            anillo = el_anillo(lon + trozo * lado * 1.2, lat, lado * 0.5)
            recintos.append(
                {
                    "recinto": trozo,
                    "referencia": f"{parcelaria}-{trozo}",
                    "superficie_ha": round(superficie / 2, 4),
                    "uso_sigpac": USOS[indice][0],
                    "uso": USOS[indice][1],
                    "pendiente_pct": 2.0,
                    "altitud": 780,
                    "coeficiente_regadio": 0.0,
                    "region": 2,
                    "admisibilidad": None,
                    "tiene_dibujo": True,
                    "puntos": anillo,
                }
            )
        datos["busquedas"][referencia] = {
            "textos": textos_de_la_busqueda,
            "busqueda": referencia.replace("-", ":"),
            "referencia_catastral": None,
            "municipio": {"nombre": MUNICIPIO, "provincia": PROVINCIA, "codigo_ine": "47999"},
            "encontrados": len(recintos),
            "recintos": recintos,
            "mensaje": None,
        }
    datos["referencias"] = [tierra[1] for tierra in TIERRAS]

    # Sin apuntes ni calendario: la demo no enseña trabajos de nadie.
    datos["trabajos"] = {
        "tipos": [],
        "elegido": None,
        "trabajos": [],
        "resumen": {"n": 0, "ha": None, "cantidades": []},
    }
    datos["calendario"] = {
        "desde": "2026-11-01",
        "hasta": "2026-11-30",
        "dias": [],
        "totales": {"n": 0, "cantidades": []},
    }
    datos["facturas"] = []
    datos["documentos"] = []
    # **Gastos y ventas ficticios** (CU-I1): una finca de verdad no está a cero. Los importes son
    # inventados y no vienen de ninguna cuenta de nadie.
    datos["resumen"] = {
        "gastos": {"total": 1240.5, "pendiente": 320.0},
        "ventas": {"total": 5400.0, "cobrado": 3000.0, "pendiente": 2400.0},
        "cuaderno": {"faltan": 3, "ejemplos": ["el nº de registro de la explotación", "la dirección y la localidad", "un teléfono de contacto"]},
        "facturas": {"n": 2},
    }
    datos["que_falta"] = {"faltan": 0, "items": []}

    DEMO.write_text(
        json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline=""
    )
    print(f"Demo ficticia escrita en {DEMO} ({DEMO.stat().st_size // 1024} KB)")
    print("tierras:", ", ".join(t[0] for t in TIERRAS))
    print("municipio:", MUNICIPIO, "·", PROVINCIA, f"· {hectareas} ha inventadas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
