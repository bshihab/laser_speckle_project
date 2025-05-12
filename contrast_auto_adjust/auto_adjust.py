import cv2
import numpy as np
import matplotlib.pyplot as plt

# Load the image in grayscale
image_path =  "/Users/bilalshihab/dev/laser_speckle_project/contrast_auto_adjust/02.RawLaserSpeckle_xyz=260x214x51_t=10ms.tiff"
image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

if image is None:
    raise ValueError("Image not found or unable to load.")

# Compute the overall brightness of the image (mean pixel intensity)
brightness = np.mean(image)

# Adaptive contrast scaling factor
# Higher brightness -> lower contrast adjustment, Lower brightness -> higher contrast adjustment
contrast_scale = 1 + (128 - brightness) / 128  # Normalized adjustment

# Define window size
window_size = 7
half_window = window_size // 2

# Get image dimensions
height, width = image.shape

# Initialize contrast map
contrast_map = np.zeros((height - 2 * half_window, width - 2 * half_window))

# Compute adaptive contrast for each window
for i in range(half_window, height - half_window):
    for j in range(half_window, width - half_window):
        window = image[i - half_window:i + half_window + 1, j - half_window:j + half_window + 1]
        mean_val = np.mean(window)
        std_val = np.std(window)

        # Adjust contrast dynamically based on brightness
        contrast_value = (std_val / mean_val) * contrast_scale if mean_val != 0 else 0
        contrast_map[i - half_window, j - half_window] = contrast_value

# Normalize contrast map for visualization
contrast_map_normalized = (contrast_map - np.min(contrast_map)) / (np.max(contrast_map) - np.min(contrast_map))

# Display the contrast map with auto-adjustment
plt.figure(figsize=(8, 6))
plt.imshow(contrast_map_normalized, cmap="hot", interpolation="nearest")
plt.colorbar(label="Contrast (K) - Auto Adjusted")
plt.title(f"Speckle Contrast Map (7x7) - Auto Adjusted (Brightness = {brightness:.2f})")
plt.show()