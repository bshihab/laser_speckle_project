import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
import os
from datetime import datetime
import time

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

def analyze_saturation_by_histogram(img, high_intensity_threshold=0.9, critical_bin_threshold=0.1, weight_sigma=None, weight_mask=None):
    """
    Analyze image saturation using weighted histogram analysis with center-focused weighting.
    
    Args:
        img: Image as numpy array
        high_intensity_threshold: Threshold fraction of max value to consider high intensity
        critical_bin_threshold: Threshold for histogram bin percentage to indicate saturation
        weight_sigma: Standard deviation for the radial weight mask, if None uses default
        weight_mask: Custom weight mask, if provided will override the auto-generated mask
    
    Returns:
        Dictionary containing analysis results
    """
    # Determine max possible value and scale for visualization
    if img.dtype == np.uint16:
        max_possible_value = 65535
        # Scale to 8-bit for visualization and histogram
        img_8bit = (img / 256).astype(np.uint8)
    else:  # Assume uint8
        max_possible_value = 255
        img_8bit = img.copy()
    
    # Create or use provided weight mask
    if weight_mask is None:
        weight_mask = create_radial_weight_mask(img.shape, sigma=weight_sigma)
    
    # Flatten image and weight mask for histogram calculation
    flat_img = img.flatten()
    flat_weights = weight_mask.flatten()
    
    # Calculate histogram for entire image but with pixel weighting
    # For 16-bit images, we'll bin to 256 levels for display
    if img.dtype == np.uint16:
        # Convert to 8-bit scale for histogram
        hist_img = (flat_img / 256).astype(np.uint8)
        hist, bins = np.histogram(hist_img, bins=256, range=(0, 255), weights=flat_weights)
        bin_centers = (bins[:-1] + bins[1:]) / 2
    else:
        hist, bins = np.histogram(flat_img, bins=256, range=(0, 255), weights=flat_weights)
        bin_centers = (bins[:-1] + bins[1:]) / 2
    
    # Normalize histogram to percentages (against total weight)
    total_weight = np.sum(flat_weights)
    hist_percentage = (hist / total_weight) * 100
    
    # Calculate high intensity threshold value
    if img.dtype == np.uint16:
        high_threshold_value = int(max_possible_value * high_intensity_threshold)
        # Convert to 8-bit scale for analysis
        high_threshold_8bit = int(255 * high_intensity_threshold)
    else:
        high_threshold_value = int(max_possible_value * high_intensity_threshold)
        high_threshold_8bit = high_threshold_value
    
    # Check for histogram peak at high intensities (possible saturation)
    # Sum the histogram bins above the high intensity threshold
    high_intensity_sum = np.sum(hist_percentage[high_threshold_8bit:])
    
    # Check if the highest bin has a significant percentage (indicating saturation)
    highest_bin_percentage = hist_percentage[-1]
    
    # Determine if image is saturated based on histogram
    is_saturated = (highest_bin_percentage > critical_bin_threshold) or (high_intensity_sum > 10)
    
    # Calculate weighted statistics
    weighted_mean = np.average(flat_img, weights=flat_weights)
    # For weighted std, calculate manually
    weighted_variance = np.average((flat_img - weighted_mean)**2, weights=flat_weights)
    weighted_std = np.sqrt(weighted_variance)
    
    # Calculate weighted percentiles
    # Sort flat_img and get corresponding weights
    sorted_indices = np.argsort(flat_img)
    sorted_img = flat_img[sorted_indices]
    sorted_weights = flat_weights[sorted_indices]
    
    # Calculate cumulative weights
    cumulative_weights = np.cumsum(sorted_weights)
    cumulative_weights = cumulative_weights / cumulative_weights[-1]  # Normalize
    
    # Find values at percentiles
    p95_idx = np.searchsorted(cumulative_weights, 0.95)
    percentile_95 = sorted_img[p95_idx]
    
    # Find p5 for dynamic range calculation
    p5_idx = np.searchsorted(cumulative_weights, 0.05)
    percentile_5 = sorted_img[p5_idx]
    
    # Calculate dynamic range as percentage of max possible value
    if img.dtype == np.uint16:
        max_possible = 65535
    else:
        max_possible = 255
    
    dynamic_range = (percentile_95 - percentile_5) / max_possible
    
    # Count near-max pixels with weighting
    near_max_mask = img > (0.95 * max_possible_value)
    weighted_near_max = np.sum(near_max_mask * weight_mask)
    near_max_percentage = (weighted_near_max / total_weight) * 100
    
    # Generate saturation map
    saturation_map = np.zeros((*img.shape, 3), dtype=np.uint8)
    
    # Base layer - grayscale image
    for i in range(3):
        saturation_map[:, :, i] = img_8bit
    
    # Highlight center weighting with a subtle green tint
    # Normalize weight_mask to 0-30 range for subtle tint
    green_tint = (weight_mask * 30).astype(np.uint8)
    saturation_map[:, :, 1] = np.minimum(255, saturation_map[:, :, 1] + green_tint)
    
    # Highlight high intensity pixels in red
    high_pixels = img > high_threshold_value
    saturation_map[:, :, 0][high_pixels] = 255  # Red
    saturation_map[:, :, 1][high_pixels] = 0    # No green
    saturation_map[:, :, 2][high_pixels] = 0    # No blue
    
    # Compile results
    return {
        "image_shape": img.shape,
        "histogram": hist,
        "bin_centers": bin_centers,
        "histogram_percentage": hist_percentage,
        "high_threshold_value": high_threshold_value,
        "high_intensity_sum": high_intensity_sum,
        "highest_bin_percentage": highest_bin_percentage,
        "is_saturated": is_saturated,
        "weighted_mean": weighted_mean,
        "weighted_std": weighted_std,
        "max_intensity": np.max(img),
        "percentile_95": percentile_95,
        "percentile_5": percentile_5,
        "dynamic_range": dynamic_range,
        "near_max_percentage": near_max_percentage,
        "weight_mask": weight_mask,
        "img_8bit": img_8bit,
        "saturation_map": saturation_map
    }

