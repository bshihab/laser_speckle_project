import numpy as np
import matplotlib.pyplot as plt

# Define image properties (Set according to your camera settings)
width = 1920   # Set your camera's width
height = 1200  # Set your camera's height
dtype = np.uint8  # Use np.uint16 if it's a 16-bit image

# Load raw binary image data
with open("captured_image.raw", "rb") as f:
    img_array = np.frombuffer(f.read(), dtype=dtype)

# Reshape the array to match the image dimensions
img_array = img_array.reshape((height, width))

# Display the image
plt.imshow(img_array, cmap="gray")
plt.title("Loaded RAW Image ff")
plt.axis("off")
plt.show()