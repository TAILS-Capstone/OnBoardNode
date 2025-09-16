import numpy as np
from filterpy.kalman import KalmanFilter

# Positional accuracy is 2.0 m radius
# Speed accuracy is 0.1 m/s


class KFDenoiser1D:
    def __init__(
        self,
        initial_value=0.0,
        initial_uncertainty=1000.0,
        measurement_noise=0.01,
        process_noise=0.1,
    ):
        """
        Initializes a one-dimensional Kalman filter for denoising numerical data.
        This filter models the state with two components:
            - The value (e.g., speed, temperature, etc.)
            - Its rate of change (velocity)
        """
        self.kf = KalmanFilter(dim_x=2, dim_z=1)
        # State vector: [value, velocity]
        self.kf.x = np.array([[initial_value], [0.0]])
        # State transition matrix: next_value = current_value + velocity; velocity assumed constant.
        self.kf.F = np.array([[1, 1], [0, 1]])
        # Measurement function: we only measure the value.
        self.kf.H = np.array([[1, 0]])
        # Initialize state covariance matrix with large uncertainty.
        self.kf.P = np.eye(2) * initial_uncertainty
        # Measurement noise covariance.
        self.kf.R = np.array([[measurement_noise]])
        # Process noise covariance.
        self.kf.Q = np.array([[process_noise, 0], [0, process_noise]])

    def update(self, measurement) -> float:
        """
        Update the Kalman filter with a single measurement.

        Parameters:
            measurement (float): A raw numerical measurement.

        Returns:
            float: The filtered value after processing the measurement.
        """
        self.kf.predict()
        self.kf.update(np.array([[measurement]]))
        return self.kf.x[0, 0]


class KFDenoiser2D:
    def __init__(
        self,
        initial_lat=0.0,
        initial_lon=0.0,
        initial_uncertainty=1000.0,
        measurement_noise=4.0,  # 2.0 m CEP roughly corresponds to 2.0 m standard deviation per axis (variance ≈ 4)
        process_noise=0.1,
    ):
        """
        Initializes a 2-dimensional Kalman filter for denoising GPS coordinates (latitude and longitude).

        The state vector is defined as:
            [latitude, latitude_velocity, longitude, longitude_velocity]
        with a constant velocity model.

        Parameters:
            initial_lat (float): Initial latitude value.
            initial_lon (float): Initial longitude value.
            initial_uncertainty (float): Initial uncertainty for the state covariance.
            measurement_noise (float): Measurement noise variance (per coordinate).
            process_noise (float): Process noise variance (applied to each state component).
        """
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        # State vector: [latitude, latitude_velocity, longitude, longitude_velocity]
        self.kf.x = np.array([[initial_lat], [0.0], [initial_lon], [0.0]])
        # Constant velocity state transition matrix:
        # latitude_new = latitude + latitude_velocity
        # latitude_velocity_new = latitude_velocity (same for longitude)
        self.kf.F = np.array([[1, 1, 0, 0], [0, 1, 0, 0], [0, 0, 1, 1], [0, 0, 0, 1]])
        # Measurement function: we measure only the latitude and longitude.
        self.kf.H = np.array([[1, 0, 0, 0], [0, 0, 1, 0]])
        # Initialize the state covariance matrix.
        self.kf.P = np.eye(4) * initial_uncertainty
        # Measurement noise covariance (R).
        # Each axis (lat, lon) is assumed to have the same noise variance.
        self.kf.R = np.eye(2) * measurement_noise
        # Process noise covariance (Q).
        self.kf.Q = np.eye(4) * process_noise

    def update(self, measurement):
        """
        Update the Kalman filter with a single GPS measurement.

        Parameters:
            measurement (tuple): A tuple (latitude, longitude) representing the raw GPS coordinates.

        Returns:
            tuple: The filtered (latitude, longitude) after processing the measurement.
        """
        # Convert the measurement into a 2x1 column vector.
        z = np.array([[measurement[0]], [measurement[1]]])
        self.kf.predict()
        self.kf.update(z)
        filtered_lat = self.kf.x[0, 0]
        filtered_lon = self.kf.x[2, 0]
        return (filtered_lat, filtered_lon)