def plot_results(img, results, image_path, save_output=True):
    """
    Plot the histogram-based saturation analysis results with center weighting.
    
    Args:
        img: Original image as numpy array
        results: Dictionary containing analysis results
        image_path: Path to the original image file or None if no saving is required
        save_output: Whether to save output images to disk
    """
    fig = plt.figure(figsize=(16, 8))
    gs = plt.GridSpec(2, 2, figure=fig, height_ratios=[1, 1])
    
    # Plot original image
    ax1 = fig.add_subplot(gs[0, 0])
    if img.dtype == np.uint16:
        ax1.imshow(results.get("img_8bit", img), cmap='gray', vmin=0, vmax=255)
    else:
        ax1.imshow(img, cmap='gray', vmin=0, vmax=255)
    
    ax1.set_title(f"Original Image\n{Path(image_path).name}")
    ax1.axis('off')
    
    # Plot weighted histogram
    ax2 = fig.add_subplot(gs[0, 1])
    
    # Check for required keys and provide defaults if missing
    if "bin_centers" in results and "histogram" in results:
        bin_centers = results["bin_centers"]
        hist_data = results.get("weighted_histogram", results["histogram"])
        
        # Generate bin edges if they're missing
        if "bin_edges" not in results:
            # Calculate bin width from bin centers
            if len(bin_centers) > 1:
                bin_width = bin_centers[1] - bin_centers[0]
            else:
                bin_width = 1
            bin_edges = np.append(bin_centers - bin_width/2, bin_centers[-1] + bin_width/2)
        else:
            bin_edges = results["bin_edges"]
            # Calculate bin width from bin edges
            if len(bin_edges) > 1:
                bin_width = bin_edges[1] - bin_edges[0]
            else:
                bin_width = 1
        
        # Plot histogram
        bars = ax2.bar(bin_centers, hist_data, width=bin_width,
                    alpha=0.7, color='blue', edgecolor='black')
        
        # Get or calculate saturation thresholds
        saturation_threshold = results.get("saturation_threshold", 
                                        int(np.max(bin_centers) * 0.95))
        upper_guideline = results.get("upper_guideline", 
                                    int(np.max(bin_centers) * 0.85))
        
        # Set different colors for specific regions
        for i, bar in enumerate(bars):
            if bin_centers[i] >= saturation_threshold:
                bar.set_color('red')
                bar.set_alpha(0.7)
            elif bin_centers[i] >= upper_guideline:
                bar.set_color('yellow')
                bar.set_alpha(0.7)
        
        # Add vertical lines for important thresholds
        ax2.axvline(x=upper_guideline, color='orange', linestyle='--', 
                    label=f'Upper Guideline ({upper_guideline})')
        ax2.axvline(x=saturation_threshold, color='red', linestyle='--', 
                    label=f'Saturation Threshold ({saturation_threshold})')
        
        # Add color key for histogram
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='blue', edgecolor='black', alpha=0.7, label='Normal Intensity'),
            Patch(facecolor='yellow', edgecolor='black', alpha=0.7, label='High Intensity'),
            Patch(facecolor='red', edgecolor='black', alpha=0.7, label='Saturation Region')
        ]
        ax2.legend(handles=legend_elements, loc='upper right')
        
        ax2.set_title("Weighted Histogram Analysis")
        ax2.set_xlabel("Pixel Intensity")
        ax2.set_ylabel("Weighted Count")
        
        # Determine saturation status
        is_saturated = results.get("is_saturated", False)
        highest_bin = results.get("highest_bin_percentage", 0)
        
        status_text = "SATURATED" if is_saturated else "NOT SATURATED"
        status_color = "red" if is_saturated else "green"
        
        # Add text annotations
        if is_saturated:
            ax2.text(0.5, 0.95, f"Status: {status_text}", transform=ax2.transAxes,
                    fontsize=12, ha='center', va='top',
                    bbox=dict(boxstyle='round', facecolor=status_color, alpha=0.3))
    else:
        ax2.text(0.5, 0.5, "Histogram data not available", 
                transform=ax2.transAxes, fontsize=12, ha='center')
    
    # Plot saturation map
    ax3 = fig.add_subplot(gs[1, 0])
    
    if "saturation_map" in results:
        saturation_map = ax3.imshow(results["saturation_map"])
        ax3.set_title("Saturation Map\n(Red = Saturated Pixels)")
        ax3.axis('off')
    else:
        ax3.text(0.5, 0.5, "Saturation map not available", 
                transform=ax3.transAxes, fontsize=12, ha='center')
    
    # Add summary text with recommendations
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')
    
    # Format text based on available data
    high_sum = results.get("high_intensity_sum", 0)
    highest_bin = results.get("highest_bin_percentage", 0)
    is_saturated = results.get("is_saturated", False)
    weighted_mean = results.get("weighted_mean", 0)
    
    # Use more granular steps for laser current adjustment recommendations
    if is_saturated:
        if highest_bin > 10.0:
            rec_text = "DECREASE laser current by 50%"
            color = "darkred"
        elif highest_bin > 5.0:
            rec_text = "DECREASE laser current by 30%"
            color = "darkred"
        elif highest_bin > 2.0:
            rec_text = "DECREASE laser current by 20%"
            color = "red"
        elif highest_bin > 1.0:
            rec_text = "DECREASE laser current by 10%"
            color = "red"
        elif highest_bin > 0.5:
            rec_text = "DECREASE laser current by 5%"
            color = "orange"
        else:
            rec_text = "DECREASE laser current by 2%"
            color = "orange"
    elif high_sum < 0.1:
        rec_text = "INCREASE laser current by 15%"
        color = "blue"
    elif high_sum < 0.5:
        rec_text = "INCREASE laser current by 8%"
        color = "blue"
    elif high_sum < 1.0:
        rec_text = "INCREASE laser current by 4%"
        color = "lightblue"
    elif high_sum < 2.0:
        rec_text = "INCREASE laser current by 2%"
        color = "lightblue"
    else:
        rec_text = "MAINTAIN current laser settings"
        color = "green"
    
    summary_text = f"""HISTOGRAM ANALYSIS RESULTS:

Status: {"SATURATED" if is_saturated else "NOT SATURATED"}

High Intensity Pixels: {high_sum:.2f}%
Highest Bin Percentage: {highest_bin:.2f}%
Weighted Mean: {weighted_mean:.2f}

RECOMMENDATION:
{rec_text}
"""
    
    ax4.text(0.1, 0.95, summary_text, fontsize=12, va='top',
             bbox=dict(boxstyle='round', facecolor=color, alpha=0.15))
    
    # Adjust layout
    plt.tight_layout()
    
    # Save if requested and if path is provided
    if save_output and image_path is not None:
        # Create output directory if it doesn't exist
        output_dir = Path(os.path.dirname(image_path))
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Generate output path
        base_name = Path(image_path).stem
        
        # Create timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(image_path)  # Use the exact path that was provided
        
        # Save figure
        plt.savefig(output_path)
        print(f"Analysis saved to {output_path}")
    
    return fig

