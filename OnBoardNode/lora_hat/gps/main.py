import L76X
import time
import srtm
from denoise import KFDenoiser1D, KFDenoiser2D

# NOTE: Performance of the GPS seems to be better without denoising

try:
    gps = L76X.L76X()
    gps.L76X_Set_Baudrate(9600)
    gps.L76X_Send_Command(gps.SET_POS_FIX_400MS)
    gps.L76X_Send_Command(gps.SET_NMEA_OUTPUT)
    # gps.L76X_Send_Command(gps.SET_FULL_COLD_START)

    elevation_data = srtm.get_data()

    gps.L76X_Exit_BackupMode()

    # Initialize the CSV file with header for coordinates.
    with open("coordinates.csv", "w") as file:
        file.write("latitude,longitude\n")

    # Create Kalman filter denoisers for speed and coordinates.
    # For speed: sensor accuracy is 0.1 m/s, so measurement variance = 0.1² = 0.01.
    speed_denoiser = KFDenoiser1D(initial_value=0.0, measurement_noise=0.01)
    # For coordinates: 2.0 m CEP roughly corresponds to a standard deviation of ~2.0 m per axis,
    # so variance ≈ 4.0 (assuming independent errors in latitude and longitude).
    pos_denoiser = KFDenoiser2D(initial_lat=0.0, initial_lon=0.0, measurement_noise=4.0)

    while True:
        gps.get_gps_data(elevation_data)

        if gps.Status == 1:
            print("Already positioned")
        else:
            print("No positioning")

        # Print the time
        print("Time: {:02}:{:02}:{:02}".format(gps.Time_H, gps.Time_M, int(gps.Time_S)))

        # Print raw GPS data
        print("Raw Lat = %f, Raw Lon = %f" % (gps.Lat, gps.Lon))
        print("Raw Speed = %f" % gps.speed)

        # Denoise the coordinates and speed using the Kalman filters
        denoised_coords = pos_denoiser.update((gps.Lat, gps.Lon))
        denoised_speed = speed_denoiser.update(gps.speed)

        # Print denoised values
        print(
            "Denoised Lat = %f, Denoised Lon = %f"
            % (denoised_coords[0], denoised_coords[1])
        )
        print("Denoised Speed = %f" % denoised_speed)
        print("Course = %f" % gps.course)
        print("Elevation above ground = %f" % gps.elevation_above_ground)
        print("------------------------------")

        # Append denoised coordinates to the CSV file.
        with open("coordinates.csv", "a") as file:
            file.write(f"{gps.Lat},{gps.Lon}\n")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nProgram end")
    exit()
