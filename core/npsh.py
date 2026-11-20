"""NPSH calculations at the pump suction flange (SI units)."""
from __future__ import annotations
import math
G = 9.80665

def calculate(*, flow_m3_h: float, diameter_mm: float, suction_pressure_kPa: float,
              pressure_type: str, density_kg_m3: float, vapor_pressure_MPa: float,
              atmospheric_pressure_kPa: float | None = None,
              npshr_m: float | None = None, alpha: float = 1.0) -> dict:
    vals = [flow_m3_h, diameter_mm, suction_pressure_kPa, density_kg_m3, vapor_pressure_MPa, alpha]
    if not all(math.isfinite(float(x)) for x in vals):
        raise ValueError("All inputs must be finite.")
    if flow_m3_h < 0 or diameter_mm <= 0 or density_kg_m3 <= 0 or vapor_pressure_MPa <= 0 or alpha <= 0:
        raise ValueError("Invalid nonpositive physical parameter.")
    kind = pressure_type.lower().strip()
    if kind not in ("absolute", "gauge"):
        raise ValueError("pressure_type must be absolute or gauge.")
    if kind == "gauge":
        if atmospheric_pressure_kPa is None or atmospheric_pressure_kPa <= 0:
            raise ValueError("Gauge pressure requires positive atmospheric pressure in kPa.")
        p_abs = suction_pressure_kPa + atmospheric_pressure_kPa
    else:
        p_abs = suction_pressure_kPa
    if p_abs <= 0:
        raise ValueError("Suction absolute pressure must be positive.")
    d = diameter_mm / 1000
    q = flow_m3_h / 3600
    v = 4 * q / (math.pi * d*d)
    pressure_margin_head = (p_abs*1000 - vapor_pressure_MPa*1e6)/(density_kg_m3*G)
    velocity_head = alpha*v*v/(2*G)
    available = pressure_margin_head + velocity_head
    result = dict(velocity_m_s=v, velocity_head_m=velocity_head,
                  suction_pressure_absolute_kPa=p_abs, pressure_margin_head_m=pressure_margin_head,
                  npsha_m=available, npshr_m=npshr_m, npsh_margin_m=None,
                  npsh_ratio=None, assessment="NPSHr unavailable: cannot assess margin.")
    if npshr_m is not None:
        if not math.isfinite(npshr_m) or npshr_m <= 0:
            raise ValueError("NPSHr must be positive and finite.")
        result["npsh_margin_m"] = available-npshr_m
        result["npsh_ratio"] = available/npshr_m
        result["assessment"] = ("NPSHa below NPSHr: high cavitation risk." if available < npshr_m
                                else "NPSHa meets NPSHr; verify manufacturer-recommended margin.")
    return result
