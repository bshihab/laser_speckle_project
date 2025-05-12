import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
import glob
import os
import re

def read_raw_image(file_path, width=1920, height=600, dtype=np.uint16):
    """
    Read a raw image file.
    
    Args:
        file_path: Path to the raw image file
        width: Width of the image (default: 1920)
        height: Height of the image (default: 600)
        dtype: Data type of the image (default: np.uint16 for 16-bit images)
    
    Returns:
        numpy array containing the image data
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    
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

def create_central_roi_mask(img_shape, roi_fraction=0.5):
    """
    Create a mask for the central region of interest.
    
    Args:
        img_shape: Shape of the image (height, width)
        roi_fraction: Fraction of image dimensions to include in ROI (0.5 = center 50%)
    
    Returns:
        Boolean mask with True for pixels in the ROI
    """
    height, width = img_shape
    
    # Calculate ROI dimensions
    roi_height = int(height * roi_fraction)
    roi_width = int(width * roi_fraction)
    
    # Calculate ROI boundaries
    y_start = (height - roi_height) // 2
    y_end = y_start + roi_height
    x_start = (width - roi_width) // 2
    x_end = x_start + roi_width
    
    # Create mask
    mask = np.zeros(img_shape, dtype=bool)
    mask[y_start:y_end, x_start:x_end] = True
    
    return mask

def analyze_image_intensity(img, roi_fraction=0.5):
    """
    Analyze image intensity metrics in the central ROI.
    
    Args:
        img: Image as numpy array
        roi_fraction: Fraction of image to consider as central ROI
    
    Returns:
        Dictionary containing intensity analysis results
    """
    # Create central ROI mask
    roi_mask = create_central_roi_mask(img.shape, roi_fraction)
    
    # Extract ROI pixels
    roi_pixels = img[roi_mask]
    
    # Calculate intensity metrics
    mean_intensity = np.mean(roi_pixels)
    median_intensity = np.median(roi_pixels)
    std_intensity = np.std(roi_pixels)
    min_intensity = np.min(roi_pixels)
    max_intensity = np.max(roi_pixels)
    
    # Calculate histogram
    if img.dtype == np.uint16:
        # For 16-bit images, bin more coarsely for the histogram
        hist, bins = np.histogram(roi_pixels, bins=256, range=(0, 65535))
    else:
        hist, bins = np.histogram(roi_pixels, bins=256, range=(0, 255))
    
    # Calculate percentiles
    p5 = np.percentile(roi_pixels, 5)
    p25 = np.percentile(roi_pixels, 25)
    p50 = np.percentile(roi_pixels, 50)
    p75 = np.percentile(roi_pixels, 75)
    p95 = np.percentile(roi_pixels, 95)
    p99 = np.percentile(roi_pixels, 99)
    
    # Count saturated pixels (defined as >98% of max possible value)
    if img.dtype == np.uint16:
        saturation_threshold = int(0.98 * 65535)
    else:
        saturation_threshold = int(0.98 * 255)
    
    saturated_pixels = np.sum(roi_pixels > saturation_threshold)
    saturated_percentage = (saturated_pixels / roi_pixels.size) * 100
    
    # Calculate contrast (coefficient of variation)
    contrast = std_intensity / mean_intensity if mean_intensity > 0 else 0
    
    # Calculate dynamic range utilization (as percentage of total possible range)
    if img.dtype == np.uint16:
        max_possible = 65535
    else:
        max_possible = 255
    
    dynamic_range = (p99 - p5) / max_possible * 100
    
    return {
        "mean_intensity": mean_intensity,
        "median_intensity": median_intensity,
        "std_intensity": std_intensity,
        "min_intensity": min_intensity,
        "max_intensity": max_intensity,
        "histogram": hist,
        "bin_edges": bins,
        "p5": p5,
        "p25": p25,
        "p50": p50,
        "p75": p75, 
        "p95": p95,
        "p99": p99,
        "saturation_threshold": saturation_threshold,
        "saturated_pixels": saturated_pixels,
        "saturated_percentage": saturated_percentage,
        "contrast": contrast,
        "dynamic_range": dynamic_range,
        "roi_mask": roi_mask
    }

def calculate_optimal_score(results):
    """
    Calculate an optimization score for each exposure.
    Higher score is better (0-100).
    
    Args:
        results: Dictionary of intensity analysis results
    
    Returns:
        Float score (0-100)
    """
    # Start with a perfect score
    score = 100.0
    
    # Penalize for saturation (major factor but with progressive penalty)
    saturated = results["saturated_percentage"]
    if saturated > 0:
        if saturated < 0.1:
            # Minimal saturation (<0.1%) - light penalty
            saturation_penalty = saturated * 50  # Max 5 points off
        elif saturated < 1:
            # Moderate saturation (0.1-1%) - medium penalty
            saturation_penalty = 5 + (saturated - 0.1) * 70  # 5-65 points off
        else:
            # Severe saturation (>1%) - heavy penalty
            saturation_penalty = 65 + min(30, (saturated - 1) * 3)  # 65-95 points off
        
        score -= saturation_penalty
    
    # Penalize for poor dynamic range utilization
    # Ideal is to use 40-70% of available dynamic range for speckle
    dynamic_range = results["dynamic_range"]
    if dynamic_range < 25:
        # Too little of the dynamic range is used
        range_penalty = (25 - dynamic_range) * 1.2
        score -= range_penalty
    elif dynamic_range > 70:
        # Too much dynamic range used (risking saturation)
        score -= (dynamic_range - 70) * 0.8
    
    # Penalize for inappropriate contrast (speckle-specific)
    contrast = results["contrast"]
    ideal_contrast_min = 0.15  # Minimum good speckle contrast (for biological tissues)
    ideal_contrast_max = 0.6   # Maximum good speckle contrast
    
    if contrast < ideal_contrast_min:
        # Too little contrast - major penalty
        score -= min(60, (ideal_contrast_min - contrast) * 300)
    elif contrast > 1.0:
        # Extremely high contrast (>1.0) indicates very low signal or noise dominance
        score -= min(80, (contrast - 1.0) * 100)
    elif contrast > ideal_contrast_max:
        # Higher than ideal but still usable - moderate penalty
        score -= min(30, (contrast - ideal_contrast_max) * 60)
    
    # Boost score for exposures that maximize intensity without saturation
    # This helps select the highest usable exposure
    if saturated < 0.1:  # Only if minimal saturation
        # Calculate mean intensity as percentage of saturation threshold
        intensity_usage = results["mean_intensity"] / results["saturation_threshold"] * 100
        
        # Boost for utilizing a good percentage of the range (30-80%)
        if 30 <= intensity_usage <= 80:
            # Maximum bonus at 60% utilization
            if intensity_usage <= 60:
                intensity_bonus = (intensity_usage - 30) / 6  # Up to 5 points
            else:
                intensity_bonus = 5 - (intensity_usage - 60) / 4  # Decreasing from 5 points
            
            score += intensity_bonus
    
    # Give a small bonus for higher exposure if other factors are equal
    # This helps prefer the highest usable exposure for better SNR
    if saturated < 0.5 and contrast >= ideal_contrast_min and contrast <= 1.0:
        exposure_factor = min(results["mean_intensity"] / 5000, 5)
        score += exposure_factor
    
    # Ensure score is non-negative and cap at 100
    return max(0, min(100, score))

def extract_exposure_time(file_path):
    """Extract exposure time from filename (assuming captured_image_XXXXXus.raw format)"""
    match = re.search(r'_(\d+)us', str(file_path))
    if match:
        return int(match.group(1))
    else:
        # Cannot determine exposure - return None
        return None

def calibrate_exposure(image_paths, width=1920, height=600, dtype=np.uint16, roi_fraction=0.5):
    """
    Perform exposure calibration across multiple images with different exposure times.
    
    Args:
        image_paths: List of paths to raw image files
        width: Width of the images
        height: Height of the images
        dtype: Data type of the images
        roi_fraction: Fraction of image to use as ROI
    
    Returns:
        Dictionary containing calibration results
    """
    exposure_times = []
    analysis_results = []
    
    print("Analyzing images for exposure calibration...")
    
    for path in image_paths:
        # Extract exposure time from filename
        exposure_us = extract_exposure_time(path)
        if exposure_us is None:
            print(f"Warning: Could not determine exposure time for {path}. Skipping.")
            continue
        
        exposure_ms = exposure_us / 1000
        
        print(f"Analyzing {Path(path).name} (exposure: {exposure_ms:.2f}ms)")
        
        # Read and analyze image
        img = read_raw_image(path, width, height, dtype)
        results = analyze_image_intensity(img, roi_fraction)
        
        # Calculate optimization score
        score = calculate_optimal_score(results)
        
        # Store results
        exposure_times.append(exposure_ms)
        analysis_results.append({
            "path": path,
            "exposure_us": exposure_us,
            "exposure_ms": exposure_ms,
            "results": results,
            "score": score
        })
    
    # Sort by exposure time
    sorted_results = sorted(analysis_results, key=lambda x: x["exposure_ms"])
    
    # Find optimal exposure (highest score)
    if sorted_results:
        optimal_result = max(sorted_results, key=lambda x: x["score"])
        
        # Find next best exposures
        sorted_by_score = sorted(sorted_results, key=lambda x: x["score"], reverse=True)
        top_results = sorted_by_score[:3]  # Top 3 results
        
        return {
            "all_results": sorted_results,
            "optimal_result": optimal_result,
            "top_results": top_results
        }
    else:
        print("No valid results to analyze.")
        return None

def plot_calibration_results(calibration_results):
    """
    Plot exposure calibration results.
    
    Args:
        calibration_results: Results from calibrate_exposure
    """
    if not calibration_results:
        print("No calibration results to plot.")
        return
    
    sorted_results = calibration_results["all_results"]
    optimal_result = calibration_results["optimal_result"]
    
    # Extract data for plotting
    exposure_times = [r["exposure_ms"] for r in sorted_results]
    mean_intensities = [r["results"]["mean_intensity"] for r in sorted_results]
    contrasts = [r["results"]["contrast"] for r in sorted_results]
    saturated_percentages = [r["results"]["saturated_percentage"] for r in sorted_results]
    scores = [r["score"] for r in sorted_results]
    
    # Create figure for plots
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    
    # Helper function to mark the optimal point
    def mark_optimal(ax, x_data, y_data, label):
        # Plot all points
        ax.plot(x_data, y_data, 'o-', label=label)
        
        # Find index of optimal point
        opt_idx = exposure_times.index(optimal_result["exposure_ms"])
        
        # Mark optimal point
        ax.plot(x_data[opt_idx], y_data[opt_idx], 'X', color='red', markersize=12, 
               label=f'Optimal: {optimal_result["exposure_ms"]:.2f}ms')
    
    # Plot 1: Mean Intensity vs Exposure Time
    ax1 = axs[0, 0]
    mark_optimal(ax1, exposure_times, mean_intensities, "Mean Intensity")
    ax1.set_title("Mean Intensity vs Exposure Time")
    ax1.set_xlabel("Exposure Time (ms)")
    ax1.set_ylabel("Mean Intensity")
    ax1.set_xscale('log')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Contrast vs Exposure Time
    ax2 = axs[0, 1]
    mark_optimal(ax2, exposure_times, contrasts, "Contrast")
    
    # Add optimal range for contrast
    ax2.axhspan(0.08, 0.25, color='green', alpha=0.2, label="Ideal Contrast Range")
    
    ax2.set_title("Contrast vs Exposure Time")
    ax2.set_xlabel("Exposure Time (ms)")
    ax2.set_ylabel("Contrast (σ/μ)")
    ax2.set_xscale('log')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Plot 3: Saturation Percentage vs Exposure Time
    ax3 = axs[1, 0]
    mark_optimal(ax3, exposure_times, saturated_percentages, "Saturated Pixels")
    
    # Add threshold line
    ax3.axhline(y=0.1, color='red', linestyle='--', label="Saturation Threshold (0.1%)")
    
    ax3.set_title("Saturation Percentage vs Exposure Time")
    ax3.set_xlabel("Exposure Time (ms)")
    ax3.set_ylabel("Saturated Pixels (%)")
    ax3.set_xscale('log')
    ax3.set_yscale('log')
    ax3.set_ylim(bottom=0.001)
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Plot 4: Optimization Score vs Exposure Time
    ax4 = axs[1, 1]
    mark_optimal(ax4, exposure_times, scores, "Optimization Score")
    ax4.set_title("Optimization Score vs Exposure Time\n(Higher is better)")
    ax4.set_xlabel("Exposure Time (ms)")
    ax4.set_ylabel("Score (0-100)")
    ax4.set_xscale('log')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    # Add overall title
    plt.suptitle("Exposure Calibration Results", fontsize=16)
    
    plt.tight_layout()
    plt.savefig("exposure_calibration_results.png")
    print("Calibration results saved to exposure_calibration_results.png")
    
    # Generate histograms for top exposures
    plot_top_histograms(calibration_results["top_results"])
    
    return fig

def plot_top_histograms(top_results):
    """
    Plot histograms for the top exposure times.
    
    Args:
        top_results: List of top results from calibration
    """
    fig, axs = plt.subplots(len(top_results), 1, figsize=(12, 4*len(top_results)))
    
    if len(top_results) == 1:
        axs = [axs]  # Make it iterable if only one plot
    
    for i, result in enumerate(top_results):
        ax = axs[i]
        
        # Get histogram data
        hist = result["results"]["histogram"]
        bins = result["results"]["bin_edges"][:-1]  # Remove the last bin edge
        
        if result["results"]["bin_edges"].max() > 255:
            # 16-bit data, scale x-axis as percentage of max
            x_vals = bins / 65535 * 100
            x_label = "Intensity (% of max)"
        else:
            # 8-bit data
            x_vals = bins
            x_label = "Intensity (0-255)"
        
        # Plot histogram
        ax.bar(x_vals, hist, width=x_vals[1]-x_vals[0], alpha=0.7, 
              label=f"Exposure: {result['exposure_ms']:.2f}ms")
        
        # Mark key percentiles
        p5 = result["results"]["p5"]
        p95 = result["results"]["p95"]
        
        if result["results"]["bin_edges"].max() > 255:
            # Scale percentiles to percentage of max
            p5_scaled = p5 / 65535 * 100
            p95_scaled = p95 / 65535 * 100
        else:
            p5_scaled = p5
            p95_scaled = p95
        
        ax.axvline(x=p5_scaled, color='green', linestyle='--', 
                  label=f'5th percentile: {p5:.0f}')
        ax.axvline(x=p95_scaled, color='red', linestyle='--', 
                  label=f'95th percentile: {p95:.0f}')
        
        # Add key metrics
        mean = result["results"]["mean_intensity"]
        contrast = result["results"]["contrast"]
        saturated = result["results"]["saturated_percentage"]
        score = result["score"]
        
        if result["results"]["bin_edges"].max() > 255:
            # Scale mean to percentage of max
            mean_scaled = mean / 65535 * 100
        else:
            mean_scaled = mean
        
        ax.axvline(x=mean_scaled, color='blue', linestyle='-', 
                  label=f'Mean: {mean:.0f}')
        
        # Add text with metrics
        ax.text(0.98, 0.95, 
               f"Score: {score:.1f}\n"
               f"Contrast: {contrast:.3f}\n"
               f"Saturated: {saturated:.2f}%",
               transform=ax.transAxes, ha='right', va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.set_title(f"Histogram for {Path(result['path']).name}")
        ax.set_xlabel(x_label)
        ax.set_ylabel("Frequency")
        ax.set_yscale('log')
        ax.set_ylim(bottom=0.1)
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("top_exposure_histograms.png")
    print("Top exposure histograms saved to top_exposure_histograms.png")
    
    return fig

def print_recommendations(calibration_results):
    """
    Print exposure calibration recommendations.
    
    Args:
        calibration_results: Results from calibrate_exposure
    """
    if not calibration_results:
        print("No calibration results to generate recommendations.")
        return
    
    optimal_result = calibration_results["optimal_result"]
    top_results = calibration_results["top_results"]
    all_results = calibration_results["all_results"]
    
    print("\n" + "="*50)
    print("EXPOSURE CALIBRATION RECOMMENDATIONS")
    print("="*50)
    
    print(f"\nOPTIMAL EXPOSURE: {optimal_result['exposure_us']}us ({optimal_result['exposure_ms']:.2f}ms)")
    print(f"Optimization score: {optimal_result['score']:.1f}/100")
    print(f"Mean intensity: {optimal_result['results']['mean_intensity']:.1f}")
    print(f"Contrast (σ/μ): {optimal_result['results']['contrast']:.4f}")
    print(f"Saturated pixels: {optimal_result['results']['saturated_percentage']:.4f}%")
    print(f"Dynamic range used: {optimal_result['results']['dynamic_range']:.1f}%")
    print(f"Image file: {Path(optimal_result['path']).name}")
    
    print("\nAlternative recommended exposures:")
    for i, result in enumerate(top_results[1:], 1):  # Skip the first one (already shown)
        print(f"{i}. {result['exposure_us']}us ({result['exposure_ms']:.2f}ms) - Score: {result['score']:.1f}")
    
    print("\nAll exposures analyzed (sorted by score):")
    print("-" * 85)
    print(f"{'Exposure (ms)':<15} {'Score':<8} {'Mean':<10} {'Contrast':<10} {'Saturated %':<12} {'Dynamic Range %':<15}")
    print("-" * 85)
    
    # Sort all results by score, descending
    sorted_results = sorted(all_results, key=lambda x: x["score"], reverse=True)
    for result in sorted_results:
        print(f"{result['exposure_ms']:<15.2f} {result['score']:<8.1f} "
              f"{result['results']['mean_intensity']:<10.1f} "
              f"{result['results']['contrast']:<10.4f} "
              f"{result['results']['saturated_percentage']:<12.4f} "
              f"{result['results']['dynamic_range']:<15.1f}")
    
    print("\nDetailed analysis of problematic exposures:")
    for result in all_results:
        # Report issues if any
        issues = []
        if result['results']['saturated_percentage'] > 0.1:
            issues.append(f"High saturation ({result['results']['saturated_percentage']:.2f}%)")
        
        if result['results']['dynamic_range'] < 25:
            issues.append(f"Low dynamic range utilization ({result['results']['dynamic_range']:.1f}%)")
        elif result['results']['dynamic_range'] > 70:
            issues.append(f"Excessive dynamic range ({result['results']['dynamic_range']:.1f}%)")
        
        if result['results']['contrast'] < 0.15:
            issues.append(f"Low contrast ({result['results']['contrast']:.4f})")
        elif result['results']['contrast'] > 1.0:
            issues.append(f"Extremely high contrast ({result['results']['contrast']:.4f})")
        elif result['results']['contrast'] > 0.6:
            issues.append(f"High contrast ({result['results']['contrast']:.4f})")
        
        if issues:
            print(f"\n{result['exposure_ms']:.2f}ms ({Path(result['path']).name}):")
            for issue in issues:
                print(f"  - {issue}")
    
    print("\nRecommendations for your experiment:")
    print("1. Use the optimal exposure time for most reliable speckle contrast measurements.")
    print("2. If you're seeing saturation during your experiment, consider using the next lower exposure.")
    print("3. For time-sensitive measurements, you may use a shorter exposure but expect lower contrast.")
    
    # Generate specific advice based on results
    if all(r['results']['saturated_percentage'] > 1 or r['results']['contrast'] > 1.0 for r in all_results):
        print("\nNOTE: All available images have either high saturation or very high contrast.")
        print("You may need to capture new images with intermediate exposure times.")
    
    if optimal_result['results']['saturated_percentage'] > 0:
        print("\nCAUTION: Even the optimal exposure shows some saturation.")
        print("Consider reducing laser power if possible.")
    
    if optimal_result['results']['contrast'] > 1.0:
        print("\nWARNING: High speckle contrast in the optimal image suggests very low signal.")
        print("Consider increasing exposure time or laser power.")
    
    if optimal_result['results']['contrast'] < 0.15:
        print("\nWARNING: Low speckle contrast detected even at optimal exposure.")
        print("Possible causes:")
        print("- Insufficient laser coherence")
        print("- Excessive sample movement")
        print("- Improper focusing of imaging system")
    
    print("\nThese recommendations are based on static speckle analysis.")
    print("For dynamic measurements, you may need to adjust based on your specific sample.")
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate exposure time for laser speckle imaging")
    parser.add_argument("--pattern", default="captured_image_*us.raw", 
                        help="Glob pattern to find raw image files")
    parser.add_argument("--width", type=int, default=1920, help="Image width in pixels")
    parser.add_argument("--height", type=int, default=600, help="Image height in pixels")
    parser.add_argument("--dtype", choices=["uint8", "uint16"], default="uint16", 
                        help="Image data type (default: uint16)")
    parser.add_argument("--roi", type=float, default=0.5,
                        help="Fraction of image dimensions to use as ROI (default: 0.5)")
    parser.add_argument("--specific-files", nargs="*", 
                        help="Specific files to analyze instead of using pattern")
    
    args = parser.parse_args()
    
    # Convert dtype string to numpy dtype
    dtype_map = {"uint8": np.uint8, "uint16": np.uint16}
    dtype = dtype_map[args.dtype]
    
    # Get list of files
    if args.specific_files:
        image_paths = args.specific_files
    else:
        image_paths = glob.glob(args.pattern)
    
    if not image_paths:
        print(f"No image files found matching the pattern: {args.pattern}")
        exit(1)
    
    print(f"Found {len(image_paths)} image files for calibration.")
    
    # Run calibration
    calibration_results = calibrate_exposure(
        image_paths, args.width, args.height, dtype, args.roi)
    
    # Plot results
    if calibration_results:
        plot_calibration_results(calibration_results)
        print_recommendations(calibration_results) 