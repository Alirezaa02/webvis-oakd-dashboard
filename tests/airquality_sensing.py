# The payload must be installed on the X500UAV or similar (provided by the QUT ASL) using
# an off-the-shelf bracket (Appendix D) integrated with the UAV. It must measure and transmit
# live temperature, pressure, humidity, light, gas sensor data, and video to the web server.
# The temperature sensor must be calibrated. Sensor data must be made available in real
# time via a Web interface (dynamic website). The website must enable access to users from
# both smartphones and computers.

import colorsys
import os
import sys
import time

try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

import logging

from bme280 import BME280
from fonts.ttf import RobotoMedium as UserFont
from PIL import Image, ImageDraw, ImageFont

from enviroplus import gas

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S")

logging.info("""all-in-one.py - Displays readings from all of Enviro plus' sensors
Press Ctrl+C to exit!
""")

# BME280 temperature/pressure/humidity sensor
bme280 = BME280()

message = ""

# Get the temperature of the CPU for compensation
def get_cpu_temperature():
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp = f.read()
        temp = int(temp) / 1000.0
    return temp


# Tuning factor for compensation. Decrease this number to adjust the
# temperature down, and increase to adjust up
factor = 2.25

cpu_temps = [get_cpu_temperature()] * 5
light = 1

# 12/08/25 baselines R0 Oxidised: 3863.945578231293 R0 Reduced: 354666.66666666686 R0 nh3: 150020.06688963214
R0_Oxidised = 3863.945578231293 
R0_Reduced = 354666.66666666686
R0_nh3 = 150020.06688963214


# The main loop
try:
    while True:
        # PROXIMITY
        proximity = ltr559.get_proximity()

        # TEMPERATURE
        cpu_temp = get_cpu_temperature()
        # Smooth out with some averaging to decrease jitter
        cpu_temps = cpu_temps[1:] + [cpu_temp]
        avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
        raw_temp = bme280.get_temperature()
        temperature = raw_temp - ((avg_cpu_temp - raw_temp) / factor)

        # PRESSURE
        pressure = bme280.get_pressure()

        # HUMIDITY
        humidity = bme280.get_humidity()

        # LIGHT
        if proximity < 10:
            light = ltr559.get_lux()
        else:
            light = 1

        # GAS SENSOR
        data = gas.read_all()
        Rs_Oxidised = data.oxidising
        Rs_Reduced = data.reducing
        Rs_nh3 = data.nh3

        R_Ox = Rs_Oxidised/R0_Oxidised
        R_Re = Rs_Reduced/R0_Reduced
        R_NH3 = Rs_nh3/R0_nh3


        #Calculate Concentrations
        OX_ppm = (R_Ox/6.49)**(0.985)
        RED_ppm = (R_Re/3.574)**(-1.171)
        NH3_ppm = (R_NH3/0.787)**(-1.859)
        
        # #Calculate Concentrations
        # OX_ppm = Rs_Oxidised/(5*R0_Oxidised)
        # RED_ppm = (Rs_Reduced/(13.6*R0_Reduced))**(-1.6949)
        # NH3_ppm = (Rs_nh3/(2.043*R0_nh3))**(-1.537)
        
        logging.info(f"Temperature {temperature} °C")
        logging.info(f"Pressure {pressure} hPa")
        logging.info(f"Humidity {humidity} %")
        logging.info(f"Light {light} lux")
        logging.info(f"oxidised {OX_ppm} ppm")
        logging.info(f"reduced {RED_ppm} ppm")
        logging.info(f"nh3 {NH3_ppm} ppm")

        time.sleep(0.979)

# Exit cleanly
except KeyboardInterrupt:
    sys.exit(0)
