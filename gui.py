"""Tkinter GUI for the NPSH solver. Run: python gui.py"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

from core.npsh import calculate
from core.water_properties import calculate_water_properties


AUTHOR = "Ali_zarei_eng"

PRESSURE_TO_KPA = {"bar": 100.0, "psi": 6.894757293168, "kPa": 1.0, "Pa": 0.001}


def pressure_to_kpa(value: float, unit: str) -> float:
    """Convert pressure magnitude to kPa without changing gauge/absolute reference."""
    if unit not in PRESSURE_TO_KPA:
        raise ValueError(f"Unsupported pressure unit: {unit}")
    if not math.isfinite(value):
        raise ValueError("Pressure must be finite.")
    return value * PRESSURE_TO_KPA[unit]


class NPSHApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pump NPSH & Cavitation Solver")
        self.geometry("790x760")
        self.minsize(680, 640)
        self.configure(bg="#eef3f8")
        self.vars = {
            "fluid": tk.StringVar(value="seawater"),
            "temperature": tk.StringVar(value="30"),
            "ec": tk.StringVar(value="58"),
            "flow": tk.StringVar(value="150"),
            "diameter": tk.StringVar(value="204.6"),
            "pressure": tk.StringVar(value="100"),
            "pressure_type": tk.StringVar(value="gauge"),
            "pressure_unit": tk.StringVar(value="kPa"),
            "atmospheric_unit": tk.StringVar(value="kPa"),
            "atmospheric": tk.StringVar(value="101.325"),
            "npshr": tk.StringVar(value=""),
        }
        self.report_text = None
        self._build()
        self.vars["pressure_type"].trace_add("write", lambda *_: self._update_state())
        self.vars["fluid"].trace_add("write", lambda *_: self._update_state())
        self.vars["pressure_unit"].trace_add("write", lambda *_: self._sync_atmospheric_unit())
        self._update_state()

    def _build(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#eef3f8")
        style.configure("TLabelframe", background="#eef3f8")
        style.configure("TLabelframe.Label", background="#eef3f8", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#eef3f8", font=("Segoe UI", 10))
        style.configure("TButton", padding=8, font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", padding=4)
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="PUMP NPSH & CAVITATION SOLVER",
                  font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text=f"Developed by {AUTHOR}",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(2, 2))
        ttk.Label(outer, text="Pump suction flange method | SI units",
                  font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 12))

        fluid = ttk.LabelFrame(outer, text="Fluid properties", padding=12)
        fluid.pack(fill="x", pady=5)
        self._combo(fluid, 0, "Fluid", "fluid", ["freshwater", "seawater"])
        self._entry(fluid, 1, "Temperature [°C]", "temperature")
        self.ec_entry = self._entry(fluid, 2, "EC [mS/cm] (in-situ at water temperature)", "ec")

        suction = ttk.LabelFrame(outer, text="Suction conditions", padding=12)
        suction.pack(fill="x", pady=5)
        self._entry(suction, 0, "Flow rate [m³/h]", "flow")
        self._entry(suction, 1, "Pipe internal diameter [mm]", "diameter")
        self._entry(suction, 2, "Flange suction pressure", "pressure")
        self._combo(suction, 3, "Suction pressure unit", "pressure_unit",
                    ["bar", "psi", "kPa", "Pa"])
        self._combo(suction, 4, "Pressure reference", "pressure_type",
                    ["gauge", "absolute"])
        self.atm_entry = self._entry(suction, 5, "Atmospheric pressure", "atmospheric")
        ttk.Label(suction, text="Atmospheric unit follows suction pressure unit automatically.").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=4)
        self._entry(suction, 7, "NPSHr [m] (optional)", "npshr")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(10, 6))
        ttk.Button(actions, text="Calculate", command=self._calculate).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Clear results", command=self._clear).pack(side="left", padx=(0, 8))
        self.save_button = ttk.Button(actions, text="Export TXT", command=self._export_txt, state="disabled")
        self.save_button.pack(side="left")

        results = ttk.LabelFrame(outer, text="Results", padding=10)
        results.pack(fill="both", expand=True, pady=5)
        self.output = tk.Text(results, height=12, wrap="word", font=("Consolas", 10),
                              bg="#ffffff", fg="#17263b", relief="flat", padx=10, pady=10)
        scroll = ttk.Scrollbar(results, command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        self.output.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._write("Enter operating conditions and click Calculate.\n"
                    "For seawater, EC must be measured at actual water temperature.\n"
                    "Pressure must be measured at the pump suction flange.")

    def _entry(self, frame, row, label, key):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=4)
        entry = ttk.Entry(frame, textvariable=self.vars[key], width=24)
        entry.grid(row=row, column=1, sticky="ew", pady=4)
        frame.columnconfigure(1, weight=1)
        return entry

    def _combo(self, frame, row, label, key, choices):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=4)
        combo = ttk.Combobox(frame, textvariable=self.vars[key], values=choices,
                             state="readonly", width=21)
        combo.grid(row=row, column=1, sticky="ew", pady=4)
        frame.columnconfigure(1, weight=1)
        return combo

    def _update_state(self):
        gauge = self.vars["pressure_type"].get() == "gauge"
        self.atm_entry.configure(state="normal" if gauge else "disabled")

    def _sync_atmospheric_unit(self):
        """Keep atmospheric pressure physically unchanged when suction units change."""
        new_unit = self.vars["pressure_unit"].get()
        old_unit = self.vars["atmospheric_unit"].get()
        if new_unit == old_unit:
            return
        try:
            current = float(self.vars["atmospheric"].get())
            if not math.isfinite(current):
                raise ValueError("Non-finite atmospheric pressure")
            atmospheric_kpa = pressure_to_kpa(current, old_unit)
        except (ValueError, KeyError):
            atmospheric_kpa = 101.325
        converted = atmospheric_kpa / PRESSURE_TO_KPA[new_unit]
        self.vars["atmospheric"].set(f"{converted:.10g}")
        self.vars["atmospheric_unit"].set(new_unit)

    def _number(self, key, optional=False):
        value = self.vars[key].get().strip()
        if optional and not value:
            return None
        if not value:
            raise ValueError(f"Missing value: {key}")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{key} must be finite.")
        return number

    def _write(self, value):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", value)
        self.output.configure(state="disabled")

    def _clear(self):
        self.report_text = None
        self.save_button.configure(state="disabled")
        self._write("")

    def _export_txt(self):
        if self.report_text is None:
            messagebox.showwarning("No results", "Calculate NPSH before exporting.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save NPSH report",
            defaultextension=".txt",
            initialfile=f"NPSH_Report_{datetime.now():%Y%m%d_%H%M%S}.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as handle:
                handle.write(self.report_text)
            messagebox.showinfo("Export successful", "Report saved successfully.")
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))


    def _calculate(self):
        self.report_text = None
        self.save_button.configure(state="disabled")
        try:
            kind = self.vars["fluid"].get()
            t = self._number("temperature")
            ec = self._number("ec")
            flow = self._number("flow")
            diameter = self._number("diameter")
            p_entered = self._number("pressure")
            p = pressure_to_kpa(p_entered, self.vars["pressure_unit"].get())
            pt = self.vars["pressure_type"].get()
            atm = (pressure_to_kpa(self._number("atmospheric"), self.vars["atmospheric_unit"].get())
                   if pt == "gauge" else None)
            npshr = self._number("npshr", optional=True)
            p_abs = p + atm if pt == "gauge" else p
            if p_abs <= 0:
                raise ValueError("Absolute suction pressure must be positive.")
            # Seawater PSS-78 conductivity conversion uses a near-surface reference
            # pressure, not the potentially sub-atmospheric pump flange pressure.
            property_p = 0.101325 if kind == "seawater" else max(0.101325, p_abs / 1000)
            props = calculate_water_properties(
                temperature_C=t, water_type=kind, pressure_MPa_abs=property_p,
                EC_value=ec, EC_unit="mS/cm", conductivity_temperature_mode="in_situ")
            pv = props["vapor_pressure_MPa"]
            if pv is None:
                raise ValueError("Vapor pressure is not available for this state.")
            result = calculate(
                flow_m3_h=flow, diameter_mm=diameter,
                suction_pressure_kPa=p, pressure_type=pt,
                atmospheric_pressure_kPa=atm, density_kg_m3=props["density_kg_m3"],
                vapor_pressure_MPa=pv, npshr_m=npshr)
            lines = [
                f"Developed by {AUTHOR}",
                "",
                "FLUID PROPERTIES",
                f"Fluid:                 {kind}",
                f"Temperature:           {t:.2f} °C",
                f"EC:                    {ec:.3f} mS/cm",
                f"Density:               {props['density_kg_m3']:.3f} kg/m³",
                f"Dynamic viscosity:     {props['dynamic_viscosity_Pa_s']:.7g} Pa·s",
                f"Kinematic viscosity:   {props['kinematic_viscosity_m2_s']:.7g} m²/s",
                f"Vapor pressure:        {pv*1000:.5f} kPa",
            ]
            if props["absolute_salinity_g_kg"] is not None:
                lines.append(f"Reference salinity:    {props['absolute_salinity_g_kg']:.3f} g/kg")
            lines += [
                "", "SUCTION HYDRAULICS",
                f"Entered suction:       {p_entered:.5g} {self.vars['pressure_unit'].get()} ({pt})",
                f"Converted suction:     {p:.4f} kPa ({pt})",
                f"Absolute pressure:     {result['suction_pressure_absolute_kPa']:.3f} kPa",
                f"Velocity:              {result['velocity_m_s']:.4f} m/s",
                f"Velocity head:         {result['velocity_head_m']:.4f} m",
                f"Pressure head margin:  {result['pressure_margin_head_m']:.4f} m",
                "", "NPSH ASSESSMENT",
                f"NPSH Available:        {result['npsha_m']:.4f} m",
            ]
            if npshr is not None:
                lines += [f"NPSH Required:         {npshr:.4f} m",
                          f"NPSH Margin:           {result['npsh_margin_m']:.4f} m",
                          f"NPSH Ratio:            {result['npsh_ratio']:.4f}"]
            lines += ["", result["assessment"]]
            if props["warnings"]:
                lines += ["", "NOTES:"] + ["- " + w for w in props["warnings"]]
            report_lines = [
                "PUMP NPSH & CAVITATION SOLVER",
                f"Developed by {AUTHOR}",
                "=" * 54,
                f"Report generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
                "",
                "INPUT DATA",
                f"Fluid:                 {kind}",
                f"Temperature:           {t:.2f} C",
                f"EC:                    {ec:.3f} mS/cm (in-situ)",
                f"Flow rate:             {flow:.4f} m3/h",
                f"Internal diameter:     {diameter:.4f} mm",
                f"Suction pressure:      {p_entered:.6g} {self.vars['pressure_unit'].get()} ({pt})",
            ]
            if pt == "gauge":
                report_lines.append(
                    f"Atmospheric pressure:  {self._number('atmospheric'):.6g} "
                    f"{self.vars['atmospheric_unit'].get()}"
                )
            report_lines.append(
                f"NPSHr input:           {npshr:.4f} m" if npshr is not None
                else "NPSHr input:           Not provided"
            )
            report_lines += ["", "CALCULATED RESULTS", "=" * 54] + lines
            report_lines += [
                "", "CALCULATION BASIS",
                "NPSHa = (P_suction_abs - P_vapor)/(rho*g) + V^2/(2*g)",
                "g = 9.80665 m/s2; velocity coefficient alpha = 1.",
                "Pressure is measured at the pump suction flange.",
                "Suction-line losses must not be subtracted a second time.",
                "NPSHa >= NPSHr does not guarantee cavitation-free operation.",
            ]
            self.report_text = "\n".join(report_lines) + "\n"
            self._write("\n".join(lines))
            self.save_button.configure(state="normal")
        except (ValueError, ArithmeticError, ImportError, NotImplementedError) as exc:
            messagebox.showerror("Calculation error", str(exc))


if __name__ == "__main__":
    NPSHApp().mainloop()