def find_optimal_exposure(image_paths, width=None, height=None, dtype=np.uint16, 
                         high_intensity_threshold=0.9, critical_bin_threshold=0.1, weight_sigma=None):
    """
    Find the optimal exposure time from a set of images using weighted histogram analysis.
    
    Args:
        image_paths: List of paths to raw image files
        width, height, dtype: Image parameters
        high_intensity_threshold, critical_bin_threshold, weight_sigma: Analysis parameters
    
    Returns:
        Path to the optimal image and its analysis results
    """
    exposure_times = []
    analysis_results = []
    
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
        results = analyze_saturation_by_histogram(
            img, high_intensity_threshold, critical_bin_threshold, weight_sigma)
        
        # Store results
        exposure_times.append(exposure_ms)
        analysis_results.append({
            "path": path,
            "exposure_ms": exposure_ms,
            "results": results
        })
    
    # Find the highest exposure time that's not saturated
    valid_exposures = [r for r in analysis_results if not r["results"]["is_saturated"]]
    
    if valid_exposures:
        # Calculate a quality score for each valid exposure
        # Higher is better, but we want to avoid getting too close to saturation
        for exp in valid_exposures:
            # Calculate a quality score based on high intensity percentage
            # We want some high intensity pixels but not too many
            high_sum = exp["results"]["high_intensity_sum"]
            highest_bin = exp["results"]["highest_bin_percentage"]
            
            # Ideal range is 1-3% high intensity sum with very low highest bin percentage
            if high_sum < 0.1:
                quality_score = high_sum * 5  # Very low, not utilizing dynamic range
            elif high_sum < 3.0:
                quality_score = 10 - (3.0 - high_sum) * 2  # Closer to 3% is better
            else:
                quality_score = 10 - (high_sum - 3.0) * 3  # Penalize for getting too high
            
            # Penalize if highest bin is starting to accumulate
            if highest_bin > 0.1:
                quality_score -= highest_bin * 5
                
            exp["quality_score"] = quality_score
        
        # Sort by quality score (descending)
        sorted_valid = sorted(valid_exposures, key=lambda x: x["quality_score"], reverse=True)
        optimal = sorted_valid[0]
        
        print(f"\nOptimal exposure found: {optimal['exposure_ms']}ms")
        print(f"Image: {optimal['path']}")
        print(f"Quality score: {optimal['quality_score']:.2f}")
        print(f"High intensity pixels: {optimal['results']['high_intensity_sum']:.2f}%")
        print(f"Highest bin percentage: {optimal['results']['highest_bin_percentage']:.2f}%")
        
        # Show the top 3 exposures if available
        if len(sorted_valid) > 1:
            print("\nTop exposures by quality:")
            for i, exp in enumerate(sorted_valid[:min(3, len(sorted_valid))]):
                print(f"{i+1}. {exp['exposure_ms']}ms - Score: {exp['quality_score']:.2f}, " + 
                      f"High sum: {exp['results']['high_intensity_sum']:.2f}%")
        
        return optimal["path"], optimal["results"]
    else:
        # If all are saturated, calculate the degree of saturation and choose the least saturated
        for exp in analysis_results:
            # Calculate a saturation penalty
            highest_bin = exp["results"]["highest_bin_percentage"]
            high_sum = exp["results"]["high_intensity_sum"]
            
            # Higher penalty for higher saturation
            saturation_penalty = highest_bin * 2 + high_sum
            exp["saturation_penalty"] = saturation_penalty
        
        # Sort by saturation penalty (ascending)
        sorted_saturated = sorted(analysis_results, key=lambda x: x["saturation_penalty"])
        least_saturated = sorted_saturated[0]
        
        print(f"\nWarning: All images are saturated. Selecting least saturated:")
        print(f"Image: {least_saturated['path']}")
        print(f"Exposure: {least_saturated['exposure_ms']}ms")
        print(f"Saturation penalty: {least_saturated['saturation_penalty']:.2f}")
        print(f"High intensity pixels: {least_saturated['results']['high_intensity_sum']:.2f}%")
        print(f"Highest bin percentage: {least_saturated['results']['highest_bin_percentage']:.2f}%")
        
        print("\nRecommendation: Try again with lower exposure times")
        
        return least_saturated["path"], least_saturated["results"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze image saturation using weighted histogram analysis")
    parser.add_argument("image_path", nargs='?', default="captured_image_50000us.raw",
                        help="Path to the raw image file (default: captured_image_50000us.raw)")
    parser.add_argument("--width", type=int, default=960, 
                        help="Image width in pixels (default: 960)")
    parser.add_argument("--height", type=int, default=1200, 
                        help="Image height in pixels (default: 1200)")
    parser.add_argument("--dtype", choices=["uint8", "uint16"], default="uint16", 
                        help="Image data type (default: uint16)")
    parser.add_argument("--high-threshold", type=float, default=0.9, 
                        help="High intensity threshold as fraction of max value (default: 0.9)")
    parser.add_argument("--bin-threshold", type=float, default=0.1, 
                        help="Critical histogram bin threshold percentage (default: 0.1)")
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
            args.high_threshold, args.bin_threshold, args.sigma)
        
        print(f"\nOptimal image: {optimal_path}")
        img = read_raw_image(optimal_path, args.width, args.height, dtype)
        plot_results(img, optimal_results, optimal_path, not args.no_save)
    else:
        # Process a single image
        img = read_raw_image(args.image_path, args.width, args.height, dtype)
        results = analyze_saturation_by_histogram(
            img, args.high_threshold, args.bin_threshold, args.sigma)
        
        # Print more concise summary
        sat_status = "SATURATED" if results["is_saturated"] else "NOT SATURATED"
        print(f"\n{sat_status} - {args.image_path}")
        print(f"  High intensity: {results['high_intensity_sum']:.1f}%, Highest bin: {results['highest_bin_percentage']:.2f}%")
        print(f"  Mean intensity: {results['weighted_mean']:.0f}, Dynamic range: {results['dynamic_range']*100:.1f}%")
        
        # Suggest laser current adjustment if requested
        if args.suggest_laser_current:
            if results['is_saturated']:
                # Image is saturated, suggest decreasing laser current
                if results['highest_bin_percentage'] > 10.0:
                    suggested_reduction = 0.50  # Reduce by 50%
                    print(f"  RECOMMENDATION: DECREASE laser current by 50%")
                elif results['highest_bin_percentage'] > 5.0:
                    suggested_reduction = 0.30  # Reduce by 30%
                    print(f"  RECOMMENDATION: DECREASE laser current by 30%")
                elif results['highest_bin_percentage'] > 2.0:
                    suggested_reduction = 0.20  # Reduce by 20%
                    print(f"  RECOMMENDATION: DECREASE laser current by 20%")
                elif results['highest_bin_percentage'] > 1.0:
                    suggested_reduction = 0.10  # Reduce by 10%
                    print(f"  RECOMMENDATION: DECREASE laser current by 10%")
                elif results['highest_bin_percentage'] > 0.5:
                    suggested_reduction = 0.05  # Reduce by 5%
                    print(f"  RECOMMENDATION: DECREASE laser current by 5%")
                else:
                    suggested_reduction = 0.02  # Reduce by 2%
                    print(f"  RECOMMENDATION: DECREASE laser current by 2%")
            elif results['high_intensity_sum'] < 0.1:
                # Very few high intensity pixels, suggest increasing laser current
                print(f"  RECOMMENDATION: INCREASE laser current by 15%")
            elif results['high_intensity_sum'] < 0.5:
                # Few high intensity pixels, suggest increasing laser current
                print(f"  RECOMMENDATION: INCREASE laser current by 8%")
            elif results['high_intensity_sum'] < 1.0:
                # Small amount of high intensity pixels, suggest small increase
                print(f"  RECOMMENDATION: INCREASE laser current by 4%")
            elif results['high_intensity_sum'] < 2.0:
                # Almost optimal, suggest tiny increase
                print(f"  RECOMMENDATION: INCREASE laser current by 2%")
            else:
                # Image is not saturated but has some high intensity pixels, good exposure
                print("  RECOMMENDATION: MAINTAIN current laser current settings")
        
        plot_results(img, results, args.image_path, not args.no_save) 