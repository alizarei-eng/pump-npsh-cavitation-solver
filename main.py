"""Interactive NPSH solver. Run: python main.py"""
from core.water_properties import calculate_water_properties
from core.npsh import calculate

def ask_float(label, optional=False):
    while True:
        raw = input(label).strip()
        if optional and not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            print("Enter a numeric value.")

def run():
    while True:
        print("\\n=== PUMP NPSH & CAVITATION SOLVER ===")
        print("1. Freshwater  2. Natural seawater  0. Exit")
        kind = input("Select fluid: ").strip()
        if kind == "0": return
        if kind not in ("1", "2"):
            print("Invalid choice."); continue
        try:
            t = ask_float("Temperature [C]: ")
            ec = ask_float("EC [mS/cm]: ")
            mode = "in_situ"
            if kind == "2":
                mode = input("EC reference (1=in-situ, 2=EC@25C): ").strip()
                if mode != "1":
                    print("EC@25C conversion requires meter-specific compensation; enter in-situ EC."); continue
            q = ask_float("Flow [m3/h]: ")
            d = ask_float("Suction internal diameter [mm]: ")
            p = ask_float("Suction flange pressure [kPa]: ")
            pt = input("Pressure (1=absolute, 2=gauge): ").strip()
            if pt not in ("1","2"): raise ValueError("Choose 1 or 2 for pressure reference.")
            atm = ask_float("Atmospheric pressure [kPa]: ") if pt == "2" else None
            npshr = ask_float("NPSHr [m] (optional, Enter to skip): ", optional=True)
            p_abs = p if pt == "1" else p + atm
            # For seawater PSS-78, use near-surface ambient pressure as property reference;
            # suction pressure can be sub-atmospheric and is not sea hydrostatic pressure.
            property_p = max(0.101325, p_abs / 1000) if kind == "1" else 0.101325
            props = calculate_water_properties(temperature_C=t,
                water_type="freshwater" if kind=="1" else "seawater",
                pressure_MPa_abs=property_p, EC_value=ec, EC_unit="mS/cm",
                conductivity_temperature_mode="in_situ")
            pv = props["vapor_pressure_MPa"]
            if pv is None: raise ValueError("Vapor pressure is unavailable for this state.")
            result = calculate(flow_m3_h=q, diameter_mm=d, suction_pressure_kPa=p,
                pressure_type="absolute" if pt=="1" else "gauge",
                atmospheric_pressure_kPa=atm, density_kg_m3=props["density_kg_m3"],
                vapor_pressure_MPa=pv, npshr_m=npshr)
            print(f"\\nDensity: {props['density_kg_m3']:.3f} kg/m3")
            print(f"Vapor pressure: {pv*1000:.5f} kPa")
            print(f"Velocity: {result['velocity_m_s']:.4f} m/s")
            print(f"Velocity head: {result['velocity_head_m']:.4f} m")
            print(f"NPSHa: {result['npsha_m']:.4f} m")
            if npshr is not None:
                print(f"NPSH margin: {result['npsh_margin_m']:.4f} m")
                print(f"NPSH ratio: {result['npsh_ratio']:.4f}")
            print(result["assessment"])
            for warning in props["warnings"]: print("NOTE:", warning)
        except (ValueError, ImportError, NotImplementedError) as exc:
            print("ERROR:", exc)

if __name__ == "__main__":
    run()
