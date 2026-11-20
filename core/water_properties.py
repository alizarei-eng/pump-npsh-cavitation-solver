"""Water-property calculations for freshwater and natural seawater.

Freshwater:
    IAPWS-IF97 for density, dynamic viscosity and saturation pressure.

Natural seawater:
    GSW/TEOS-10 for PSS-78 practical salinity, Absolute Salinity and density.
    Sharqawy et al. (2010) correlation for dynamic viscosity.

Inland brines are deliberately not inferred from EC alone.
All pressures supplied to the public API are absolute MPa.
"""

from __future__ import annotations

import math
from typing import Any

try:
    from iapws import IAPWS97
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    IAPWS97 = None

try:
    import gsw
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    gsw = None


STANDARD_ATMOSPHERE_MPA = 0.101325
GRAVITY_M_S2 = 9.80665

_EC_TO_MS_CM = {
    "uS/cm": 0.001,
    "µS/cm": 0.001,
    "μS/cm": 0.001,
    "mS/cm": 1.0,
    "S/m": 10.0,
}


def _finite_number(name: str, value: Any) -> float:
    """Convert a value to a finite float or raise a useful ValueError."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number, not bool.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number


def conductivity_to_ms_cm(value: float, unit: str) -> float:
    """Convert electrical conductivity to mS/cm."""
    if unit not in _EC_TO_MS_CM:
        allowed = ", ".join(_EC_TO_MS_CM)
        raise ValueError(f"Unsupported EC unit {unit!r}. Allowed units: {allowed}.")
    ec = _finite_number("EC_value", value)
    if ec < 0:
        raise ValueError("EC_value cannot be negative.")
    return ec * _EC_TO_MS_CM[unit]


def sharqawy_seawater_viscosity_Pa_s(
    temperature_C: float, salinity_g_kg: float
) -> float:
    """Dynamic viscosity from Sharqawy et al. (2010), Eqs. 22 and 23.

    Salinity is supplied in g/kg and converted internally to mass fraction.
    Documented correlation domain: 0 < t < 180 °C and 0 < S < 0.15 kg/kg.
    """
    t = _finite_number("temperature_C", temperature_C)
    salinity = _finite_number("salinity_g_kg", salinity_g_kg)
    mass_fraction = salinity / 1000.0

    if not (0.0 < t < 180.0):
        raise ValueError("Sharqawy viscosity correlation requires 0 < temperature_C < 180.")
    if not (0.0 < mass_fraction < 0.15):
        raise ValueError("Sharqawy correlation requires 0 < salinity mass fraction < 0.15.")

    mu_water = 4.2844e-5 + (
        0.157 * (t + 64.993) ** 2 - 91.296
    ) ** -1

    a = 1.541 + 1.998e-2 * t - 9.52e-5 * t**2
    b = 7.974 - 7.561e-2 * t + 4.724e-4 * t**2
    mu_seawater = mu_water * (1.0 + a * mass_fraction + b * mass_fraction**2)

    if not math.isfinite(mu_seawater) or mu_seawater <= 0:
        raise ArithmeticError("Sharqawy correlation returned a non-physical viscosity.")
    return mu_seawater


def _base_result(water_type: str, temperature_C: float, pressure_MPa_abs: float) -> dict:
    return {
        "water_type": water_type,
        "temperature_C": temperature_C,
        "pressure_MPa_abs": pressure_MPa_abs,
        "method": None,
        "practical_salinity": None,
        "absolute_salinity_g_kg": None,
        "density_kg_m3": None,
        "dynamic_viscosity_Pa_s": None,
        "kinematic_viscosity_m2_s": None,
        "vapor_pressure_MPa": None,
        "warnings": [],
        "assumptions": [],
        "validity": {},
    }


def calculate_water_properties(
    *,
    temperature_C: float,
    water_type: str,
    pressure_MPa_abs: float = STANDARD_ATMOSPHERE_MPA,
    EC_value: float | None = None,
    EC_unit: str | None = None,
    conductivity_temperature_mode: str = "in_situ",
    latitude_deg: float | None = None,
    longitude_deg: float | None = None,
) -> dict:
    """Calculate water properties and return a serializable dictionary.

    Parameters
    ----------
    temperature_C:
        In-situ water temperature in degrees Celsius.
    water_type:
        'freshwater', 'seawater', or 'inland_brine'.
    pressure_MPa_abs:
        Absolute pressure in MPa (not gauge pressure).
    EC_value, EC_unit:
        Conductivity and one of uS/cm, µS/cm, μS/cm, mS/cm, S/m.
    conductivity_temperature_mode:
        Must be 'in_situ' for seawater PSS-78. Compensated EC is rejected.
    latitude_deg, longitude_deg:
        Optional geographic coordinates for TEOS-10 Absolute Salinity.

    Notes
    -----
    For inland_brine, this function raises NotImplementedError because EC alone
    cannot uniquely determine salinity, density or viscosity for arbitrary brines.
    """
    t = _finite_number("temperature_C", temperature_C)
    p_abs = _finite_number("pressure_MPa_abs", pressure_MPa_abs)
    kind = str(water_type).strip().lower()

    if p_abs <= 0:
        raise ValueError("pressure_MPa_abs must be greater than zero.")
    if kind not in {"freshwater", "seawater", "inland_brine"}:
        raise ValueError("water_type must be freshwater, seawater, or inland_brine.")

    result = _base_result(kind, t, p_abs)

    if kind == "inland_brine":
        raise NotImplementedError(
            "Inland brine properties cannot be inferred from EC alone. "
            "Provide a validated chemistry-specific model or full ionic analysis."
        )

    if kind == "freshwater":
        if IAPWS97 is None:
            raise ImportError("Freshwater calculations require 'iapws'. Install requirements.txt.")
        state = IAPWS97(T=t + 273.15, P=p_abs)
        rho = float(state.rho)
        mu = float(state.mu)

        if not (math.isfinite(rho) and rho > 0 and math.isfinite(mu) and mu > 0):
            raise ArithmeticError("IAPWS-IF97 returned non-physical freshwater properties.")

        result.update({
            "method": "IAPWS-IF97",
            "density_kg_m3": rho,
            "dynamic_viscosity_Pa_s": mu,
            "kinematic_viscosity_m2_s": mu / rho,
            "vapor_pressure_MPa": None,
            "validity": {
                "model": "IAPWS-IF97",
                "note": "IAPWS-IF97 validity depends on thermodynamic region and input state."
            },
        })

        # Saturation pressure is a temperature-only property for a liquid-vapor
        # equilibrium state. IAPWS97(x=0) supplies saturated-liquid state.
        try:
            if 0.0 < t < 373.946:
                sat_liquid = IAPWS97(T=t + 273.15, x=0)
                result["vapor_pressure_MPa"] = float(sat_liquid.P)
            else:
                result["warnings"].append(
                    "Saturation pressure was not calculated outside the subcritical liquid range."
                )
        except Exception as exc:
            result["warnings"].append(f"Could not calculate saturation pressure: {exc}")

        if EC_value is not None:
            if EC_unit is None:
                raise ValueError("EC_unit is required when EC_value is provided.")
            ec_ms_cm = conductivity_to_ms_cm(EC_value, EC_unit)
            result["conductivity_mS_cm"] = ec_ms_cm
            result["warnings"].append(
                "EC is recorded for water-quality context only; it is not used to modify IAPWS freshwater properties."
            )
        elif EC_unit is not None:
            raise ValueError("EC_unit was provided without EC_value.")

        return result

    # Natural seawater branch
    if gsw is None:
        raise ImportError("Seawater calculations require 'gsw'. Install requirements.txt.")
    if EC_value is None or EC_unit is None:
        raise ValueError("Natural seawater requires EC_value and EC_unit.")
    if conductivity_temperature_mode != "in_situ":
        raise ValueError(
            "PSS-78 requires in-situ conductivity. Temperature-compensated EC "
            "cannot be used unless the compensation algorithm is known and reversed."
        )

    ec_ms_cm = conductivity_to_ms_cm(EC_value, EC_unit)
    p_sea_dbar = (p_abs - STANDARD_ATMOSPHERE_MPA) * 100.0
    if p_sea_dbar < -1.0:
        raise ValueError(
            "Absolute pressure is below the standard-atmosphere reference; "
            "check pressure reference and units before converting to sea pressure."
        )

    practical_salinity = float(gsw.SP_from_C(ec_ms_cm, t, p_sea_dbar))
    if not math.isfinite(practical_salinity) or practical_salinity < 0:
        raise ValueError("PSS-78 returned an invalid practical salinity.")

    if latitude_deg is not None or longitude_deg is not None:
        if latitude_deg is None or longitude_deg is None:
            raise ValueError("Provide both latitude_deg and longitude_deg, or neither.")
        lat = _finite_number("latitude_deg", latitude_deg)
        lon = _finite_number("longitude_deg", longitude_deg)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValueError("Latitude must be in [-90, 90] and longitude in [-180, 180].")
        absolute_salinity = float(gsw.SA_from_SP(practical_salinity, p_sea_dbar, lon, lat))
        result["assumptions"].append(
            "Absolute Salinity calculated by TEOS-10 using the supplied geographic position."
        )
    else:
        absolute_salinity = float(gsw.SR_from_SP(practical_salinity))
        result["warnings"].append(
            "No coordinates supplied: Absolute Salinity approximated by Reference Salinity; "
            "the local delta-SA anomaly is not included."
        )

    conservative_temperature = float(
        gsw.CT_from_t(absolute_salinity, t, p_sea_dbar)
    )
    rho = float(gsw.rho(absolute_salinity, conservative_temperature, p_sea_dbar))
    mu = sharqawy_seawater_viscosity_Pa_s(t, absolute_salinity)

    if not all(math.isfinite(v) and v > 0 for v in (rho, mu)):
        raise ArithmeticError("Seawater model returned non-physical density or viscosity.")

    result.update({
        "method": "GSW/TEOS-10 (PSS-78 + Absolute Salinity + density) and Sharqawy et al. (2010) viscosity",
        "conductivity_mS_cm": ec_ms_cm,
        "sea_pressure_dbar": p_sea_dbar,
        "practical_salinity": practical_salinity,
        "absolute_salinity_g_kg": absolute_salinity,
        "conservative_temperature_C": conservative_temperature,
        "density_kg_m3": rho,
        "dynamic_viscosity_Pa_s": mu,
        "kinematic_viscosity_m2_s": mu / rho,
        "vapor_pressure_MPa": seawater_vapor_pressure_MPa(t, absolute_salinity),
        "validity": {
            "salinity_method": "PSS-78 / TEOS-10",
            "viscosity_method": "Sharqawy et al. (2010), Eqs. 22-23",
            "viscosity_temperature_C": "0 < t < 180",
            "viscosity_salinity_mass_fraction": "0 < S < 0.15",
        },
    })
    result["assumptions"].append("Seawater vapor pressure uses the Sharqawy et al. (2010) salinity correction to pure-water saturation pressure.")
    result["assumptions"].append(
        "Water is treated as natural seawater compatible with PSS-78, not an arbitrary industrial brine."
    )
    return result


def seawater_vapor_pressure_MPa(temperature_C: float, salinity_g_kg: float) -> float:
    """Sharqawy et al. (2010), seawater vapor-pressure correction.

    ln(P_sw/P_w) = -4.5818e-4*S - 2.0443e-6*S**2,
    S in g/kg. Intended for ordinary seawater in the liquid range.
    P_w from IAPWS97 saturation. Conservative application range: 0<t<100 C,
    0<=S<=120 g/kg. Do not extrapolate to arbitrary RO concentrate chemistry.
    """
    t = _finite_number("temperature_C", temperature_C)
    s = _finite_number("salinity_g_kg", salinity_g_kg)
    if not (0 < t < 100 and 0 <= s <= 120):
        raise ValueError("Seawater vapor pressure requires 0<T<100 C and 0<=S<=120 g/kg.")
    if IAPWS97 is None:
        raise ImportError("Install iapws for seawater vapor-pressure calculation.")
    p_pure = float(IAPWS97(T=t + 273.15, x=0).P)
    return p_pure * math.exp(-4.5818e-4 * s - 2.0443e-6 * s * s)
