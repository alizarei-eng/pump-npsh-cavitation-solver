# Pump NPSH & Cavitation Solver

CLI tool for pump suction NPSH, freshwater and **natural seawater**. EC is entered in mS/cm.

## Install and run

```bash
pip install -r requirements.txt
python main.py
python -m unittest discover -s tests
```

## Method

- Water-property implementation adapted from `alizarei-eng/calculates-diameter-HDPE/core/water_properties.py` (IAPWS-IF97; GSW/TEOS-10; Sharqawy viscosity).
- Seawater vapor-pressure correction: Sharqawy, Lienhard & Zubair (2010), ln(Psw/Pw) = -4.5818e-4*S - 2.0443e-6*S², S in g/kg. Pure-water saturation pressure from IAPWS97. Restricted to 0<T<100 C and 0<=S<=120 g/kg in this implementation.
- PSS-78 requires **in-situ** conductivity, not EC@25 C. EC@25 C is intentionally rejected until the meter's compensation algorithm is known.
- Only natural seawater chemistry is supported, not arbitrary RO concentrate/brine.
- NPSHa at suction flange = (P_suction_absolute - P_v)/(rho*g) + alpha*V²/(2*g), alpha=1; V=4Q/(pi*D²).
- Suction pressure must be measured at the pump suction flange. **Do not subtract upstream suction-line losses again.**
- NPSHr comes from manufacturer curves; NPSHa >= NPSHr alone does not guarantee cavitation-free operation. Manufacturer margin guidance still applies.
- Freshwater EC is recorded for context, not used to alter IAPWS properties.

## References

- IAPWS IF97: https://iapws.org/relguide/IF97-Rev.html
- GSW/TEOS-10: https://teos-10.github.io/GSW-Python/
- Sharqawy et al. (2010): https://web.mit.edu/lienhard/www/papers/journal/Thermophysical_properties_of_seawater-DWT-16-354-2010.pdf

## Desktop GUI (Tkinter)

Run `python gui.py` to open the graphical interface. Tkinter is included with most standard Python desktop installations; on some Linux distributions install `python3-tk` separately. The existing CLI remains available via `python main.py`.

The GUI accepts temperature, EC (mS/cm), fluid type, flow, internal pipe diameter, suction flange pressure (absolute or gauge), atmospheric pressure for gauge readings, and optional NPSHr. It displays fluid properties, velocity, vapor pressure, NPSHa, and NPSH margin. For natural seawater, use EC measured at the actual water temperature; EC@25C is rejected until meter-specific correction is available.
