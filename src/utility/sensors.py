import os
from bme280 import BME280
from enviroplus import gas
try:
    from ltr559 import LTR559
    _ltr = LTR559()
except ImportError:
    import ltr559 as _ltr  # fallback to module API

_bme = BME280()

# Tuning factor for compensation. Decrease this number to adjust the
# temperature down, and increase to adjust up
factor = 2

light = 1

# 12/08/25 baselines R0 Oxidised: 3863.945578231293 R0 Reduced: 354666.66666666686 R0 nh3: 150020.06688963214
R0_Oxidised = 3863.945578231293 
R0_Reduced = 354666.66666666686
R0_nh3 = 150020.06688963214

def cpu_temp_c() -> float:
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        return int(f.read()) / 1000.0

def proximity() -> int:
    return _ltr.get_proximity()

def light_lux() -> float:
    return _ltr.get_lux()

def bme_temperature_c() -> float:
    return _bme.get_temperature()

def bme_pressure_hpa() -> float:
    return _bme.get_pressure()

def bme_humidity_pct() -> float:
    return _bme.get_humidity()

def gas_read_all():
    return gas.read_all()  # has .oxidising, .reducing, .nh3 (Ohms)

def get_all_sensor_data(CPU_TEMPS) -> dict:
    # PROXIMITY
    proximity_sens = proximity()

    # TEMPERATURE
    cpu_temp = cpu_temp_c()
    # Smooth out with some averaging to decrease jitter
    CPU_TEMPS = CPU_TEMPS[1:] + [cpu_temp]
    avg_cpu_temp = sum(CPU_TEMPS) / float(len(CPU_TEMPS))
    raw_temp = bme_temperature_c()
    temperature = raw_temp - ((avg_cpu_temp - raw_temp) / factor)

    # PRESSURE
    pressure = bme_pressure_hpa()

    # HUMIDITY
    humidity = bme_humidity_pct()

    # LIGHT
    if proximity_sens < 10:
        light = light_lux()
    else:
        light = 1

    # GAS SENSOR
    gas_data = gas_read_all()
    Rs_Oxidised = gas_data.oxidising
    Rs_Reduced = gas_data.reducing
    Rs_nh3 = gas_data.nh3

    R_Ox = Rs_Oxidised/R0_Oxidised
    R_Re = Rs_Reduced/R0_Reduced
    R_NH3 = Rs_nh3/R0_nh3

    if R_Ox == 0:
        R_Ox = 0.001
    if R_Re == 0:
        R_Re = 0.001
    if R_NH3 == 0:
        R_NH3 = 0.001

    #Calculate Concentrations
    OX_ppm = (R_Ox/6.49)**(0.985)
    RED_ppm = (R_Re/3.574)**(-1.171)
    NH3_ppm = (R_NH3/0.787)**(-1.859)

    data = {
        "Temperature": temperature,
        "Light": light,
        "Pressure": pressure,
        "Humidity": humidity,
        "Oxidising": OX_ppm,
        "Reducing": RED_ppm,
        "NH3": NH3_ppm
    }
    return data
