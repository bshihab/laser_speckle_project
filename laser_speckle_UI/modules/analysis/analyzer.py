#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import numpy as np
import traceback
from pathlib import Path
import time
from datetime import datetime

# Import analysis modules
# Add parent directory to path to ensure imports work
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import from the parent directory
from histogram_saturation_analyzer import analyze_saturation_by_histogram
from saturation_pixel_count_analyzer import analyze_saturation_by_pixel_count
from contrast_analyzer import analyze_contrast

# Import from the utils module
from laser_speckle_UI.modules.utils.image_utils import create_radial_weight_mask

class ImageAnalyzer:
    """
    Class for analyzing laser speckle images with different methods
    """
    
    def __init__(self, logger_callback=None):
        """
        Initialize the analyzer
        
        Args:
            logger_callback: Function to call for logging messages
        """
        self.logger = logger_callback if logger_callback else print
        self.roi_info = None  # (center_y, center_x, radius)
        
        # Initialize tracking variables for auto adjustment
        self.prev_high_sum = None
        self.stable_count = 0
        self.last_mean_values = []
        self.last_adjustment_values = []
    
    def log(self, message, error=False):
        """Log a message using the provided logger callback"""
        if self.logger:
            self.logger(message, error)
    
    def set_roi(self, roi_info):
        """
        Set the region of interest
        
        Args:
            roi_info: Tuple of (center_y, center_x, radius)
        """
        self.roi_info = roi_info
        self.log(f"ROI set to center=({roi_info[0]}, {roi_info[1]}), radius={roi_info[2]}")
    
    def reset_roi(self):
        """Reset the region of interest"""
        self.roi_info = None
        self.log("ROI reset")
    
    def create_roi_mask(self, shape):
        """
        Create a circular mask for the ROI
        
        Args:
            shape: Shape of the image (height, width)
            
        Returns:
            numpy.ndarray: Binary mask (1 inside ROI, 0 outside)
        """
        if self.roi_info is None:
            # No ROI set, return a mask that covers the entire image
            return np.ones(shape, dtype=np.uint8)
            
        height, width = shape
        mask = np.zeros((height, width), dtype=np.uint8)
        center_y, center_x, radius = self.roi_info
        
        # Create coordinate grids
        y, x = np.ogrid[:height, :width]
        
        # Calculate distance from center
        dist_from_center = np.sqrt((y - center_y)**2 + (x - center_x)**2)
        
        # Create circular mask
        mask[dist_from_center <= radius] = 1
        
        return mask
    
    def analyze_image(self, img, method='histogram', auto_roi=False):
        """
        Analyze an image using the specified method
        
        Args:
            img: Input image as numpy array
            method: Analysis method ('histogram', 'pixel_count', or 'contrast')
            auto_roi: Automatically determine ROI if none is set
            
        Returns:
            dict: Analysis results
        """
        if img is None:
            self.log("Cannot analyze: No image data", error=True)
            return None
            
        try:
            # Create ROI mask if ROI is set
            if self.roi_info is not None:
                roi_mask = self.create_roi_mask(img.shape)
            else:
                # Use full image
                roi_mask = np.ones(img.shape, dtype=np.uint8)
                
                # Auto-determine ROI if requested
                if auto_roi:
                    # Simple auto ROI: use center of image with radius of 1/3 of the smaller dimension
                    height, width = img.shape
                    center_y, center_x = height // 2, width // 2
                    radius = min(height, width) // 3
                    self.roi_info = (center_y, center_x, radius)
                    roi_mask = self.create_roi_mask(img.shape)
            
            # Apply the appropriate analysis method
            if method == 'histogram':
                # Create weight mask centered on ROI
                weight_mask = None
                if self.roi_info:
                    center_y, center_x, radius = self.roi_info
                    weight_mask = create_radial_weight_mask(img.shape, center=(center_y, center_x), sigma=radius)
                
                # Call histogram analysis
                results = analyze_saturation_by_histogram(img, weight_mask=weight_mask)
                self.log(f"Histogram analysis completed. Mean intensity: {results.get('weighted_mean', 0):.1f}")
                
            elif method == 'pixel_count':
                # Create weight mask centered on ROI
                weight_mask = None
                if self.roi_info:
                    center_y, center_x, radius = self.roi_info
                    weight_mask = create_radial_weight_mask(img.shape, center=(center_y, center_x), sigma=radius)
                
                # Call pixel count analysis
                results = analyze_saturation_by_pixel_count(img, weight_mask=weight_mask)
                self.log(f"Pixel count analysis completed. Saturation: {results.get('saturation_percentage', 0):.2f}%")
                
            elif method == 'contrast':
                # Create weight mask centered on ROI
                weight_mask = None
                if self.roi_info:
                    center_y, center_x, radius = self.roi_info
                    weight_mask = create_radial_weight_mask(img.shape, center=(center_y, center_x), sigma=radius)
                
                # Call contrast analysis
                results = analyze_contrast(img, weight_mask=weight_mask)
                self.log(f"Contrast analysis completed. Contrast ratio: {results.get('global_contrast', 0):.3f}")
                
            else:
                self.log(f"Unknown analysis method: {method}", error=True)
                return None
            
            # Add metadata to results
            results['analysis_method'] = method
            results['timestamp'] = datetime.now().isoformat()
            results['roi_info'] = self.roi_info
            
            return results
            
        except Exception as e:
            self.log(f"Error analyzing image: {str(e)}", error=True)
            traceback.print_exc()
            return None
    
    def calculate_adjustment(self, results, method, current_value):
        """
        Calculate how much to adjust the laser current based on analysis results
        
        Args:
            results: Analysis results dictionary
            method: Analysis method used
            current_value: Current laser intensity value (percentage)
            
        Returns:
            float: Adjustment value (percentage points to add/subtract)
        """
        if results is None:
            return 0.0
            
        # Store current value for reference in calculations
        self.current_value = current_value
        
        # Different calculation based on analysis method
        if method == 'histogram':
            return self._calculate_histogram_adjustment(results)
        elif method == 'pixel_count':
            return self._calculate_pixel_count_adjustment(results)
        elif method == 'contrast':
            return self._calculate_contrast_adjustment(results)
        else:
            self.log(f"Unknown analysis method for adjustment: {method}", error=True)
            return 0.0
    
    def _calculate_histogram_adjustment(self, results):
        """Calculate adjustment based on histogram analysis"""
        adjustment = 0.0
        
        # Add hysteresis - don't adjust unless change would be significant
        min_adjustment_threshold = 0.3  # Reduced to allow finer adjustments
        
        # Get key metrics for balanced decision-making
        highest_bin = results.get("highest_bin_percentage", 0)
        weighted_sat = results.get("weighted_saturation_percentage", 0)
        high_sum = results.get("high_intensity_sum", 0)
        weighted_mean = results.get("weighted_mean", 0)
        max_intensity = results.get("max_intensity", 255)  # Default to 8-bit
        
        # Force 8-bit processing
        is_16bit = False
        
        # Log the key metrics for debugging
        self.log(f"Histogram analysis metrics - Mean: {weighted_mean:.1f} (raw: {results.get('unweighted_mean', 0):.1f}), High sum: {high_sum:.2f}% (raw: {results.get('unweighted_saturated_percentage', 0):.2f}%), Highest bin: {highest_bin:.2f}%, Bit depth: 8-bit")
        
        # Track current measurements for stability
        current_high_sum = high_sum
        current_mean = weighted_mean
        
        # Normalize mean intensity to 0-100 range (8-bit)
        norm_mean = (weighted_mean / 255) * 100
        
        # Define optimal mean range (wider range based on observed good results)
        optimal_mean_min = 40
        optimal_mean_max = 60
        
        # Define optimal saturation range (increased based on observed good results)
        optimal_sat_min = 35
        optimal_sat_max = 45
        
        # Log additional normalized metrics for better debugging
        self.log(f"Normalized metrics - Mean: {norm_mean:.1f}% (optimal range: {optimal_mean_min}-{optimal_mean_max}%), Saturation: {high_sum:.2f}% (raw: {results.get('unweighted_saturated_percentage', 0):.2f}%) (optimal range: {optimal_sat_min}-{optimal_sat_max}%)")
        
        # Check if we're in a stable range
        if self.prev_high_sum is not None:
            # Calculate the change since last measurement
            delta_sum = abs(current_high_sum - self.prev_high_sum)
            
            if delta_sum < 0.1:  # If measurement is stable
                self.stable_count += 1
                self.log(f"Stable reading #{self.stable_count}: high_sum={high_sum:.3f}, mean={norm_mean:.1f}%")
            else:
                # Reset stability counter if readings are fluctuating
                self.stable_count = 0
                self.log(f"Unstable reading: high_sum={high_sum:.3f}, delta={delta_sum:.3f}")
        
        # Store current values for next comparison
        self.prev_high_sum = current_high_sum
        
        # Append current mean to list of recent values (limit to last 5)
        self.last_mean_values.append(norm_mean)
        if len(self.last_mean_values) > 5:
            self.last_mean_values.pop(0)
        
        # DECISION LOGIC - CONSIDERS BOTH MEAN AND SATURATION SIMULTANEOUSLY
        
        # CASE 0: EXTREMELY DARK - Aggressive increase for completely dark images
        if norm_mean < 2.0 or high_sum < 0.01:  # Near-zero mean or extremely few bright pixels
            # Scale adjustment based on how extreme the darkness is
            if norm_mean < 1.0:  # Practically no signal
                adjustment = 3.0  # Very aggressive for truly dark images
            elif norm_mean < 2.0:  # Very dark
                adjustment = 2.0  # More aggressive for very dark
            else:  # Dark but not extreme
                adjustment = 1.0  # More aggressive for moderately dark
            
            self.log(f"Image EXTREMELY DARK (mean {norm_mean:.1f}%) - increasing current by {adjustment}%")
            
            # Check for oscillation conditions
            if (self.current_value <= 20 and self.current_value >= 18 and
                len(self.last_mean_values) >= 2 and 
                any(val > 30 for val in self.last_mean_values[:-1])):
                # We just dropped from bright to dark at this critical percentage
                adjustment = 0.3  # Very small adjustment to avoid oscillation
                self.log(f"⚠️ CLIFF EDGE DETECTED at {self.current_value}% - using micro-adjustment of 0.3%")
        
        # Remaining decision logic would go here - abbreviated for clarity
        # Full logic would include cases for undersaturation, oversaturation, etc.
        
        # Record this adjustment for oscillation detection
        self.last_adjustment_values.append(adjustment)
        if len(self.last_adjustment_values) > 5:
            self.last_adjustment_values.pop(0)
        
        # Return the calculated adjustment
        return adjustment
    
    def _calculate_pixel_count_adjustment(self, results):
        """Calculate adjustment based on pixel count analysis"""
        # Simplified adjustment logic for pixel count method
        saturation_percentage = results.get("saturation_percentage", 0)
        
        if saturation_percentage < 0.1:  # Too dark
            return 1.0
        elif saturation_percentage > 5.0:  # Too bright
            return -1.0
        elif saturation_percentage > 2.0:  # Slightly too bright
            return -0.5
        elif saturation_percentage < 0.5:  # Slightly too dark
            return 0.5
        else:  # Optimal range
            return 0.0
    
    def _calculate_contrast_adjustment(self, results):
        """Calculate adjustment based on contrast analysis"""
        # Simplified adjustment logic for contrast method
        contrast = results.get("global_contrast", 0)
        
        # Optimal contrast for speckle patterns typically around 0.3-0.4
        if contrast < 0.2:  # Too low contrast
            return 1.0
        elif contrast > 0.5:  # Too high contrast
            return -1.0
        elif contrast > 0.4:  # Slightly high contrast
            return -0.3
        elif contrast < 0.3:  # Slightly low contrast
            return 0.3
        else:  # Optimal range
            return 0.0 