import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
import os

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
            width = 960  # Default width (was 1920, changed to avoid duplication)
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

def analyze_saturation_by_pixel_count(img, saturation_threshold=0.98, max_weighted_saturation=100, weight_sigma=None, weight_mask=None):
    """
    Analyze image saturation by weighted counting of saturated pixels, with more weight given to center pixels.
    
    Args:
        img: Image as numpy array
        saturation_threshold: Threshold fraction of max value to consider a pixel saturated
        max_weighted_saturation: Maximum allowable weighted saturation before flagging as saturated
        weight_sigma: Standard deviation for the radial weight mask, if None uses default
        weight_mask: Custom weight mask, if provided will override the auto-generated mask
    
    Returns:
        Dictionary containing analysis results
    """
    # Determine max possible value based on data type
    if img.dtype == np.uint16:
        max_possible_value = 65535
        # Scale to 8-bit for visualization
        img_8bit = (img / 256).astype(np.uint8)
    else:  # Assume uint8
        max_possible_value = 255
        img_8bit = img.copy()
    
    # Create or use provided weight mask
    if weight_mask is None:
        weight_mask = create_radial_weight_mask(img.shape, sigma=weight_sigma)
    
    # Calculate saturation threshold value
    sat_threshold_value = int(max_possible_value * saturation_threshold)
    
    # Create saturation mask (True for saturated pixels)
    saturation_mask = img > sat_threshold_value
    
    # Count saturated pixels (both raw and weighted)
    saturated_pixels = np.sum(saturation_mask)
    
    # Apply weighting to the saturated pixels
    weighted_saturation = np.sum(saturation_mask * weight_mask)
    
    # Calculate effective total weight for percentage calculation
    total_weight = np.sum(weight_mask)
    
    # Calculate saturation percentages
    total_pixels = img.size
    saturated_percentage = (saturated_pixels / total_pixels) * 100
    weighted_saturation_percentage = (weighted_saturation / total_weight) * 100
    
    # Determine if image is saturated based on weighted saturation
    # Use both an absolute threshold and a percentage threshold
    is_saturated = (weighted_saturation > max_weighted_saturation) or (weighted_saturation_percentage > 0.5)
    
    # Generate visual saturation map
    saturation_map = np.zeros((*img.shape, 3), dtype=np.uint8)
    
    # Base layer - grayscale image
    for i in range(3):
        saturation_map[:, :, i] = img_8bit
    
    # Highlight center weighting with a subtle green tint
    # Normalize weight_mask to 0-30 range for subtle tint
    green_tint = (weight_mask * 30).astype(np.uint8)
    saturation_map[:, :, 1] = np.minimum(255, saturation_map[:, :, 1] + green_tint)
    
    # Highlight saturated pixels in red
    saturation_map[:, :, 0][saturation_mask] = 255  # Red
    saturation_map[:, :, 1][saturation_mask] = 0    # No green
    saturation_map[:, :, 2][saturation_mask] = 0    # No blue
    
    # Compile results
    return {
        "image_shape": img.shape,
        "saturated_pixels": saturated_pixels,
        "saturated_percentage": saturated_percentage,
        "weighted_saturation": weighted_saturation,
        "weighted_saturation_percentage": weighted_saturation_percentage,
        "max_weighted_saturation": max_weighted_saturation,
        "is_saturated": is_saturated,
        "saturation_threshold": sat_threshold_value,
        "weight_mask": weight_mask,
        "saturation_map": saturation_map,
        "img_8bit": img_8bit
    }

