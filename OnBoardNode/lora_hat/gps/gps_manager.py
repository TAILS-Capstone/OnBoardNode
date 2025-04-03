import L76X
import srtm
from typing import Tuple, Optional

class GPSManager:
    def __init__(self):
        self.gps = L76X.L76X()
        self.gps.L76X_Set_Baudrate(9600)
        self.gps.L76X_Send_Command(self.gps.SET_POS_FIX_400MS)
        self.gps.L76X_Send_Command(self.gps.SET_NMEA_OUTPUT)
        self.elevation_data = srtm.get_data()
        self.gps.L76X_Exit_BackupMode()

    def get_current_location(self) -> Tuple[float, float, float]:
        """
        Get the current GPS location and elevation
        Returns:
            Tuple[float, float, float]: (latitude, longitude, elevation)
        """
        self.gps.get_gps_data(self.elevation_data)
        return (self.gps.Lat, self.gps.Lon, self.gps.elevation_above_ground)

    def get_speed_and_course(self) -> Tuple[float, float]:
        """
        Get the current speed and course
        Returns:
            Tuple[float, float]: (speed, course)
        """
        return (self.gps.speed, self.gps.course)

    @property
    def is_positioned(self) -> bool:
        """
        Check if GPS has position fix
        Returns:
            bool: True if positioned, False otherwise
        """
        return self.gps.Status == 1 