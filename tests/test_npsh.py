import unittest
from core.npsh import calculate
from core.water_properties import seawater_vapor_pressure_MPa

class TestNPSH(unittest.TestCase):
    def test_pressure_equal_vapor(self):
        r=calculate(flow_m3_h=360, diameter_mm=112.8379167,
            suction_pressure_kPa=5, pressure_type="absolute",
            density_kg_m3=1000, vapor_pressure_MPa=0.005)
        self.assertAlmostEqual(r["pressure_margin_head_m"],0,places=7)
        self.assertAlmostEqual(r["npsha_m"],r["velocity_head_m"],places=7)
    def test_gauge(self):
        r=calculate(flow_m3_h=0,diameter_mm=100,suction_pressure_kPa=0,
            pressure_type="gauge",atmospheric_pressure_kPa=101.325,
            density_kg_m3=1000,vapor_pressure_MPa=0.003)
        self.assertAlmostEqual(r["suction_pressure_absolute_kPa"],101.325)
    def test_vapor_reduction(self):
        self.assertLess(seawater_vapor_pressure_MPa(30,35),seawater_vapor_pressure_MPa(30,0))

if __name__=="__main__": unittest.main()
