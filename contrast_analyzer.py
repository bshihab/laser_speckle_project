import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
import os
import time
from datetime import datetime

def read_raw_image(file_path, width=None, height=None, dtype=np.uint16):
    """
    Read a raw image file.
    
    Args:
        file_path: Path to the raw image file
        width: Width of the image (must be provided for raw files)
        height: Height of the image (must be provided for raw files)
        dtype: Data type of the image (default: np.uint16 for 16-bit images)
    
    Returns:
        numpy array containing the image data
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Determine image dimensions if not provided
    if width is None or height is None:
        # Try to infer from filename or use default values
        if width is None:
            width = 960  # Default width
        if height is None:
            height = 1200  # Default height
    
    # Fix for duplicated images - if width is 1920, reduce to 960
    if width == 1920:
        print("Applying automatic fix for duplicated images (using width=960 instead of 1920)")
        width = 960
    
    # Calculate bytes per pixel based on dtype
    bytes_per_pixel = np.dtype(dtype).itemsize
    
    # Check if file size matches expected dimensions
    expected_size = width * height * bytes_per_pixel
    if len(data) != expected_size:
        print(f"Warning: File size ({len(data)} bytes) doesn't match expected dimensions "
              f"({width}x{height}, {bytes_per_pixel} bytes per pixel = {expected_size} bytes)")
        # Try to adjust dimensions based on file size
        total_pixels = len(data) // bytes_per_pixel
        if width is not None and width > 0:
            height = total_pixels // width
        elif height is not None and height > 0:
            width = total_pixels // height
        else:
            # If both dimensions are unknown, assume a square image
            width = height = int(np.sqrt(total_pixels))
        print(f"Adjusted dimensions to {width}x{height}")
    
    # Convert raw data to numpy array
    img = np.frombuffer(data, dtype=dtype).reshape(height, width)
    
    return img

def create_radial_weight_mask(img_shape, center=None, sigma=None):
    """
    Create a radial weight mask that gives more weight to the center of the image.
    
    Args:
        img_shape: Shape of the image (height, width)
        center: Center coordinates (y, x), defaults to the center of the image
        sigma: Standard deviation of the Gaussian weighting, defaults to 1/6 of the shortest dimension
    
    Returns:
        2D numpy array with Gaussian weights (highest at center)
    """
    height, width = img_shape
    
    if center is None:
        center = (height // 2, width // 2)
    
    if sigma is None:
        sigma = min(height, width) // 6  # Using 1/6 of the shortest dimension for focused center weighting
    
    y, x = np.ogrid[:height, :width]
    y_dist = ((y - center[0]) ** 2)
    x_dist = ((x - center[1]) ** 2)
    dist_from_center = np.sqrt(y_dist + x_dist)
    
    # Create Gaussian weight mask (highest at center)
    weight_mask = np.exp(-0.5 * (dist_from_center / sigma) ** 2)
    
    # Further emphasize center by applying power function
    weight_mask = weight_mask ** 2
    
    # Normalize weights to [0, 1]
    weight_mask = weight_mask / weight_mask.max()
    
    return weight_mask

def analyze_contrast(img, window_size=7, weight_sigma=None, weight_mask=None):
    """
    Analyze speckle contrast (σ/μ) with window-based approach and weight mask.
    
    Args:
        img: Image as numpy array
        window_size: Size of the sliding window for local contrast calculation
        weight_sigma: Standard deviation for the radial weight mask, if None uses default
        weight_mask: Custom weight mask, if provided will override the auto-generated mask
    
    Returns:
        Dictionary containing contrast analysis results
    """
    # Scale to 8-bit for visualization
    if img.dtype == np.uint16:
        img_8bit = (img / 256).astype(np.uint8)
    else:  # Assume uint8
        img_8bit = img.copy()
    
    # Create or use provided weight mask
    if weight_mask is None:
        weight_mask = create_radial_weight_mask(img.shape, sigma=weight_sigma)
    
    # Calculate global contrast (standard deviation / mean)
    # Apply weighting to calculations
    flat_img = img.flatten()
    flat_weights = weight_mask.flatten()
    
    # Calculate weighted mean
    weighted_mean = np.average(flat_img, weights=flat_weights)
    
    # Calculate weighted standard deviation
    weighted_variance = np.average((flat_img - weighted_mean)**2, weights=flat_weights)
    weighted_std = np.sqrt(weighted_variance)
    
    # Calculate global contrast ratio
    global_contrast = weighted_std / weighted_mean if weighted_mean > 0 else 0
    
    # Calculate local contrast map using sliding window
    half_window = window_size // 2
    height, width = img.shape
    contrast_map = np.zeros_like(img, dtype=np.float32)
    
    # Pad the image to handle edges
    padded_img = np.pad(img, half_window, mode='reflect')
    
    # Slide window over image and calculate local contrast
    for y in range(height):
        for x in range(width):
            # Extract window
            window = padded_img[y:y+window_size, x:x+window_size]
            
            # Calculate local contrast
            local_mean = np.mean(window)
            if local_mean > 0:
                local_std = np.std(window)
                contrast_map[y, x] = local_std / local_mean
            else:
                contrast_map[y, x] = 0
    
    # Apply weight mask to contrast map to focus on ROI
    weighted_contrast_map = contrast_map * weight_mask
    
    # Calculate contrast statistics
    mean_contrast = np.mean(contrast_map)
    median_contrast = np.median(contrast_map)
    weighted_mean_contrast = np.average(contrast_map.flatten(), weights=flat_weights)
    
    # Evaluate contrast quality based on common thresholds for speckle
    # Optimal contrast for biological tissue typically ranges from 0.15 to 0.6
    low_contrast_threshold = 0.15
    high_contrast_threshold = 0.6
    
    # Count pixels in different contrast ranges
    low_contrast_count = np.sum((contrast_map < low_contrast_threshold) * weight_mask)
    optimal_contrast_count = np.sum(((contrast_map >= low_contrast_threshold) & 
                                    (contrast_map <= high_contrast_threshold)) * weight_mask)
    high_contrast_count = np.sum((contrast_map > high_contrast_threshold) * weight_mask)
    
    # Calculate percentages
    total_weight = np.sum(weight_mask)
    low_contrast_percentage = (low_contrast_count / total_weight) * 100
    optimal_contrast_percentage = (optimal_contrast_count / total_weight) * 100
    high_contrast_percentage = (high_contrast_count / total_weight) * 100
    
    # Determine if contrast is in optimal range
    is_optimal_contrast = (weighted_mean_contrast >= low_contrast_threshold and 
                          weighted_mean_contrast <= high_contrast_threshold)
    
    # Create visualization map
    contrast_vis_map = np.zeros((*img.shape, 3), dtype=np.uint8)
    
    # Base layer - grayscale image
    for i in range(3):
        contrast_vis_map[:, :, i] = img_8bit
    
    # Create normalized contrast map for visualization (0-255)
    norm_contrast_map = np.clip(contrast_map * 255 / high_contrast_threshold, 0, 255).astype(np.uint8)
    
    # Apply colormap to contrast values
    # Red: high contrast, Green: optimal contrast, Blue: low contrast
    low_mask = contrast_map < low_contrast_threshold
    optimal_mask = (contrast_map >= low_contrast_threshold) & (contrast_map <= high_contrast_threshold)
    high_mask = contrast_map > high_contrast_threshold
    
    # Apply with alpha blending for visualization
    alpha = 0.5
    contrast_vis_map[:, :, 0][high_mask] = int(255 * alpha) + contrast_vis_map[:, :, 0][high_mask] * (1 - alpha)  # Red
    contrast_vis_map[:, :, 1][optimal_mask] = int(255 * alpha) + contrast_vis_map[:, :, 1][optimal_mask] * (1 - alpha)  # Green
    contrast_vis_map[:, :, 2][low_mask] = int(255 * alpha) + contrast_vis_map[:, :, 2][low_mask] * (1 - alpha)  # Blue
    
    # Apply weight mask as a subtle overlay to show ROI
    alpha_weight = 0.2
    green_tint = (weight_mask * 255 * alpha_weight).astype(np.uint8)
    contrast_vis_map[:, :, 1] = np.minimum(255, contrast_vis_map[:, :, 1] + green_tint)
    
    # Compile results
    return {
        "image_shape": img.shape,
        "global_contrast": global_contrast,
        "mean_contrast": mean_contrast,
        "median_contrast": median_contrast,
        "weighted_mean_contrast": weighted_mean_contrast,
        "low_contrast_percentage": low_contrast_percentage,
        "optimal_contrast_percentage": optimal_contrast_percentage,
        "high_contrast_percentage": high_contrast_percentage,
        "is_optimal_contrast": is_optimal_contrast,
        "contrast_map": contrast_map,
        "weighted_contrast_map": weighted_contrast_map,
        "weight_mask": weight_mask,
        "img_8bit": img_8bit,
        "contrast_vis_map": contrast_vis_map,
        "window_size": window_size,
        "low_contrast_threshold": low_contrast_threshold,
        "high_contrast_threshold": high_contrast_threshold
    }

def plot_results(img, results, image_path, save_output=True):
    """
    Plot contrast analysis results.
    
    Args:
        img: Original image as numpy array
        results: Dictionary containing analysis results
        image_path: Path to save results or None if no saving is required
        save_output: Whether to save output to disk
    """
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot original image
    ax1 = axs[0, 0]
    if img.dtype == np.uint16:
        ax1.imshow(results["img_8bit"], cmap='gray', vmin=0, vmax=255)
    else:
        ax1.imshow(img, cmap='gray', vmin=0, vmax=255)
    
    ax1.set_title(f"Original Image\n{Path(image_path).name}")
    ax1.axis('off')
    
    # Plot contrast visualization map
    ax2 = axs[0, 1]
    contrast_map = ax2.imshow(results["contrast_vis_map"], cmap='jet', vmin=0, vmax=1.0)
    
    # Add colorbar
    cbar = plt.colorbar(contrast_map, ax=ax2, orientation='vertical', pad=0.01)
    cbar.set_label('Contrast Value', rotation=270, labelpad=15)
    
    # Add legend for contrast ranges
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    
    legend_elements = [
        Patch(facecolor='blue', edgecolor='none', label='Low Contrast (<0.15)\nIncrease Current by 10%'),
        Patch(facecolor='cyan', edgecolor='none', label='Medium-Low (0.15-0.25)\nIncrease Current by 5%'),
        Patch(facecolor='green', edgecolor='none', label='Optimal (0.25-0.45)\nMaintain Current'),
        Patch(facecolor='yellow', edgecolor='none', label='Medium-High (0.45-0.6)\nMaintain Current'),
        Patch(facecolor='red', edgecolor='none', label='High Contrast (>0.6)\nDecrease Current by 20%')
    ]
    
    # Place legend below the plot
    ax2.legend(handles=legend_elements, loc='upper center', 
              bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize='small')
              
    ax2.set_title(f"Contrast Map\nMean={results['mean_contrast']:.3f}")
    ax2.axis('off')
    
    # Plot histogram of contrast values
    ax3 = axs[1, 0]
    bins = np.linspace(0, 1, 50)
    n, bins, patches = ax3.hist(results["contrast_values"].flatten(), bins=bins, 
                              alpha=0.7, color='blue', weights=results["weight_values"].flatten())
    
    # Add vertical lines for optimal range and mean
    ax3.axvline(x=0.15, color='blue', linestyle='--', label='Low Threshold (0.15)')
    ax3.axvline(x=0.25, color='cyan', linestyle='--', label='Medium-Low Threshold (0.25)')
    ax3.axvline(x=0.45, color='green', linestyle='--', label='Medium Threshold (0.45)')
    ax3.axvline(x=0.6, color='red', linestyle='--', label='High Threshold (0.6)')
    ax3.axvline(x=results["mean_contrast"], color='black', linestyle='-', label=f'Mean ({results["mean_contrast"]:.3f})')
    
    ax3.set_title("Weighted Histogram of Contrast Values")
    ax3.set_xlabel("Contrast Value")
    ax3.set_ylabel("Frequency (weighted)")
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Display text summary of results
    ax4 = axs[1, 1]
    ax4.axis('off')
    
    # Determine status based on mean contrast
    mean_contrast = results["mean_contrast"]
    if mean_contrast < 0.15:
        status = "LOW CONTRAST"
        color = "blue"
        recommendation = "INCREASE laser current by 10%"
        arduino_code = "current_value *= 1.1; // Increase by 10%"
    elif mean_contrast < 0.25:
        status = "SLIGHTLY LOW CONTRAST"
        color = "cyan"
        recommendation = "INCREASE laser current by 5%"
        arduino_code = "current_value *= 1.05; // Increase by 5%"
    elif mean_contrast > 0.6:
        status = "HIGH CONTRAST"
        color = "red"
        recommendation = "DECREASE laser current by 20%"
        arduino_code = "current_value *= 0.8; // Decrease by 20%"
    else:
        status = "OPTIMAL CONTRAST"
        color = "green"
        recommendation = "MAINTAIN current laser settings"
        arduino_code = "// No change needed, contrast is optimal"
    
    # Results text
    text = (
        f"CONTRAST ANALYSIS RESULTS:\n\n"
        f"Mean Contrast: {results['mean_contrast']:.3f}\n"
        f"Median Contrast: {results['median_contrast']:.3f}\n"
        f"Low Contrast Percentage: {results['low_contrast_percentage']:.1f}%\n"
        f"High Contrast Percentage: {results['high_contrast_percentage']:.1f}%\n"
        f"Optimal Contrast Percentage: {results['optimal_contrast_percentage']:.1f}%\n\n"
        f"Status: {status}\n\n"
        f"Recommendation: {recommendation}\n\n"
        f"Arduino Implementation:\n"
        f"{arduino_code}\n\n"
        f"Color Key:\n"
        f"• Blue: Low contrast (<0.15) - Increase current\n"
        f"• Cyan: Medium-low contrast (0.15-0.25) - Slight increase\n"
        f"• Green: Optimal contrast (0.25-0.45) - Maintain\n"
        f"• Yellow: Medium-high contrast (0.45-0.6) - Maintain\n"
        f"• Red: High contrast (>0.6) - Decrease current"
    )
    
    ax4.text(0, 1.0, text, va='top', fontsize=10, 
             bbox=dict(boxstyle="round,pad=0.5", facecolor=f"{color}", alpha=0.3))
    
    plt.tight_layout()
    
    # Save if requested and path is provided
    if save_output and image_path is not None:
        # Create output directory if it doesn't exist
        output_dir = Path(os.path.dirname(image_path))
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Save figure
        plt.savefig(image_path)
        print(f"Analysis saved to {image_path}")
    
    return fig

def assess_contrast_quality(median_contrast):
    """
    Assess the quality of the contrast and provide recommendations.
    
    Args:
        median_contrast: Median contrast value
        
    Returns:
        Dictionary with contrast assessment information
    """
    # Define optimal contrast range
    optimal_min = 0.15
    optimal_max = 0.25
    
    result = {
        "target_min": optimal_min,
        "target_max": optimal_max
    }
    
    # Determine contrast status
    if median_contrast < optimal_min:
        result["status"] = "too_low"
        # Calculate severity (0.0-1.0) based on how far from optimal
        result["severity"] = min(1.0, (optimal_min - median_contrast) / optimal_min)
    elif median_contrast > optimal_max:
        result["status"] = "too_high"
        # Calculate severity (0.0-1.0) based on how far from optimal
        result["severity"] = min(1.0, (median_contrast - optimal_max) / optimal_max)
    else:
        result["status"] = "optimal"
        result["severity"] = 0.0
    
    return result

def suggest_improvements(results):
    """
    Suggest improvements based on contrast analysis.
    
    Args:
        results: Dictionary containing analysis results
    
    Returns:
        String with suggestions
    """
    suggestions = []
    
    # Check if contrast is too low
    if results["weighted_mean_contrast"] < results["low_contrast_threshold"]:
        suggestions.append("Contrast is too low. Consider the following:")
        suggestions.append("- Increase laser power/current")
        suggestions.append("- Optimize imaging aperture (smaller aperture increases speckle contrast)")
        suggestions.append("- Check for motion blur or vibration affecting speckle")
        suggestions.append("- Ensure proper focusing of imaging system")
    
    # Check if contrast is too high
    elif results["weighted_mean_contrast"] > results["high_contrast_threshold"]:
        suggestions.append("Contrast is too high. Consider the following:")
        suggestions.append("- Decrease laser power/current")
        suggestions.append("- Check for saturation in bright regions")
        suggestions.append("- Increase exposure time to gather more light")
        suggestions.append("- Add a light diffuser to spread the illumination more evenly")
    
    # If contrast is in optimal range
    else:
        suggestions.append("Contrast is in optimal range. Current settings are good.")
        
        # Check if there are still significant areas of non-optimal contrast
        if results["optimal_contrast_percentage"] < 70:
            suggestions.append("However, only {:.1f}% of the ROI has optimal contrast. Consider:".format(
                results["optimal_contrast_percentage"]))
            suggestions.append("- Fine-tuning illumination to make it more uniform")
            suggestions.append("- Adjusting ROI to focus on areas with better speckle formation")
    
    return "\n".join(suggestions)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze speckle contrast with weighted ROI")
    parser.add_argument("image_path", nargs='?', default="captured_image_50000us.raw",
                        help="Path to the raw image file (default: captured_image_50000us.raw)")
    parser.add_argument("--width", type=int, default=960, 
                        help="Image width in pixels (default: 960)")
    parser.add_argument("--height", type=int, default=1200, 
                        help="Image height in pixels (default: 1200)")
    parser.add_argument("--dtype", choices=["uint8", "uint16"], default="uint16", 
                        help="Image data type (default: uint16)")
    parser.add_argument("--window", type=int, default=7,
                        help="Window size for local contrast calculation (default: 7)")
    parser.add_argument("--sigma", type=float, default=None,
                        help="Sigma for center weighting (default: auto)")
    parser.add_argument("--suggest", action="store_true",
                        help="Suggest improvements based on contrast analysis")
    parser.add_argument("--suggest-laser-current", action="store_true",
                        help="Suggest specific laser current adjustment based on contrast")
    parser.add_argument("--no-save", action="store_true",
                        help="Don't save output images to disk")
    
    args = parser.parse_args()
    
    # Convert dtype string to numpy dtype
    dtype_map = {"uint8": np.uint8, "uint16": np.uint16}
    dtype = dtype_map[args.dtype]
    
    # Process the image
    img = read_raw_image(args.image_path, args.width, args.height, dtype)
    results = analyze_contrast(img, args.window, args.sigma)
    
    # Print results summary
    if results["is_optimal_contrast"]:
        status = "OPTIMAL"
    else:
        status = "SUB-OPTIMAL"
    
    print(f"\nContrast Analysis: {status}")
    print(f"  Global contrast: {results['global_contrast']:.3f}")
    print(f"  Weighted mean contrast: {results['weighted_mean_contrast']:.3f}")
    print(f"  Optimal range coverage: {results['optimal_contrast_percentage']:.1f}%")
    
    # Suggest improvements if requested
    if args.suggest:
        print("\nImprovement Suggestions:")
        print(suggest_improvements(results))
    
    # Suggest specific laser current adjustment if requested
    if args.suggest_laser_current:
        contrast_value = results["weighted_mean_contrast"]
        ideal_min = results["low_contrast_threshold"]  # 0.15
        ideal_max = results["high_contrast_threshold"]  # 0.6
        
        if contrast_value < ideal_min:
            # Too low contrast - increase laser power
            # Calculate percentage based on how far below threshold
            percentage_low = (ideal_min - contrast_value) / ideal_min
            adjustment_factor = min(1.5, 1 + percentage_low)  # Cap at 50% increase
            print(f"\nRECOMMENDATION: INCREASE laser current by {(adjustment_factor-1)*100:.0f}%")
            print(f"  Current contrast: {contrast_value:.3f}, Target range: {ideal_min:.2f}-{ideal_max:.2f}")
        
        elif contrast_value > ideal_max:
            # Too high contrast - decrease laser power
            percentage_high = (contrast_value - ideal_max) / ideal_max
            adjustment_factor = max(0.5, 1 - percentage_high * 0.5)  # Cap at 50% decrease
            print(f"\nRECOMMENDATION: DECREASE laser current by {(1-adjustment_factor)*100:.0f}%")
            print(f"  Current contrast: {contrast_value:.3f}, Target range: {ideal_min:.2f}-{ideal_max:.2f}")
        
        else:
            # Optimal contrast range
            print(f"\nRECOMMENDATION: MAINTAIN current laser settings")
            print(f"  Current contrast: {contrast_value:.3f} is within optimal range: {ideal_min:.2f}-{ideal_max:.2f}")
    
    # Plot results
    plot_results(img, results, args.image_path, not args.no_save) 