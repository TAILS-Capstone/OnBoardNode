from ultralytics import YOLO
import cv2

# Load the YOLOv8 model
model = YOLO('yolov8n.pt')  # Use 'yolov8n.pt' for the smallest model

# Open the webcam
cap = cv2.VideoCapture(0)  # 0 is usually the default webcam

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLOv8 inference
    results = model(frame)

    # Annotate the frame with detected objects
    annotated_frame = results[0].plot()  # This method plots the detections on the frame

    # Display the annotated frame
    cv2.imshow("YOLOv8 Detection", annotated_frame)

    # Exit with 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
