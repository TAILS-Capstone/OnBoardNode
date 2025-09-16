import lgpio
import config
import math
import time
from micropyGPS import MicropyGPS
import srtm

g = MicropyGPS(+8)
Temp = "0123456789ABCDEF*"
BUFFSIZE = 1100

pi = 3.14159265358979324
a = 6378245.0
ee = 0.00669342162296594323
x_pi = 3.14159265358979324 * 3000.0 / 180.0


class L76X(object):
    Lon = 0.0
    Lat = 0.0
    Lon_area = "E"
    Lat_area = "W"
    Time_H = 0
    Time_M = 0
    Time_S = 0
    Status = 0
    Lon_Baidu = 0.0
    Lat_Baidu = 0.0
    Lon_Google = 0.0
    Lat_Google = 0.0
    elevation_above_ground = 0.0
    speed = 0.0
    course = 0.0

    # Note: The transform functions use the names "Lon_Goodle" and "Lat_Goodle"
    # to remain consistent with the original code logic.
    GPS_Lon = 0
    GPS_Lat = 0

    # Startup mode commands
    SET_HOT_START = "$PMTK101"
    SET_WARM_START = "$PMTK102"
    SET_COLD_START = "$PMTK103"
    SET_FULL_COLD_START = "$PMTK104"

    # Standby mode -- Exit requires high level trigger
    SET_PERPETUAL_STANDBY_MODE = "$PMTK161"

    SET_PERIODIC_MODE = "$PMTK225"
    SET_NORMAL_MODE = "$PMTK225,0"
    SET_PERIODIC_BACKUP_MODE = "$PMTK225,1,1000,2000"
    SET_PERIODIC_STANDBY_MODE = "$PMTK225,2,1000,2000"
    SET_PERPETUAL_BACKUP_MODE = "$PMTK225,4"
    SET_ALWAYSLOCATE_STANDBY_MODE = "$PMTK225,8"
    SET_ALWAYSLOCATE_BACKUP_MODE = "$PMTK225,9"

    # Set the message interval, 100ms~10000ms
    SET_POS_FIX = "$PMTK220"
    SET_POS_FIX_100MS = "$PMTK220,100"
    SET_POS_FIX_200MS = "$PMTK220,200"
    SET_POS_FIX_400MS = "$PMTK220,400"
    SET_POS_FIX_800MS = "$PMTK220,800"
    SET_POS_FIX_1S = "$PMTK220,1000"
    SET_POS_FIX_2S = "$PMTK220,2000"
    SET_POS_FIX_4S = "$PMTK220,4000"
    SET_POS_FIX_8S = "$PMTK220,8000"
    SET_POS_FIX_10S = "$PMTK220,10000"

    # Switching time output
    SET_SYNC_PPS_NMEA_OFF = "$PMTK255,0"
    SET_SYNC_PPS_NMEA_ON = "$PMTK255,1"

    # To restore the system default setting
    SET_REDUCTION = "$PMTK314,-1"

    # Set NMEA sentence output frequencies
    SET_NMEA_OUTPUT = "$PMTK314,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,0"
    # Baud rate commands
    SET_NMEA_BAUDRATE = "$PMTK251"
    SET_NMEA_BAUDRATE_115200 = "$PMTK251,115200"
    SET_NMEA_BAUDRATE_57600 = "$PMTK251,57600"
    SET_NMEA_BAUDRATE_38400 = "$PMTK251,38400"
    SET_NMEA_BAUDRATE_19200 = "$PMTK251,19200"
    SET_NMEA_BAUDRATE_14400 = "$PMTK251,14400"
    SET_NMEA_BAUDRATE_9600 = "$PMTK251,9600"
    SET_NMEA_BAUDRATE_4800 = "$PMTK251,4800"

    def __init__(self):
        self.config = config.config(9600)
        self._gpio_handle = None  # Will hold the input-mode handle if needed

    def L76X_Send_Command(self, data):
        Check = ord(data[1])
        for i in range(2, len(data)):
            Check = Check ^ ord(data[i])
        data = data + Temp[16]
        data = data + Temp[(Check // 16)]
        data = data + Temp[(Check % 16)]
        self.config.Uart_SendString(data.encode())
        self.config.Uart_SendByte("\r".encode())
        self.config.Uart_SendByte("\n".encode())
        # print(data)

    def get_gps_data(self, elevation_data):
        data = ""
        while True:
            if g.valid:
                self.Status = 1
            else:
                self.Status = 0
            x = self.config.Uart_ReceiveByte()
            if x == b"$":
                while x != b"\r":
                    data += x.decode()
                    g.update(x.decode())
                    x = self.config.Uart_ReceiveByte()
                data += "\r\n"
                if "$GNGLL" in data:
                    break
        self.Lat = g.latitude[0] + g.latitude[1] / 60
        self.Lon = g.longitude[0] + g.longitude[1] / 60
        if g.latitude[2] != "N":
            self.Lat = -self.Lat
        if g.longitude[2] != "E":
            self.Lon = -self.Lon
        self.Time_H = g.timestamp[0]
        self.Time_M = g.timestamp[1]
        self.Time_S = g.timestamp[2]

        ground_elevation = elevation_data.get_elevation(self.Lat, self.Lon)

        # print("Altitude ", g.altitude)
        # print("Ground elevation ", ground_elevation)

        if ground_elevation:
            self.elevation_above_ground = g.altitude - elevation_data.get_elevation(
                self.Lat, self.Lon
            )
        self.speed = g.speed[2]
        self.course = g.course
        # print(data)
        data = "\r\n"

    def transformLat(self, x, y):
        ret = (
            -100.0
            + 2.0 * x
            + 3.0 * y
            + 0.2 * y * y
            + 0.1 * x * y
            + 0.2 * math.sqrt(abs(x))
        )
        ret += (
            (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        )
        ret += (20.0 * math.sin(y * pi) + 40.0 * math.sin(y / 3.0 * pi)) * 2.0 / 3.0
        ret += (
            (160.0 * math.sin(y / 12.0 * pi) + 320 * math.sin(y * pi / 30.0))
            * 2.0
            / 3.0
        )
        return ret

    def transformLon(self, x, y):
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (
            (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        )
        ret += (20.0 * math.sin(x * pi) + 40.0 * math.sin(x / 3.0 * pi)) * 2.0 / 3.0
        ret += (
            (150.0 * math.sin(x / 12.0 * pi) + 300.0 * math.sin(x / 30.0 * pi))
            * 2.0
            / 3.0
        )
        return ret

    def bd_encrypt(self):
        # Using the same variable names as in the original code.
        x = self.Lon_Goodle
        y = self.Lat_Goodle
        z = math.sqrt(x * x + y * y) + 0.00002 * math.sin(y * x_pi)
        theta = math.atan2(y, x) + 0.000003 * math.cos(x * x_pi)
        self.Lon_Baidu = z * math.cos(theta) + 0.0065
        self.Lat_Baidu = z * math.sin(theta) + 0.006

    def transform(self):
        dLat = self.transformLat(self.GPS_Lon - 105.0, self.GPS_Lat - 35.0)
        dLon = self.transformLon(self.GPS_Lon - 105.0, self.GPS_Lat - 35.0)
        radLat = self.GPS_Lat / 180.0 * pi
        magic = math.sin(radLat)
        magic = 1 - ee * magic * magic
        sqrtMagic = math.sqrt(magic)
        dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * pi)
        dLon = (dLon * 180.0) / (a / sqrtMagic * math.cos(radLat) * pi)
        # Retain the original variable naming "Goodle"
        self.Lat_Goodle = self.GPS_Lat + dLat
        self.Lon_Goodle = self.GPS_Lon + dLon

    def L76X_Baidu_Coordinates(self, U_Lat, U_Lon):
        self.GPS_Lat = (U_Lat % 1) * 100 / 60 + math.floor(U_Lat)
        self.GPS_Lon = (U_Lon % 1) * 100 / 60 + math.floor(U_Lon)
        self.transform()
        self.bd_encrypt()

    def L76X_Google_Coordinates(self, U_Lat, U_Lon):
        self.GPS_Lat = (U_Lat % 1) / 60 + U_Lat
        self.GPS_Lon = (U_Lon % 1) / 60 + U_Lon
        self.transform()

    def L76X_Set_Baudrate(self, Baudrate):
        self.config.Uart_Set_Baudrate(Baudrate)

    def L76X_Exit_BackupMode(self):
        # Replace RPi.GPIO calls with lgpio functions.
        # Assume self.config.FORCE holds the BCM pin number to be toggled.
        line = self.config.FORCE

        # Claim the pin as output and toggle it.
        self._gpio_handle = self.config.get_handler()
        lgpio.gpio_claim_output(
            self._gpio_handle, line, 0
        )  # Set as output, initial value low
        time.sleep(1)
        lgpio.gpio_write(self._gpio_handle, line, 1)  # Drive high
        time.sleep(1)
        lgpio.gpio_write(self._gpio_handle, line, 0)  # Drive low
        time.sleep(1)
        lgpio.gpiochip_close(
            self._gpio_handle
        )  # This releases the output configuration
