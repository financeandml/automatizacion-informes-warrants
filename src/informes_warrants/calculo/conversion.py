"""Emisores extranjeros (P4): estados en USD y por ADS, para que el informe y el modelo usen la misma unidad que la
cotización (el ADS en NYSE/Nasdaq, en USD).

- Flujos (resultados y flujo de caja): tipo medio de cada ejercicio; saldos (balance): tipo de cierre del ejercicio
  (NIC 21 / ASC 830, método del tipo de cierre). Fuente de los tipos en `ingesta/divisas.py`.
- Acciones: se dividen por el número de acciones ordinarias que representa cada ADS (del propio 20-F); el BPA y los
  importes por acción se multiplican por él. Sin ADS (acción ordinaria cotizada) el ratio es 1.
Cada dato convertido guarda en su origen la moneda, el tipo y el ratio aplicados.
"""

from dataclasses import replace

SALDOS = {"caja", "inversiones_cp", "clientes", "existencias", "activo_corriente", "inmovilizado", "fondo_comercio", "intangibles",
          "activos", "proveedores", "pasivo_corriente", "pasivos", "deuda_cp", "deuda_lp", "patrimonio", "patrimonio_temporal",
          "reservas", "minoritarios", "preferentes", "pensiones", "arrendamientos_financieros", "convertibles"}
ACCIONES = {"acciones_diluidas", "opciones_ejercitables", "rsu_pendientes"}
POR_ACCION = {"bpa_diluido", "precio_ejercicio_opciones"}
SIN_CONVERSION = {"ratio_conversion"}


def a_usd_y_ads(estados, tipos: dict[int, tuple[float, float]], moneda: str, ratio_ads: float = 1.0) -> None:
    """Convierte en el sitio `estados` (EstadosNormalizados): `tipos` = clave del ejercicio → (tipo medio, tipo de cierre)."""
    for partida, por_clave in estados.datos.items():
        if partida in SIN_CONVERSION:
            continue
        for clave, dato in list(por_clave.items()):
            if clave not in tipos:
                continue
            medio, cierre = tipos[clave]
            if partida in ACCIONES:
                factor, nota = 1 / ratio_ads, f"/{ratio_ads:g} acciones por ADS" if ratio_ads != 1 else ""
            elif partida in POR_ACCION:
                factor, nota = medio * ratio_ads, f"{moneda}×{medio:.6f}" + (f" ×{ratio_ads:g} por ADS" if ratio_ads != 1 else "")
            else:
                tipo = cierre if partida in SALDOS else medio
                factor, nota = tipo, f"{moneda}×{tipo:.6f} ({'cierre' if partida in SALDOS else 'medio'})"
            if factor != 1:
                por_clave[clave] = replace(dato, valor=dato.valor * factor, origen=f"{dato.origen} · {nota}")