def plot_results(img, results, image_path, save_output=True):
    """
    Plot pixel count analysis results.
    
    Args:
        img: Original image as numpy array
        results: Dictionary containing analysis results
        image_path: Path to save results or None if no saving is required
        save_output: Whether to save output to disk
    """
    # Create figure
    fig = plt.figure(figsize=(14, 10))
    
    # Plot original image
    if img.dtype == np.uint16:
        ax1 = fig.add_subplot(2, 2, 1)
        ax1.imshow(results["img_8bit"], cmap='gray', vmin=0, vmax=255)
        ax1.set_title(f"Original Image\n{Path(image_path).name}")
        ax1.axis('off')
    
    # Plot saturation map
    ax2 = fig.add_subplot(2, 2, 2)
    saturation_map = ax2.imshow(results["saturation_map"], cmap='hot')
    cbar = plt.colorbar(saturation_map, ax=ax2, orientation='vertical', pad=0.01)
    cbar.set_label('Saturation Level', rotation=270, labelpad=15)
    
    # Add color key for saturation map
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='black', edgecolor='none', label='No Saturation (0)\nSafe'),
        Patch(facecolor='darkred', edgecolor='none', label='Low Saturation (1-50)\nConsider decreasing current by 5%'),
        Patch(facecolor='red', edgecolor='none', label='Medium Saturation (51-200)\nDecrease current by 15%'),
        Patch(facecolor='yellow', edgecolor='none', label='High Saturation (>200)\nDecrease current by 25%')
    ]
    ax2.legend(handles=legend_elements, loc='upper center', 
               bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize='small')
    
    ax2.set_title(f"Saturation Map\nSaturated Pixels: {results['saturated_pixels']} ({results['saturated_percentage']:.2f}%)")
    ax2.axis('off')
    
    # Add a subplot for detailed analysis results
    ax3 = fig.add_subplot(2, 2, 3)
    
    # Add detailed results as text
    sat_percent = results['saturated_percentage']
    weighted_sat_percent = results['weighted_saturation_percentage']
    
    # Determine status and recommendations based on saturation percentage
    if weighted_sat_percent < 0.1:
        status = "NO SATURATION DETECTED"
        color = "green"
        recommendation = "Current settings are optimal"
        arduino_code = "// No change needed, saturation is negligible"
        adjustment = 0
    elif weighted_sat_percent < 1.0:
        status = "MINIMAL SATURATION"
        color = "lightgreen"
        recommendation = "Current settings are acceptable"
        arduino_code = "// Minor adjustments optional, saturation is minimal"
        adjustment = 5
    elif weighted_sat_percent < 5.0:
        status = "MODERATE SATURATION"
        color = "orange"
        recommendation = "DECREASE laser current by 10%"
        arduino_code = "current_value *= 0.9; // Decrease by 10%"
        adjustment = 10
    elif weighted_sat_percent < 10.0:
        status = "SIGNIFICANT SATURATION"
        color = "red"
        recommendation = "DECREASE laser current by 20%"
        arduino_code = "current_value *= 0.8; // Decrease by 20%"
        adjustment = 20
    else:
        status = "SEVERE SATURATION"
        color = "darkred"
        recommendation = "DECREASE laser current by 30%"
        arduino_code = "current_value *= 0.7; // Decrease by 30%"
        adjustment = 30
    
    # Create text for results
    text_str = (
        f"PIXEL COUNT SATURATION ANALYSIS RESULTS:\n\n"
        f"Total Saturated Pixels: {results['saturated_pixels']} pixels\n"
        f"Raw Saturation Percentage: {sat_percent:.2f}%\n"
        f"Center-Weighted Saturation: {weighted_sat_percent:.2f}%\n"
        f"Saturation Threshold: {results['saturation_threshold']}\n\n"
        f"Status: {status}\n\n"
        f"Recommendation: {recommendation}\n\n"
        f"Arduino Implementation:\n"
        f"{arduino_code}\n\n"
        f"Color Key Explanation:\n"
        f"• Black: No saturated pixels\n"
        f"• Dark Red: Low saturation level\n"
        f"• Red: Medium saturation level\n"
        f"• Yellow: High saturation level\n\n"
        f"Saturation detection prioritizes central image regions,\n"
        f"where tissue is typically positioned."
    )
    
    # Add text box with results
    props = dict(boxstyle='round', facecolor=color, alpha=0.3)
    ax3.text(0.5, 0.5, text_str, transform=ax3.transAxes, fontsize=10,
             va='top', ha='center', bbox=props)
    
    # Save if requested and path is provided
    if save_output and image_path is not None:
        # Create output directory if it doesn't exist
        output_dir = Path(os.path.dirname(image_path))
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Save figure
        plt.savefig(image_path)
        print(f"Analysis saved to {image_path}")
    
    return fig

def find_optimal_exposure(image_paths, width=None, height=None, dtype=np.uint16, 
                         saturation_threshold=0.98, max_weighted_saturation=100, weight_sigma=None):
    """
    Find the optimal exposure time from a set of images using weighted saturation analysis.
    
    Args:
        image_paths: List of paths to raw image files
        width, height, dtype: Image parameters
        saturation_threshold, max_weighted_saturation, weight_sigma: Analysis parameters
    
    Returns:
        Path to the optimal image and its analysis results
    """
    exposure_times = []
    saturation_results = []
    
    print("Analyzing images to find optimal exposure time...")
    
    for path in image_paths:
        path_str = str(path)
        
        # Extract exposure time from filename (assuming format like "captured_image_50000us.raw")
        try:
            exposure_us = int(path_str.split('_')[-1].split('us')[0])
            exposure_ms = exposure_us / 1000
        except:
            # If can't extract, use index as placeholder
            exposure_ms = len(exposure_times) + 1
        
        print(f"Analyzing {path_str} (exposure: {exposure_ms}ms)")
        
        # Read and analyze image
        img = read_raw_image(path, width, height, dtype)
        results = analyze_saturation_by_pixel_count(
            img, saturation_threshold, max_weighted_saturation, weight_sigma)
        
        # Store results
        exposure_times.append(exposure_ms)
        saturation_results.append({
            "path": path,
            "exposure_ms": exposure_ms,
            "results": results
        })
    
    # Find the highest exposure time that's not saturated
    valid_exposures = [r for r in saturation_results if not r["results"]["is_saturated"]]
    
    if valid_exposures:
        # Sort by exposure time (descending) and take the highest
        optimal = sorted(valid_exposures, key=lambda x: x["exposure_ms"], reverse=True)[0]
        print(f"\nOptimal exposure found: {optimal['exposure_ms']}ms")
        print(f"Image: {optimal['path']}")
        print(f"Weighted saturation: {optimal['results']['weighted_saturation']:.1f}")
        return optimal["path"], optimal["results"]
    else:
        # If all are saturated, take the one with the least weighted saturation
        least_saturated = sorted(saturation_results, 
                                key=lambda x: x["results"]["weighted_saturation"])[0]
        print(f"\nWarning: All images are saturated. Selecting least saturated:")
        print(f"Image: {least_saturated['path']}")
        print(f"Exposure: {least_saturated['exposure_ms']}ms")
        print(f"Weighted saturation: {least_saturated['results']['weighted_saturation']:.1f}")
        return least_saturated["path"], least_saturated["results"]

