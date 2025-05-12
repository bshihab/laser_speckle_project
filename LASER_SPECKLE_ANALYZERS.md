# Laser Speckle Image Analysis Tools

This collection of tools is designed for analyzing laser speckle images to determine optimal exposure and detect saturation using different methods. The tools focus on the central region of the image (ROI) to provide appropriate analysis for laser speckle imaging.

## Available Tools

Three different analysis tools are available, each with specific purposes:

1. **Pixel Count Analyzer** (`saturation_pixel_count_analyzer.py`): Determines saturation by counting the number of saturated pixels in the central ROI. An image is considered saturated if more than 400 pixels exceed the saturation threshold.

2. **Histogram Analyzer** (`histogram_saturation_analyzer.py`): Uses histogram analysis to detect saturation patterns. Looks for peaks at high intensity levels which indicate saturation.

3. **Optimal Exposure Finder** (`optimal_exposure_finder.py`): Combines both methods to analyze a set of images with different exposure times and determine which one provides the best exposure without saturation.

## Usage Instructions

### Pixel Count Analyzer

```bash
python saturation_pixel_count_analyzer.py [image_path] [options]
```

Options:
- `--width`: Image width in pixels (default: 1920)
- `--height`: Image height in pixels (default: 1200)
- `--dtype`: Image data type (uint8 or uint16, default: uint16)
- `--roi`: Fraction of image dimensions to use as ROI (default: 0.5)
- `--threshold`: Saturation threshold as fraction of max value (default: 0.98)
- `--max-pixels`: Maximum allowed saturated pixels (default: 400)
- `--find-optimal`: Find optimal exposure time from multiple images

Examples:
```bash
# Analyze a single image
python saturation_pixel_count_analyzer.py captured_image_50000us.raw

# Find optimal exposure from multiple images
python saturation_pixel_count_analyzer.py captured_image_*.raw --find-optimal
```

### Histogram Analyzer

```bash
python histogram_saturation_analyzer.py [image_path] [options]
```

Options:
- `--width`: Image width in pixels (default: 1920)
- `--height`: Image height in pixels (default: 1200)
- `--dtype`: Image data type (uint8 or uint16, default: uint16)
- `--roi`: Fraction of image dimensions to use as ROI (default: 0.5)
- `--high-threshold`: High intensity threshold (default: 0.9)
- `--bin-threshold`: Critical bin threshold for saturation detection (default: 0.1)
- `--find-optimal`: Find optimal exposure time from multiple images

Examples:
```bash
# Analyze a single image
python histogram_saturation_analyzer.py captured_image_50000us.raw

# Find optimal exposure from multiple images
python histogram_saturation_analyzer.py captured_image_*.raw --find-optimal
```

### Optimal Exposure Finder (Combined Method)

```bash
python optimal_exposure_finder.py [image_path] [options]
```

Options:
- `--width`: Image width in pixels (default: 1920)
- `--height`: Image height in pixels (default: 1200)
- `--dtype`: Image data type (uint8 or uint16, default: uint16)
- `--roi`: Fraction of image dimensions to use as ROI (default: 0.5)
- `--pixel-threshold`: Threshold for pixel count method (default: 0.98)
- `--max-pixels`: Maximum allowed saturated pixels (default: 400)
- `--hist-threshold`: Threshold for histogram method (default: 0.9)
- `--bin-threshold`: Critical bin threshold for histogram method (default: 0.1)

Example:
```bash
# Find optimal exposure from all captured images
python optimal_exposure_finder.py captured_image_*.raw
```

## Analysis Methods Explained

### Pixel Count Method

This method counts the number of pixels in the central ROI that exceed a saturation threshold (default: 98% of maximum value). If more than 400 pixels are saturated, the image is considered overexposed.

This method is effective for detecting small areas of saturation that might be missed by histogram analysis.

### Histogram Method

This method analyzes the histogram distribution of pixel intensities in the central ROI. It looks for:

1. Peaks at the highest intensity bin (indicating saturation)
2. A high percentage of pixels above 90% of maximum intensity

An image is considered saturated if either:
- The highest bin contains more than 0.1% of all pixels
- More than 10% of pixels are in the high-intensity region

This method is good at detecting overall exposure quality and catching cases where many pixels are near (but not at) the saturation point.

### Combined Method

The optimal exposure finder combines both methods and adds:

1. A scoring system to rank images by exposure quality
2. Comparative plots to visualize exposure differences
3. Comprehensive analysis of the optimal image

The goal is to find the highest exposure time that doesn't cause saturation, maximizing signal without clipping.

## Output Files

Each tool generates analysis plots that are saved as PNG files:

- Pixel Count: `[image_path].saturation_analysis.png`
- Histogram: `[image_path].histogram_analysis.png`
- Combined Method: 
  - `[image_path].comprehensive_analysis.png`
  - `exposure_comparison.png`

## Notes

- These tools assume raw image files in a simple binary format
- Exposure time is extracted from filenames (format: `captured_image_XXXXXus.raw`)
- All tools focus on the central region of the image by default (50% of dimensions)
- Thresholds can be adjusted based on specific experimental needs 