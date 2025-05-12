import cv2
import matplotlib.pyplot as plt
from pypylon import pylon

# Create an instant camera object with the first available camera
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

# try:
#     camera.ExposureTime.SetValue(5000000)  # 500ms
#     print("Exposure time set to 500ms.")
# except Exception as e:
#     print(f"Failed to set ExposureTime: {e}")

  
# Open the camera
camera.Open()

# Print camera information
print(f"Camera Model: {camera.GetDeviceInfo().GetModelName()}")
print(f"Serial Number: {camera.GetDeviceInfo().GetSerialNumber()}")

# # grab one image with a timeout of 1s
# # returns a GrabResult, which is the image plus metadata
# res = camera.GrabOne(50) # ms

# # the raw memory of the image
# res.GetBuffer()[:100]

# # full method call
# img = res.GetArray()

# img.tofile("captured_image_500ms.raw")

# plt.imshow(img, cmap='gray', vmin=0, vmax=255)
# plt.show()

exposures = [1000, 10000,50000, 200000, 500000, 1000000]  # 1ms, 50ms, 500ms

for exp in exposures:
    camera.ExposureTime.SetValue(exp)
    print(f"Set Exposure Time: {exp} µs")

    res = camera.GrabOne(5000)  # Capture image
    img = res.GetArray()

    img.tofile("captured_image_" + str(exp) + "us.raw")

    # Display the image
    import matplotlib.pyplot as plt
    plt.imshow(img, cmap="gray", vmin=0, vmax=255)
    plt.title(f"Exposure: {exp} µs")
    plt.show()

res.Release()
# Close the camera
camera.Close()





# Capture an image
# image = camera.GrabOne()

# Convert the image to a numpy array