# Global constant for max weighted saturation
max_weighted_saturation = 100

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze image saturation using weighted pixel count")
    parser.add_argument("image_path", nargs='?', default="captured_image_50000us.raw",
                        help="Path to the raw image file (default: captured_image_50000us.raw)")
    parser.add_argument("--width", type=int, default=960, 
                        help="Image width in pixels (default: 960)")
    parser.add_argument("--height", type=int, default=1200, 
                        help="Image height in pixels (default: 1200)")
    parser.add_argument("--dtype", choices=["uint8", "uint16"], default="uint16", 
                        help="Image data type (default: uint16)")
    parser.add_argument("--threshold", type=float, default=0.98, 
                        help="Saturation threshold as fraction of max value (default: 0.98)")
    parser.add_argument("--max-weighted", type=float, default=100.0, 
                        help="Maximum allowable weighted saturation (default: 100.0)")
    parser.add_argument("--sigma", type=float, default=None,
                        help="Sigma for center weighting (default: auto)")
    parser.add_argument("--find-optimal", action="store_true", 
                        help="Find optimal exposure from multiple images")
    parser.add_argument("--batch", action="store_true", 
                        help="Process all .raw files in the current directory")
    parser.add_argument("--suggest-laser-current", action="store_true",
                        help="Suggest laser current adjustment based on saturation")
    parser.add_argument("--no-save", action="store_true",
                        help="Don't save output images to disk")
    
    args = parser.parse_args()
    
    # Set global constant
    max_weighted_saturation = args.max_weighted
    
    # Convert dtype string to numpy dtype
    dtype_map = {"uint8": np.uint8, "uint16": np.uint16}
    dtype = dtype_map[args.dtype]
    
    if args.find_optimal:
        # Find optimal exposure from multiple images
        if args.batch:
            # Process all .raw files in the current directory
            import glob
            image_paths = glob.glob("*.raw")
            if not image_paths:
                print("No .raw files found in the current directory.")
                exit(1)
        else:
            # Process only the specified image
            image_paths = [args.image_path]
        
        optimal_path, optimal_results = find_optimal_exposure(
            image_paths, args.width, args.height, dtype, 
            args.threshold, args.max_weighted, args.sigma)
        
        print(f"\nOptimal image: {optimal_path}")
        img = read_raw_image(optimal_path, args.width, args.height, dtype)
        plot_results(img, optimal_results, optimal_path, not args.no_save)
    else:
        # Process a single image
        img = read_raw_image(args.image_path, args.width, args.height, dtype)
        results = analyze_saturation_by_pixel_count(
            img, args.threshold, args.max_weighted, args.sigma)
        
        # Print concise summary
        sat_status = "SATURATED" if results["is_saturated"] else "NOT SATURATED"
        print(f"\n{sat_status} - {args.image_path}")
        print(f"  Saturated pixels: {results['saturated_pixels']} ({results['saturated_percentage']:.2f}%)")
        print(f"  Weighted saturation: {results['weighted_saturation']:.1f} ({results['weighted_saturation_percentage']:.2f}%)")
        
        # Suggest laser current adjustment if requested
        if args.suggest_laser_current:
            if results['is_saturated']:
                # Image is saturated, suggest decreasing laser current
                suggested_reduction = 1.0 / 1.2  # Reduce by factor of 1.2
                print(f"  RECOMMENDATION: DECREASE laser current by {(1-suggested_reduction)*100:.0f}%")
            elif results['weighted_saturation_percentage'] < 0.05:
                # Very few saturated pixels, suggest increasing laser current
                suggested_increase = 1.2  # Increase by factor of 1.2
                print(f"  RECOMMENDATION: INCREASE laser current by {(suggested_increase-1)*100:.0f}%")
            else:
                # Image is not saturated but has some high intensity pixels, good exposure
                print("  RECOMMENDATION: MAINTAIN current laser current settings")
        
        plot_results(img, results, args.image_path, not args.no_save) 