import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
import sys
import os

# Ensure that our other analyzer modules are importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import functions from our analyzer modules
from saturation_pixel_count_analyzer import (
    read_raw_image, create_central_roi_mask, 
    analyze_saturation_by_pixel_count
)
from histogram_saturation_analyzer import analyze_saturation_by_histogram

def analyze_image_both_methods(img, saturation_threshold=0.98, max_saturated_pixels=400, 
                             high_intensity_threshold=0.9, critical_bin_threshold=0.1, 
                             roi_fraction=0.5):
    """
    Analyze an image using both pixel count and histogram methods.
    
    Args:
        img: Image as numpy array
        saturation_threshold: Threshold for pixel count method
        max_saturated_pixels: Maximum allowed saturated pixels
        high_intensity_threshold: Threshold for histogram method
        critical_bin_threshold: Critical bin threshold for histogram method
        roi_fraction: Fraction of image to use as ROI
    
    Returns:
        Dictionary containing analysis results from both methods
    """
    # Run pixel count analysis
    pixel_count_results = analyze_saturation_by_pixel_count(
        img, saturation_threshold, max_saturated_pixels, roi_fraction)
    
    # Run histogram analysis
    histogram_results = analyze_saturation_by_histogram(
        img, high_intensity_threshold, critical_bin_threshold, roi_fraction)
    
    # Combine results
    return {
        "pixel_count": pixel_count_results,
        "histogram": histogram_results,
        "is_saturated": (pixel_count_results["is_saturated"] or 
                         histogram_results["is_saturated"]),
        "combined_score": calculate_combined_score(pixel_count_results, histogram_results)
    }

def calculate_combined_score(pixel_count_results, histogram_results):
    """
    Calculate a combined score to rank images for optimal exposure.
    Lower is better (less saturation, better exposure).
    
    Args:
        pixel_count_results: Results from pixel count analysis
        histogram_results: Results from histogram analysis
    
    Returns:
        Float score (lower is better)
    """
    # Score components (all normalized to 0-1 range)
    # Start with saturation indicators (higher = worse)
    saturated_pixel_score = min(1.0, pixel_count_results["saturated_pixels"] / 1000)
    highest_bin_score = min(1.0, histogram_results["highest_bin_percentage"] / 10)
    near_max_score = min(1.0, histogram_results["near_max_percentage"] / 10)
    
    # Add utilization of dynamic range (lower = worse)
    # We want to maximize this, so subtract from 1
    if histogram_results["percentile_95"] > 0:
        p95_score = 1.0 - min(1.0, histogram_results["percentile_95"] / 
                            (0.9 * (65535 if img.dtype == np.uint16 else 255)))
    else:
        p95_score = 1.0  # Worst score for zero
    
    # Calculate combined weighted score
    # Higher weights for saturation indicators
    score = (
        0.4 * saturated_pixel_score +
        0.3 * highest_bin_score +
        0.2 * near_max_score +
        0.1 * p95_score
    )
    
    return score

