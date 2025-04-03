import time
import L76X
import srtm
from typing import Tuple

class GPSManager:
    def __init__(self, update_threshold: float = 1.0):
        self.gps = L76X.L76X()
        self.gps.L76X_Set_Baudrate(9600)
        self.gps.L76X_Send_Command(self.gps.SET_POS_FIX_400MS)
        self.gps.L76X_Send_Command(self.gps.SET_NMEA_OUTPUT)
        self.elevation_data = srtm.get_data()
        self.gps.L76X_Exit_BackupMode()
        
        # Threshold in seconds between GPS updates
        self.update_threshold = update_threshold
        self.last_update_time = 1
        self.last_location: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def get_current_location(self) -> Tuple[float, float, float]:
        """
        Get the current GPS location and elevation.
        If the time since the last update is less than the threshold,
        return cached data; otherwise, poll the GPS module for new data.
        
        Returns:
            Tuple[float, float, float]: (latitude, longitude, elevation)
        """
        current_time = time.time()
        if (current_time - self.last_update_time) < self.update_threshold and self.last_update_time != 0.0:
            return self.last_location
        else:
            self.gps.get_gps_data(self.elevation_data)
            self.last_location = (self.gps.Lat, self.gps.Lon, self.gps.elevation_above_ground)
            self.last_update_time = current_time
            return self.last_location

    def get_speed_and_course(self) -> Tuple[float, float]:
        """
        Get the current speed and course.
        
        Returns:
            Tuple[float, float]: (speed, course)
        """
        return (self.gps.speed, self.gps.course)

    @property
    def is_positioned(self) -> bool:
        """
        Check if the GPS has a position fix.
        
        Returns:
            bool: True if positioned, False otherwise.
        """
        return self.gps.Status == 1