def find_optimal_exposure(image_paths, width=None, height=None, dtype=np.uint16,
                         saturation_threshold=0.98, max_saturated_pixels=400, 
                         high_intensity_threshold=0.9, critical_bin_threshold=0.1,
                         roi_fraction=0.5):
    """
    Find the optimal exposure time from a set of images using both analysis methods.
    
    Args:
        image_paths: List of paths to raw image files
        width, height, dtype: Image parameters
        saturation_threshold, max_saturated_pixels: Pixel count method parameters
        high_intensity_threshold, critical_bin_threshold: Histogram method parameters
        roi_fraction: Fraction of image to use as ROI
    
    Returns:
        Tuple of (optimal path, exposure time, combined results)
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
        
        print(f"Analyzing {Path(path_str).name} (exposure: {exposure_ms}ms)")
        
        # Read and analyze image
        img = read_raw_image(path, width, height, dtype)
        results = analyze_image_both_methods(
            img, saturation_threshold, max_saturated_pixels,
            high_intensity_threshold, critical_bin_threshold, roi_fraction)
        
        # Store results
        exposure_times.append(exposure_ms)
        analysis_results.append({
            "path": path,
            "exposure_ms": exposure_ms,
            "results": results
        })
    
    # Find non-saturated images
    valid_exposures = [r for r in analysis_results if not r["results"]["is_saturated"]]
    
    if valid_exposures:
        # Among non-saturated images, find the one with the best exposure (highest that's not saturated)
        # Sort by exposure time (descending)
        optimal = sorted(valid_exposures, key=lambda x: x["exposure_ms"], reverse=True)[0]
        message = "Found optimal exposure (highest non-saturated)"
    else:
        # If all are saturated, find the least saturated one based on combined score
        optimal = sorted(analysis_results, key=lambda x: x["results"]["combined_score"])[0]
        message = "WARNING: All images appear saturated. Selected least saturated."
    
    # Print results
    print(f"\n{message}")
    print(f"Optimal image: {Path(optimal['path']).name}")
    print(f"Exposure time: {optimal['exposure_ms']}ms")
    print(f"Saturated pixels: {optimal['results']['pixel_count']['saturated_pixels']}")
    print(f"Highest bin percentage: {optimal['results']['histogram']['highest_bin_percentage']:.2f}%")
    print(f"Combined score: {optimal['results']['combined_score']:.4f} (lower is better)")
    
    return optimal["path"], optimal["exposure_ms"], optimal["results"]

def plot_exposure_comparison(analysis_results, best_path=None):
    """
    Plot exposure comparison across all analyzed images.
    
    Args:
        analysis_results: List of analysis results with exposure times
        best_path: Path to the optimal image (to highlight in plots)
    """
    exposure_times = [r["exposure_ms"] for r in analysis_results]
    saturated_pixels = [r["results"]["pixel_count"]["saturated_pixels"] for r in analysis_results]
    highest_bin_percentages = [r["results"]["histogram"]["highest_bin_percentage"] for r in analysis_results]
    mean_intensities = [r["results"]["histogram"]["mean_intensity"] for r in analysis_results]
    combined_scores = [r["results"]["combined_score"] for r in analysis_results]
    is_saturated = [r["results"]["is_saturated"] for r in analysis_results]
    
    # Create figure for comparison plots
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    
    # Helper function to highlight the optimal point
    def highlight_optimal(ax, x, y, saturated):
        for i, (xi, yi, sat) in enumerate(zip(x, y, saturated)):
            if analysis_results[i]["path"] == best_path:
                marker = 'X'
                markersize = 12
                color = 'lime' if not sat else 'orange'
                label = "Optimal exposure"
            else:
                marker = 'o'
                markersize = 8
                color = 'green' if not sat else 'red'
                label = None
            ax.plot(xi, yi, marker=marker, markersize=markersize, 
                   color=color, markeredgecolor='black', alpha=0.8, label=label)
        
        # Add a single legend entry for optimal
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys())
    
    # Plot 1: Saturated pixels vs exposure time
    ax1 = axs[0, 0]
    x = exposure_times
    y = saturated_pixels
    highlight_optimal(ax1, x, y, is_saturated)
    
    # Add threshold line
    ax1.axhline(y=400, color='r', linestyle='--', label="Saturation threshold (400 pixels)")
    ax1.set_title("Saturated Pixels vs Exposure Time")
    ax1.set_xlabel("Exposure Time (ms)")
    ax1.set_ylabel("Saturated Pixels")
    ax1.set_xscale('log')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Highest bin percentage vs exposure time
    ax2 = axs[0, 1]
    x = exposure_times
    y = highest_bin_percentages
    highlight_optimal(ax2, x, y, is_saturated)
    
    # Add threshold line
    ax2.axhline(y=0.1, color='r', linestyle='--', label="Saturation threshold (0.1%)")
    ax2.set_title("Highest Bin % vs Exposure Time")
    ax2.set_xlabel("Exposure Time (ms)")
    ax2.set_ylabel("Highest Bin %")
    ax2.set_xscale('log')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Plot 3: Mean intensity vs exposure time
    ax3 = axs[1, 0]
    x = exposure_times
    y = mean_intensities
    highlight_optimal(ax3, x, y, is_saturated)
    
    ax3.set_title("Mean Intensity vs Exposure Time")
    ax3.set_xlabel("Exposure Time (ms)")
    ax3.set_ylabel("Mean Intensity")
    ax3.set_xscale('log')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Combined score vs exposure time
    ax4 = axs[1, 1]
    x = exposure_times
    y = combined_scores
    highlight_optimal(ax4, x, y, is_saturated)
    
    ax4.set_title("Combined Score vs Exposure Time\n(Lower is better)")
    ax4.set_xlabel("Exposure Time (ms)")
    ax4.set_ylabel("Combined Score")
    ax4.set_xscale('log')
    ax4.grid(True, alpha=0.3)
    
    # Add overall title
    plt.suptitle("Exposure Comparison Across Images", fontsize=16)
    
    plt.tight_layout()
    plt.savefig("exposure_comparison.png")
    print("Exposure comparison saved to exposure_comparison.png")
    
    return fig

def plot_comprehensive_results(img, combined_results, image_path):
    """
    Plot comprehensive results from both analysis methods.
    
    Args:
        img: Image as numpy array
        combined_results: Results from both analysis methods
        image_path: Path to the image file
    """
    pixel_results = combined_results["pixel_count"]
    hist_results = combined_results["histogram"]
    
    fig = plt.figure(figsize=(16, 12))
    gs = plt.GridSpec(3, 2, figure=fig)
    
    # Plot original image with ROI overlay
    ax1 = fig.add_subplot(gs[0, 0])
    if img.dtype == np.uint16:
        ax1.imshow(pixel_results["img_8bit"], cmap='gray', vmin=0, vmax=255)
    else:
        ax1.imshow(img, cmap='gray', vmin=0, vmax=255)
    
    # Show ROI as a rectangle overlay
    height, width = img.shape
    roi_fraction = 0.5  # Matching the default
    
    roi_height = int(height * roi_fraction)
    roi_width = int(width * roi_fraction)
    
    y_start = (height - roi_height) // 2
    y_end = y_start + roi_height
    x_start = (width - roi_width) // 2
    x_end = x_start + roi_width
    
    import matplotlib.patches as patches
    rect = patches.Rectangle((x_start, y_start), roi_width, roi_height, 
                             linewidth=2, edgecolor='g', facecolor='none')
    ax1.add_patch(rect)
    
    ax1.set_title(f"Original Image with ROI\n{Path(image_path).name}")
    ax1.axis('off')
    
    # Plot saturation map from pixel count method
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(pixel_results["saturation_map"])
    ax2.set_title(f"Saturation Map (Pixel Count Method)\n"
                 f"{pixel_results['saturated_pixels']} saturated pixels "
                 f"({pixel_results['saturated_percentage']:.2f}%)")
    ax2.axis('off')
    
    # Plot histogram
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.bar(hist_results["bin_centers"], hist_results["histogram_percentage"], 
           width=2, alpha=0.7, color='blue')
    
    # Add line at high intensity threshold
    high_threshold_8bit = int(255 * 0.9)  # 90% of max in 8-bit scale
    ax3.axvline(x=high_threshold_8bit, color='r', linestyle='--', 
                label=f'High Intensity Threshold ({high_threshold_8bit})')
    
    # Highlight the highest bin if it's significant
    if hist_results["highest_bin_percentage"] > 0.1:
        ax3.bar([255], [hist_results["highest_bin_percentage"]], width=2, alpha=0.9, color='red', 
                label=f'Highest Bin: {hist_results["highest_bin_percentage"]:.2f}%')
    
    ax3.set_title("ROI Histogram")
    ax3.set_xlabel("Pixel Intensity")
    ax3.set_ylabel("Percentage of Pixels (%)")
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Use log scale for better visualization
    ax3.set_yscale('log')
    ax3.set_ylim(bottom=0.001)  # Minimum y value to avoid log(0)
    
    # Plot cumulative histogram
    ax4 = fig.add_subplot(gs[1, 1])
    cumulative_hist = np.cumsum(hist_results["histogram_percentage"])
    ax4.plot(hist_results["bin_centers"], cumulative_hist, 'g-', linewidth=2)
    
    # Mark 95th percentile
    p95_8bit = min(255, int(hist_results["percentile_95"] / 256) if img.dtype == np.uint16 else int(hist_results["percentile_95"]))
    ax4.axvline(x=p95_8bit, color='orange', linestyle='--', 
               label=f'95th Percentile: {p95_8bit}')
    ax4.axhline(y=95, color='orange', linestyle=':')
    
    # Mark high intensity threshold
    ax4.axvline(x=high_threshold_8bit, color='r', linestyle='--', 
               label=f'High Intensity Threshold ({high_threshold_8bit})')
    
    ax4.set_title("Cumulative Histogram")
    ax4.set_xlabel("Pixel Intensity")
    ax4.set_ylabel("Cumulative Percentage (%)")
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    # Add combined result summary at bottom
    ax5 = fig.add_subplot(gs[2, :])
    ax5.axis('off')  # Turn off axes
    
    # Generate summary text
    pixel_saturated = "SATURATED" if pixel_results["is_saturated"] else "Not saturated"
    hist_saturated = "SATURATED" if hist_results["is_saturated"] else "Not saturated"
    combined_saturated = "SATURATED" if combined_results["is_saturated"] else "NOT SATURATED"
    
    summary_text = f"""
    COMBINED ANALYSIS RESULTS:
    
    Pixel Count Method: {pixel_saturated}
    - Saturated pixels in ROI: {pixel_results['saturated_pixels']} (threshold: 400)
    - Saturated percentage: {pixel_results['saturated_percentage']:.2f}%
    
    Histogram Method: {hist_saturated}
    - Highest bin percentage: {hist_results['highest_bin_percentage']:.2f}% (threshold: 0.1%)
    - High intensity sum: {hist_results['high_intensity_sum']:.2f}%
    - Mean intensity: {hist_results['mean_intensity']:.2f}
    - 95th percentile: {hist_results['percentile_95']:.2f}
    
    OVERALL STATUS: {combined_saturated}
    Combined score: {combined_results['combined_score']:.4f} (lower is better)
    """
    
    # Add the text to the figure
    ax5.text(0.5, 0.5, summary_text, ha='center', va='center', 
            bbox=dict(facecolor='orange' if combined_results["is_saturated"] else 'lightgreen', 
                     alpha=0.2, boxstyle='round,pad=1'), 
            fontsize=12, family='monospace')
    
    plt.tight_layout()
    plt.savefig(f"{image_path}.comprehensive_analysis.png")
    print(f"Comprehensive analysis saved to {image_path}.comprehensive_analysis.png")
    
    # Show the plot
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find optimal exposure time using multiple analysis methods")
    parser.add_argument("image_path", nargs='+', help="Path(s) to the raw image file(s)")
    parser.add_argument("--width", type=int, default=1920, help="Image width in pixels")
    parser.add_argument("--height", type=int, default=1200, help="Image height in pixels")
    parser.add_argument("--dtype", choices=["uint8", "uint16"], default="uint16", 
                        help="Image data type (default: uint16)")
    parser.add_argument("--roi", type=float, default=0.5,
                        help="Fraction of image dimensions to use as ROI (default: 0.5)")
    parser.add_argument("--pixel-threshold", type=float, default=0.98,
                        help="Saturation threshold for pixel count method (default: 0.98)")
    parser.add_argument("--max-pixels", type=int, default=400,
                        help="Maximum allowed saturated pixels (default: 400)")
    parser.add_argument("--hist-threshold", type=float, default=0.9,
                        help="High intensity threshold for histogram method (default: 0.9)")
    parser.add_argument("--bin-threshold", type=float, default=0.1,
                        help="Critical bin threshold for histogram method (default: 0.1)")
    
    args = parser.parse_args()
    
    # Convert dtype string to numpy dtype
    dtype_map = {"uint8": np.uint8, "uint16": np.uint16}
    dtype = dtype_map[args.dtype]
    
    if len(args.image_path) > 1:
        # Find optimal exposure
        optimal_path, optimal_exposure, optimal_results = find_optimal_exposure(
            args.image_path, args.width, args.height, dtype,
            args.pixel_threshold, args.max_pixels,
            args.hist_threshold, args.bin_threshold,
            args.roi)
        
        # Read the optimal image again
        optimal_img = read_raw_image(optimal_path, args.width, args.height, dtype)
        
        # Plot comprehensive results for the optimal image
        plot_comprehensive_results(optimal_img, optimal_results, optimal_path)
        
        # Build list of all analysis results for comparison plot
        all_results = []
        for path in args.image_path:
            img = read_raw_image(path, args.width, args.height, dtype)
            results = analyze_image_both_methods(
                img, args.pixel_threshold, args.max_pixels,
                args.hist_threshold, args.bin_threshold, args.roi)
            
            # Extract exposure time from filename
            try:
                exposure_us = int(str(path).split('_')[-1].split('us')[0])
                exposure_ms = exposure_us / 1000
            except:
                exposure_ms = len(all_results) + 1
            
            all_results.append({
                "path": path,
                "exposure_ms": exposure_ms,
                "results": results
            })
        
        # Plot comparison of all exposures
        plot_exposure_comparison(all_results, optimal_path)
        
    else:
        # Just analyze the single image
        image_path = args.image_path[0]
        img = read_raw_image(image_path, args.width, args.height, dtype)
        results = analyze_image_both_methods(
            img, args.pixel_threshold, args.max_pixels,
            args.hist_threshold, args.bin_threshold, args.roi)
        
        # Print summary
        print("\nComprehensive Image Analysis Summary:")
        print(f"Image: {image_path}")
        print(f"Pixel count method: {'SATURATED' if results['pixel_count']['is_saturated'] else 'Not saturated'}")
        print(f"Histogram method: {'SATURATED' if results['histogram']['is_saturated'] else 'Not saturated'}")
        print(f"Overall status: {'SATURATED' if results['is_saturated'] else 'NOT SATURATED'}")
        print(f"Combined score: {results['combined_score']:.4f} (lower is better)")
        
        # Plot comprehensive results
        plot_comprehensive_results(img, results, image_path) 