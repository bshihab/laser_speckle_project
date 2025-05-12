#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pathlib import Path
import time
import traceback
import serial
from datetime import datetime

from PySide6.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QLabel, QSizePolicy, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QDateTime
from PySide6.QtGui import QFont, QColor

# Import Basler Pylon SDK
from pypylon import pylon

# Path handling for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the analysis modules
from histogram_saturation_analyzer import analyze_saturation_by_histogram, create_radial_weight_mask, read_raw_image
from saturation_pixel_count_analyzer import analyze_saturation_by_pixel_count
from contrast_analyzer import analyze_contrast

# Import the generated UI
from updated_ui import Ui_LaserSpeckleUI

class MatplotlibCanvas(FigureCanvasQTAgg):
    """Canvas for displaying the image and allowing ROI selection"""
    
    roi_selected = Signal(tuple)  # Signal to emit when ROI is selected (center_y, center_x, radius)
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        self.axes.axis('off')
        
        super().__init__(self.figure)
        self.setParent(parent)
        
        # Initialize ROI selection variables
        self.roi_circle = None
        self.roi_start = None
        self.roi_center = None
        self.roi_radius = None
        self.is_selecting = False
        
        # Connect mouse events
        self.mpl_connect('button_press_event', self.on_mouse_press)
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.mpl_connect('button_release_event', self.on_mouse_release)
        
        # Set figure to expand properly within the layout
        self.figure.set_tight_layout(True)
    
    def clear_roi(self):
        """Remove any existing ROI circles"""
        if self.roi_circle is not None:
            try:
                self.roi_circle.remove()
                self.roi_circle = None
            except:
                # If removal fails, just set to None
                self.roi_circle = None
        self.draw()
    
    def on_mouse_press(self, event):
        """Handle mouse press to start ROI selection"""
        if event.inaxes != self.axes or event.xdata is None or event.ydata is None:
            return
            
        self.is_selecting = True
        self.roi_start = (event.ydata, event.xdata)
        self.roi_center = self.roi_start
        self.roi_radius = 0
        
        # Remove any existing ROI circle before creating a new one
        self.clear_roi()
        
        # Create a new circle
        try:
            self.roi_circle = plt.Circle(
                (self.roi_center[1], self.roi_center[0]), 
                self.roi_radius, 
                color='r', 
                fill=False
            )
            self.axes.add_artist(self.roi_circle)
            self.draw()
        except Exception:
            # If circle drawing fails, continue without visual feedback
            pass
    
    def on_mouse_move(self, event):
        """Handle mouse movement to update ROI size"""
        if self.is_selecting and event.inaxes == self.axes and self.roi_center:
            # Calculate distance from start to current position
            dx = event.xdata - self.roi_center[1]
            dy = event.ydata - self.roi_center[0]
            self.roi_radius = np.sqrt(dx**2 + dy**2)
            
            # Update circle
            if self.roi_circle is not None:
                self.roi_circle.set_radius(self.roi_radius)
                self.draw()
    
    def on_mouse_release(self, event):
        """Handle mouse release to finalize ROI selection"""
        if self.is_selecting and event.inaxes == self.axes and self.roi_radius > 10:
            self.is_selecting = False
            
            # Emit signal with ROI information
            self.roi_selected.emit((
                int(self.roi_center[0]),
                int(self.roi_center[1]),
                int(self.roi_radius)
            ))
    
    def redraw_roi(self):
        """Redraw the ROI circle on the image"""
        if self.roi_center is None or self.roi_radius is None:
            return
        
        # Safely remove existing circle
        try:
            if self.roi_circle is not None and self.roi_circle in self.axes.artists:
                self.roi_circle.remove()
        except Exception:
            # If removal fails, just continue with creating a new circle
            pass
        
        # Create a new circle 
        self.roi_circle = plt.Circle(
            (self.roi_center[1], self.roi_center[0]), 
            self.roi_radius, 
            color='r', 
            fill=False
        )
        self.axes.add_artist(self.roi_circle)
        
        # Redraw the canvas
        try:
            self.draw()
        except Exception:
            # Ignore drawing errors, will be redrawn on next update
            pass
    
    def update_image(self, img_data):
        """Update the displayed image"""
        # Clear the axes completely including any ROI circles
        self.axes.clear()
        self.roi_circle = None  # Reset the ROI circle reference
        
        # Display the new image
        self.axes.imshow(img_data, cmap='gray', aspect='equal')
        self.axes.axis('off')
        
        # Ensure figure fits the canvas properly and maintains aspect ratio
        self.figure.tight_layout()
        self.draw()
        
        # Redraw ROI if it exists
        self.redraw_roi()

class LaserSpeckleUI(QWidget):
    """Modern UI implementation for Laser Speckle Analysis"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set up UI
        self.ui = Ui_LaserSpeckleUI()
        self.ui.setupUi(self)
        
        # Set default values for exposure and frequency inputs
        self.ui.exposureInput.setText("10")
        self.ui.frequencyInput.setText("10")
        
        # Create a label for current recommendations
        self.recommendation_label = QLabel(self)
        self.recommendation_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.recommendation_label.setStyleSheet("color: #004080; background-color: #e0f0ff; padding: 8px; border-radius: 4px;")
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setText("Current Recommendation: Analyze an image to get laser current recommendations")
        self.recommendation_label.setAlignment(Qt.AlignCenter)
        self.recommendation_label.setMinimumHeight(60)
        
        # Update the labels to show both weighted and unweighted stats
        self.ui.meanLabel.setText("Mean Intensity: -- | Raw: --")
        self.ui.saturationLabel.setText("Saturated Pixels: -- | Raw: --")
        self.ui.contrastLabel.setText("Contrast Ratio: -- | Raw: --")
        
        # Add the recommendation label to the stats group
        self.ui.statsLayout.addWidget(self.recommendation_label)
        
        # Set up matplotlib canvases for image display
        self.setup_canvases()
        
        # Connect button signals
        self.ui.loadButton.clicked.connect(self.load_image)
        self.ui.saveButton.clicked.connect(self.save_results)
        self.ui.resetButton.clicked.connect(self.reset_roi)
        self.ui.analyzeButton.clicked.connect(self.generate_analysis)
        self.ui.startButton.clicked.connect(self.start_capture)
        self.ui.stopButton.clicked.connect(self.stop_capture)
        
        # Add "View Results" button
        self.view_results_button = QPushButton("View Results", self)
        self.view_results_button.setEnabled(False)  # Disabled until analysis is run
        self.view_results_button.clicked.connect(self.view_results)
        
        # Add "Clean Storage" button
        self.clean_storage_button = QPushButton("Clean Storage", self)
        self.clean_storage_button.setStyleSheet("background-color: #ff5555; color: white;")
        self.clean_storage_button.clicked.connect(self.clean_storage)
        
        # Add the buttons to the layout
        self.ui.fileControlLayout.addWidget(self.view_results_button)
        self.ui.fileControlLayout.addWidget(self.clean_storage_button)
        
        # Configure current slider
        self.ui.currentSlider.setMinimum(0)
        self.ui.currentSlider.setMaximum(100)  # Use percentage values (0-100%)
        self.ui.currentSlider.setValue(20)     # Start at 20% instead of 50%
        self.ui.currentSlider.valueChanged.connect(self.update_laser_intensity)
        self.current_value = 20  # Initialize current value at 20% instead of 50%
        self.ui.currentLabel.setText(f"Current: 20%")  # Update label to match new default
        
        # Maximum voltage (2.5V instead of 5V)
        self.max_voltage = 2.5
        
        # Add variables to track previous measurements to reduce oscillation
        self.prev_high_sum = None  # Previous high intensity sum
        self.stable_count = 0      # Counter for consecutive stable readings
        self.min_stable_readings = 3  # Require this many stable readings before allowing adjustment
        
        # Manual override timer
        self.override_timer = QTimer(self)
        self.override_timer.setSingleShot(True)
        self.override_timer.timeout.connect(self.resume_auto_adjustment)
        self.manual_override_active = False
        
        # Initialize ROI variables
        self.roi_center = None
        self.roi_radius = None
        self.custom_weight_mask = None
        self.current_image = None
        self.current_image_path = None
        
        # Initialize oscillation detection variables
        self.last_mean_values = []
        self.last_adjustment_values = []
        
        # Initialize camera variables
        self.camera = None
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.capture_frame)
        self.capturing = False
        
        # Set up serial connection for Arduino control
        self.serial_port = None
        
        # Set default mode (auto or manual)
        self.auto_mode = True
        
        # Set up auto-adjust mode radio buttons
        self.auto_mode_layout = QHBoxLayout()
        self.auto_radio = QPushButton("Auto Adjust")
        self.auto_radio.setCheckable(True)
        self.auto_radio.setChecked(True)
        self.auto_radio.clicked.connect(self.set_auto_mode)
        
        self.manual_radio = QPushButton("Manual Adjust")
        self.manual_radio.setCheckable(True)
        self.manual_radio.clicked.connect(self.set_manual_mode)
        
        self.auto_mode_layout.addWidget(self.auto_radio)
        self.auto_mode_layout.addWidget(self.manual_radio)
        
        # Add the mode selection buttons to the UI
        self.ui.currentLayout.addLayout(self.auto_mode_layout)
        
        # Disable the stop button initially
        self.ui.stopButton.setEnabled(False)
        
        # Update UI state based on initial mode
        self.update_mode_ui()
        
        # Log initial message
        self.log_message("Laser Speckle Analyzer initialized")
        self.log_message("Connect to Arduino and camera to begin capturing")
        
        # Now set up serial connection
        self.setup_serial_connection()
    
    def log_message(self, message, error=False):
        """Add a message to the log with timestamp"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        
        # Format based on message type
        if error:
            formatted_message = f"<span style='color:red;'>[{timestamp}] ERROR: {message}</span>"
        else:
            formatted_message = f"[{timestamp}] {message}"
        
        # Add to log
        self.ui.logText.append(formatted_message)
        
        # Scroll to bottom
        self.ui.logText.verticalScrollBar().setValue(
            self.ui.logText.verticalScrollBar().maximum()
        )
    
    def set_auto_mode(self):
        """Set to automatic mode where analysis methods affect laser current"""
        self.auto_mode = True
        self.auto_radio.setChecked(True)
        self.manual_radio.setChecked(False)
        self.update_mode_ui()
        self.log_message("Switched to automatic mode - analysis will control laser current")
        
        # If we already have a recommendation, apply it immediately
        if hasattr(self, 'last_recommendation') and self.last_recommendation is not None:
            current_value = self.current_value
            new_value = max(0, min(100, int(current_value + self.last_recommendation)))
            self.update_current_ui_only(new_value)
            self.send_current_to_arduino(new_value)
            self.log_message(f"Applied existing recommendation: adjusted current to {new_value}%")
    
    def set_manual_mode(self):
        """Set to manual mode where only slider affects laser current"""
        self.auto_mode = False
        self.manual_radio.setChecked(True)
        self.auto_radio.setChecked(False)
        self.update_mode_ui()
        self.log_message("Switched to manual mode - use slider to control laser current")
    
    def update_mode_ui(self):
        """Update UI based on current mode"""
        # Enable/disable analysis method selection based on mode
        self.ui.analysisGroup.setEnabled(self.auto_mode)
        
        if self.auto_mode:
            self.ui.analysisGroup.setStyleSheet("QGroupBox { color: #333333; }")
            self.ui.histogram_radio.setStyleSheet("QRadioButton { color: #333333; }")
            self.ui.pixel_count_radio.setStyleSheet("QRadioButton { color: #333333; }")
            self.ui.contrast_radio.setStyleSheet("QRadioButton { color: #333333; }")
            self.ui.all_methods_radio.setStyleSheet("QRadioButton { color: #333333; }")
        else:
            self.ui.analysisGroup.setStyleSheet("QGroupBox { color: #999999; }")
            self.ui.histogram_radio.setStyleSheet("QRadioButton { color: #999999; }")
            self.ui.pixel_count_radio.setStyleSheet("QRadioButton { color: #999999; }")
            self.ui.contrast_radio.setStyleSheet("QRadioButton { color: #999999; }")
            self.ui.all_methods_radio.setStyleSheet("QRadioButton { color: #999999; }")
            
        # Update recommendation label
        if not self.auto_mode:
            self.recommendation_label.setText("Manual Mode - Use slider to control laser current")
            self.recommendation_label.setStyleSheet("background-color: #FFD700; color: #333333; padding: 8px; border-radius: 4px;")
        else:
            self.recommendation_label.setText("Automatic Mode - Analysis will recommend laser current adjustments")
            self.recommendation_label.setStyleSheet("background-color: #e0f0ff; color: #333333; padding: 8px; border-radius: 4px;")

    def setup_canvases(self):
        """Set up the Matplotlib canvases for the UI"""
        # Create preview canvas (left side with ROI selection)
        self.preview_canvas = MatplotlibCanvas(self, width=5, height=4)
        self.preview_canvas.roi_selected.connect(self.update_roi)
        self.ui.previewLayout.addWidget(self.preview_canvas)
        self.preview_canvas.mpl_connect('resize_event', self.on_preview_resize)
        
        # Create raw image canvas (right side, top)
        self.raw_canvas = MatplotlibCanvas(self, width=5, height=4)
        self.ui.rawImageLayout.addWidget(self.raw_canvas)
        self.raw_canvas.mpl_connect('resize_event', self.on_raw_resize)
        
        # Create speckle analysis canvas (right side, bottom)
        self.speckle_canvas = MatplotlibCanvas(self, width=5, height=4)
        self.ui.speckleImageLayout.addWidget(self.speckle_canvas)
        self.speckle_canvas.mpl_connect('resize_event', self.on_speckle_resize)

    def load_image(self):
        """Load a raw image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Raw Image", "", "Raw Files (*.raw);;All Files (*)"
        )
        
        if file_path:
            self.current_image_path = file_path
            # Example parameters - adjust based on your needs
            width, height = 960, 1200
            
            try:
                # Read the raw image
                self.current_image = read_raw_image(file_path, width, height)
                
                # Update display
                if self.current_image.dtype == np.uint16:
                    display_image = (self.current_image / 256).astype(np.uint8)
                else:
                    display_image = self.current_image
                
                self.preview_canvas.update_image(display_image)
                self.raw_canvas.update_image(display_image)
                
                # Log the action
                self.log_message(f"Loaded image: {Path(file_path).name}")
                
                # Reset ROI
                self.reset_roi()
                
                # Update UI
                self.ui.resetButton.setEnabled(True)
                self.ui.analyzeButton.setEnabled(True)
                self.ui.saveButton.setEnabled(False)  # Enable after analysis
                
            except Exception as e:
                self.log_message(f"Error loading image: {str(e)}", error=True)
                traceback.print_exc()
    
    def update_roi(self, roi_info):
        """Update ROI information based on user selection"""
        self.roi_center = (roi_info[0], roi_info[1])
        self.roi_radius = roi_info[2]
        
        # Update weight mask based on ROI
        if self.current_image is not None:
            # Create a more even weight mask with a flat top covering 70% of the radius
            flat_top_radius = int(self.roi_radius * 0.7)
            self.custom_weight_mask = create_radial_weight_mask(
                self.current_image.shape,
                center=self.roi_center,
                sigma=self.roi_radius,  # Full radius for sigma instead of half
                flat_top_radius=flat_top_radius
            )
            
            # Log the weight mask parameters
            self.log_message(f"Created more even weight mask: Flat top radius={flat_top_radius}px, Sigma={self.roi_radius}px")
        
        # Log ROI info
        self.log_message(f"ROI selected: Center=({self.roi_center[1]}, {self.roi_center[0]}), Radius={self.roi_radius}")
        
        # Enable analysis button
        self.ui.analyzeButton.setEnabled(True)
    
    def reset_roi(self):
        """Reset ROI selection"""
        self.roi_center = None
        self.roi_radius = None
        self.custom_weight_mask = None
        
        # Reset ROI visualization by clearing it
        if hasattr(self, 'preview_canvas'):
            self.preview_canvas.clear_roi()
        
        if self.current_image is not None:
            if self.current_image.dtype == np.uint16:
                display_image = (self.current_image / 256).astype(np.uint8)
            else:
                display_image = self.current_image
            
            self.preview_canvas.update_image(display_image)
            
            # Create default weight mask with more even weighting
            self.custom_weight_mask = create_radial_weight_mask(
                self.current_image.shape,
                sigma=min(self.current_image.shape) // 2,  # More even weighting
                flat_top_radius=min(self.current_image.shape) // 4  # Add flat top
            )
            
            self.log_message("Created default weight mask with more even weighting")
        
        self.log_message("ROI reset")
    
    def update_laser_intensity(self, value):
        """Update laser intensity based on slider value"""
        self.current_value = value
        self.ui.currentLabel.setText(f"Current: {value}%")
        
        # Always send slider value to Arduino, regardless of mode
        self.send_current_to_arduino(value)
        
        # If in auto mode, but user manually adjusted slider, temporarily override auto mode
        if self.auto_mode:
            # Record that we're in manual override mode
            self.manual_override_active = True
            
            # Log manual adjustment
            self.log_message(f"Manual adjustment to {value}% (temporarily overriding auto mode)")
            
            # Reset stability counters since we're making a manual change
            self.stable_count = 0
            self.prev_high_sum = None
            
            # Start/restart the override timer (2 seconds instead of 5)
            self.override_timer.start(2000)  # 2 seconds
        else:
            # Log the action (show current in mA instead of voltage)
            current_mA = self.calculate_laser_current(value)
            self.log_message(f"Laser current set to {value}% ({current_mA:.1f} mA)")
    
    def generate_analysis(self):
        """Generate analysis based on current image and ROI settings"""
        if self.current_image is None:
            self.log_message("No image loaded", error=True)
            return
        
        if self.custom_weight_mask is None:
            # Create default weight mask with more even weighting
            self.custom_weight_mask = create_radial_weight_mask(
                self.current_image.shape,
                sigma=min(self.current_image.shape) // 2,  # More even weighting
                flat_top_radius=min(self.current_image.shape) // 4  # Add flat top
            )
            self.log_message("Created default weight mask with even weighting for analysis")
        
        try:
            # Special check for the critical 19-21% range to break oscillation cycle
            if self.auto_mode and 19 <= self.current_value <= 21:
                # Check the last several adjustments for oscillation pattern
                last_adjustments = getattr(self, 'last_adjustment_values', [])
                if len(last_adjustments) >= 4:
                    last_signs = [1 if adj > 0 else -1 for adj in last_adjustments[-4:]]
                    # If we detect alternating signs (oscillation), force 20%
                    if (last_signs[0] != last_signs[1] and 
                        last_signs[1] != last_signs[2] and 
                        last_signs[2] != last_signs[3]):
                        self.log_message("⚠️ CRITICAL OSCILLATION DETECTED - Forcing stable value of 20%")
                        self.update_current_ui_only(20)
                        self.send_current_to_arduino(20)
                        self.log_message("Resetting oscillation tracking and pausing auto-adjust briefly")
                        self.manual_override_active = True
                        self.override_timer.start(5000)  # 5 second pause to stabilize
                        return  # Skip analysis
            
            # Determine which analysis method to use based on radio button selection
            run_histogram = self.ui.histogram_radio.isChecked() or self.ui.all_methods_radio.isChecked()
            run_pixel_count = self.ui.pixel_count_radio.isChecked() or self.ui.all_methods_radio.isChecked()
            run_contrast = self.ui.contrast_radio.isChecked() or self.ui.all_methods_radio.isChecked()
            
            # Extract the ROI from the current image (if ROI is defined)
            if self.roi_center is not None and self.roi_radius is not None:
                # Calculate ROI coordinates
                center_y, center_x = self.roi_center
                radius = self.roi_radius
                
                # Calculate ROI boundaries with boundary checks
                y_min = max(0, int(center_y - radius))
                y_max = min(self.current_image.shape[0], int(center_y + radius))
                x_min = max(0, int(center_x - radius))
                x_max = min(self.current_image.shape[1], int(center_x + radius))
                
                # Extract ROI from image
                roi_image = self.current_image[y_min:y_max, x_min:x_max]
                
                # Extract corresponding part of weight mask
                roi_weight_mask = None
                if self.custom_weight_mask is not None:
                    roi_weight_mask = self.custom_weight_mask[y_min:y_max, x_min:x_max]
            else:
                # Use whole image as ROI if no ROI is defined
                roi_image = self.current_image
                roi_weight_mask = self.custom_weight_mask
            
            # Initialize variables for combined recommendation
            results_combined = {}
            adjustments = []
            methods_used = []
            
            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Run histogram-based saturation analysis
            if run_histogram:
                try:
                    # Run the histogram analysis
                    results = analyze_saturation_by_histogram(
                        roi_image, 
                        weight_mask=roi_weight_mask
                    )
                    
                    # Calculate unweighted metrics for comparison
                    unweighted_mean = np.mean(roi_image)
                    
                    # Calculate unweighted saturation percentage
                    high_threshold = 0.8 * np.iinfo(roi_image.dtype).max if roi_image.dtype == np.uint16 else 204
                    unweighted_saturated = np.sum(roi_image > high_threshold) / roi_image.size * 100
                    
                    # Add unweighted results to results dictionary
                    results['unweighted_mean'] = unweighted_mean
                    results['unweighted_saturated_percentage'] = unweighted_saturated
                    
                    # Check if bin_edges is missing and add it if necessary
                    if "bin_centers" in results and "bin_edges" not in results:
                        # Generate bin edges from bin centers
                        bin_centers = results["bin_centers"]
                        bin_width = bin_centers[1] - bin_centers[0] if len(bin_centers) > 1 else 1
                        results["bin_edges"] = np.append(bin_centers - bin_width/2, bin_centers[-1] + bin_width/2)
                        results["weighted_histogram"] = results["histogram"]  # Use regular histogram if weighted not available
                    
                    # Store results
                    self.last_hist_results = results
                    
                    # Update UI with results
                    self.ui.meanLabel.setText(f"Mean Intensity: {results.get('weighted_mean', 0):.1f} | Raw: {results.get('unweighted_mean', 0):.1f}")
                    self.ui.saturationLabel.setText(f"Saturated Pixels: {results.get('high_intensity_sum', 0):.2f}% | Raw: {results.get('unweighted_saturated_percentage', 0):.2f}%")
                    
                    # Calculate current adjustment (limited to +/-5%)
                    adjustment = self.calculate_current_adjustment(results, "histogram", roi_image)
                    adjustment = max(-5.0, min(5.0, adjustment))  # Limit to +/-5%
                    
                    try:
                        adjustments.append(adjustment)
                        methods_used.append("histogram")
                    except NameError:
                        # If adjustments is not defined yet, create it
                        adjustments = [adjustment]
                        methods_used = ["histogram"]
                    
                    # Ensure output directory exists
                    output_dir = Path("analysis_results")
                    output_dir.mkdir(exist_ok=True)
                    
                    # Create absolute path for the result file
                    result_filename = f"histogram_analysis_{timestamp}.png"
                    result_filepath = output_dir / result_filename
                    
                    # Save the absolute path for opening later
                    self.last_analysis_path = str(result_filepath.absolute())
                    
                    # Plot and save results with proper error handling
                    try:
                        from histogram_saturation_analyzer import plot_results
                        fig = plt.figure(figsize=(12, 8))
                        plot_results(roi_image, results, "", save_output=False)
                        plt.close(fig)
                        
                        self.log_message(f"Histogram analysis complete: {adjustment:+.1f}% adjustment recommended")
                    except Exception as plot_error:
                        self.log_message(f"Error plotting histogram results: {plot_error}", error=True)
                    
                except Exception as e:
                    self.log_message(f"Error in histogram analysis: {str(e)}", error=True)
                    traceback.print_exc()
            
            # Run pixel-count saturation analysis
            if run_pixel_count:
                try:
                    results = analyze_saturation_by_pixel_count(
                        roi_image, 
                        weight_mask=roi_weight_mask
                    )
                    
                    # Calculate unweighted metrics for comparison
                    # Count raw saturated pixels without weighting
                    high_threshold = 0.8 * np.iinfo(roi_image.dtype).max if roi_image.dtype == np.uint16 else 204
                    unweighted_saturated_pixels = np.sum(roi_image > high_threshold)
                    total_pixels = roi_image.size
                    unweighted_saturated_percentage = (unweighted_saturated_pixels / total_pixels) * 100
                    
                    # Add unweighted results to results dictionary
                    results['unweighted_saturated_pixels'] = unweighted_saturated_pixels
                    results['unweighted_saturated_percentage'] = unweighted_saturated_percentage
                    
                    # Store results
                    self.last_pixel_results = results
                    
                    # Update UI with results
                    saturated_pixels = results.get('saturated_pixels', 0)
                    total_pixels = roi_image.size
                    self.ui.saturationLabel.setText(f"Saturated Pixels: {saturated_pixels} ({results.get('saturated_percentage', 0):.2f}%) | Raw: {unweighted_saturated_percentage:.2f}%")
                    
                    # Calculate current adjustment (limited to +/-5%)
                    adjustment = self.calculate_current_adjustment(results, "pixel_count", roi_image)
                    adjustment = max(-5.0, min(5.0, adjustment))  # Limit to +/-5%
                    
                    try:
                        adjustments.append(adjustment)
                        methods_used.append("pixel_count")
                    except NameError:
                        # If adjustments is not defined yet, create it
                        adjustments = [adjustment]
                        methods_used = ["pixel_count"]
                    
                    # Ensure output directory exists
                    output_dir = Path("analysis_results")
                    output_dir.mkdir(exist_ok=True)
                    
                    # Create absolute path for the result file
                    result_filename = f"pixel_count_analysis_{timestamp}.png"
                    result_filepath = output_dir / result_filename
                    
                    # Save the absolute path for opening later
                    self.last_analysis_path = str(result_filepath.absolute())
                    
                    # Plot and save results
                    from saturation_pixel_count_analyzer import plot_results
                    fig = plt.figure(figsize=(12, 8))
                    plot_results(roi_image, results, "", save_output=False)
                    plt.close(fig)
                    
                    self.log_message(f"Pixel count analysis complete: {adjustment:+.1f}% adjustment recommended")
                    
                except Exception as e:
                    self.log_message(f"Error in pixel count analysis: {str(e)}", error=True)
                    traceback.print_exc()
            
            # Run contrast analysis
            if run_contrast:
                try:
                    results = analyze_contrast(
                        roi_image, 
                        window_size=7,
                        weight_mask=roi_weight_mask
                    )
                    
                    # Calculate unweighted contrast 
                    # This is a simplified calculation - for true unweighted contrast,
                    # we'd need to modify the analyze_contrast function
                    from scipy.ndimage import uniform_filter, gaussian_filter
                    
                    # Apply local mean filter
                    window_size = 7  # Same as in analyze_contrast
                    local_mean = uniform_filter(roi_image.astype(float), size=window_size)
                    
                    # Calculate local contrast (standard deviation / mean)
                    # Use gaussian filter for smoothing
                    local_deviation = np.sqrt(uniform_filter((roi_image.astype(float) - local_mean)**2, size=window_size))
                    unweighted_contrast = np.mean(local_deviation / (local_mean + 1))  # Add 1 to avoid division by zero
                    
                    # Add to results
                    results['unweighted_contrast'] = unweighted_contrast
                    
                    # Store results
                    self.last_contrast_results = results
                    
                    # Update UI with results
                    mean_contrast = results.get('mean_contrast', 0)
                    self.ui.contrastLabel.setText(f"Contrast Ratio: {mean_contrast:.4f} | Raw: {unweighted_contrast:.4f}")
                    
                    # Calculate current adjustment (limited to +/-5%)
                    adjustment = self.calculate_current_adjustment(results, "contrast", roi_image)
                    adjustment = max(-5.0, min(5.0, adjustment))  # Limit to +/-5%
                    
                    try:
                        adjustments.append(adjustment)
                        methods_used.append("contrast")
                    except NameError:
                        # If adjustments is not defined yet, create it
                        adjustments = [adjustment]
                        methods_used = ["contrast"]
                    
                    # Ensure output directory exists
                    output_dir = Path("analysis_results")
                    output_dir.mkdir(exist_ok=True)
                    
                    # Create absolute path for the result file
                    result_filename = f"contrast_analysis_{timestamp}.png"
                    result_filepath = output_dir / result_filename
                    
                    # Save the absolute path for opening later
                    self.last_analysis_path = str(result_filepath.absolute())
                    
                    # Plot and save results
                    from contrast_analyzer import plot_results
                    fig = plt.figure(figsize=(12, 8))
                    plot_results(roi_image, results, "", save_output=False)
                    plt.close(fig)
                    
                    self.log_message(f"Contrast analysis complete: {adjustment:+.1f}% adjustment recommended")
                    
                except Exception as e:
                    self.log_message(f"Error in contrast analysis: {str(e)}", error=True)
                    traceback.print_exc()
            
            # Calculate final adjustment recommendation (average of all used methods)
            if adjustments:
                final_adjustment = sum(adjustments) / len(adjustments)
                self.last_recommendation = final_adjustment
                
                # Format recommendation text
                current_value = self.current_value
                new_value = max(0, min(100, int(current_value + final_adjustment)))
                
                # Set color and text based on recommendation
                if abs(final_adjustment) < 0.5:
                    self.update_recommendation_label("optimal", f"MAINTAIN current ({current_value}%)", final_adjustment)
                elif final_adjustment < 0:
                    self.update_recommendation_label("decrease", f"DECREASE current to {new_value}%", final_adjustment)
                else:
                    self.update_recommendation_label("increase", f"INCREASE current to {new_value}%", final_adjustment)
                
                # If in auto mode and no manual override is active, adjust the slider position to show the new value
                if self.auto_mode and not self.manual_override_active:
                    self.log_message(f"Auto mode active - adjusting current from {current_value}% to {new_value}%")
                    
                    # Only make adjustments if the new value is different from the current one
                    if int(new_value) != int(current_value):
                        # Update slider and current value without triggering Arduino update
                        self.update_current_ui_only(new_value)
                        
                        # Now send to Arduino if connected
                        self.send_current_to_arduino(new_value)
                        
                        # Calculate current in mA for logging
                        current_mA = self.calculate_laser_current(new_value)
                        self.log_message(f"Auto-adjusted current to {new_value}% ({current_mA:.1f} mA)")
                    else:
                        self.log_message(f"No adjustment needed, current value is optimal")
                elif self.auto_mode and self.manual_override_active:
                    self.log_message(f"Manual override is active - ignoring auto adjustment for now")
                else:
                    self.log_message(f"Manual mode active - suggested adjustment: {final_adjustment:+.1f}%")
                
                # Enable the view results button
                self.view_results_button.setEnabled(True)
                
                # Display analysis result images
                if self.ui.contrast_radio.isChecked() or self.ui.all_methods_radio.isChecked():
                    self.display_analysis_visualization(self.last_contrast_results, 'contrast')
                elif self.ui.pixel_count_radio.isChecked() or self.ui.all_methods_radio.isChecked():
                    self.display_analysis_visualization(self.last_pixel_results, 'pixel_count')
                elif self.ui.histogram_radio.isChecked() or self.ui.all_methods_radio.isChecked():
                    self.display_analysis_visualization(self.last_hist_results, 'histogram')
                
                # Notify the user that analysis is complete
                self.log_message(f"Analysis complete with {final_adjustment:+.1f}% adjustment recommendation")
            else:
                self.log_message("Please select at least one analysis method", error=True)
                
        except Exception as e:
            self.log_message(f"Error generating analysis: {str(e)}", error=True)
            traceback.print_exc()
    
    def update_recommendation_label(self, status, recommendation, value=None):
        """Update the recommendation label with analysis results"""
        if "SATURATED" in status or "LOW" in status or "HIGH" in status:
            bg_color = "#ffcc80"  # Light orange
        else:
            bg_color = "#aaffaa"  # Light green
        
        # Format value text based on status
        if value is not None:
            if "CONTRAST" in status:
                value_text = f" (Contrast: {value:.3f})"
            elif "SATURATED" in status:
                value_text = f" (Saturation: {value:.2f}%)"
            else:
                value_text = f" (Value: {value:.2f})"
        else:
            value_text = ""
        
        # Create recommendation text
        text = f"<b>{status}{value_text}</b><br>{recommendation}"
        
        # Update label
        self.recommendation_label.setText(text)
        self.recommendation_label.setStyleSheet(
            f"background-color: {bg_color}; border-radius: 4px; padding: 8px; font-weight: bold;"
        )
    
    def send_current_to_arduino(self, current_percent):
        """
        Send current value (as percentage) to Arduino
        Uses the protocol defined in user_controlled_UI.ino
        """
        if self.serial_port is None:
            self.log_message("Cannot send to Arduino: No connection established", error=True)
            return False
            
        try:
            # Convert percentage (0-100) to 12-bit value (0-4095)
            # Scale to 2.5V max instead of 5V (so 4095 corresponds to 2.5V)
            current_12bit = int((current_percent / 100.0) * 4095)
            
            # Calculate actual current in mA for logging
            current_mA = self.calculate_laser_current(current_percent)
            
            # Prepare packet according to Arduino protocol
            flag = 0x01  # Flag to indicate data change
            present_current = current_12bit  # Use the same value for present and target
            present_current_high = (present_current >> 8) & 0xFF  # High byte 
            present_current_low = present_current & 0xFF  # Low byte
            target_current_high = (current_12bit >> 8) & 0xFF  # High byte of 12-bit value
            target_current_low = current_12bit & 0xFF  # Low byte of 12-bit value
            temperature = 25  # Placeholder for temperature
            
            # Calculate checksum as per Arduino code
            checksum = (flag % 10 + present_current_high % 10 + present_current_low % 10 +
                        target_current_high % 10 + target_current_low % 10 + temperature % 10) % 10
            
            # Construct packet: [START_BYTE, FLAG, PRESENT_H, PRESENT_L, TARGET_H, TARGET_L, TEMP, CHECKSUM, END_BYTE]
            packet = bytes([0xFF, flag, present_current_high, present_current_low,
                           target_current_high, target_current_low, temperature, checksum, 0xFE])
            
            # Log change (with current in mA, not packet data)
            self.log_message(f"Sending to Arduino: Current {current_percent}% → {current_mA:.1f} mA")
            
            # Send the packet
            self.serial_port.write(packet)
            
            # Check for response (non-blocking)
            time.sleep(0.1)  # Give Arduino time to respond
            if self.serial_port.in_waiting > 0:
                response = self.serial_port.read(self.serial_port.in_waiting)
                # We don't log the response hex data now
            
            return True
            
        except Exception as e:
            self.log_message(f"Error sending to Arduino: {str(e)}", error=True)
            # Try to reconnect if connection was lost
            if "write operation" in str(e).lower() or "port is closed" in str(e).lower():
                self.log_message("Connection appears to be lost. Attempting to reconnect...", error=True)
                self.setup_serial_connection()
            return False
    
    def setup_serial_connection(self):
        """Establish connection to Arduino for laser control with enhanced detection"""
        self.serial_port = None
        try:
            # Get a list of available serial ports
            import serial.tools.list_ports
            available_ports = list(serial.tools.list_ports.comports())
            self.log_message(f"Found {len(available_ports)} serial ports")
            
            # First, look for a port specifically containing 'UNO R4 Minima' in the description
            for port in available_ports:
                if "UNO R4 Minima" in port.description:
                    self.log_message(f"Found Arduino Uno R4 Minima at: {port.device}")
                    try:
                        self.serial_port = serial.Serial(port.device, 9600, timeout=1)
                        self.log_message(f"Successfully connected to Arduino at {port.device}")
                        return
                    except Exception as e:
                        self.log_message(f"Error connecting to detected Arduino at {port.device}: {str(e)}", error=True)
            
            # If specific detection failed, try common port names
            ports_to_try = [
                '/dev/cu.usbmodem1101',  # Common port for Uno R4 Minima on macOS
                '/dev/cu.usbmodem*',     # Wildcard for macOS Arduino ports
                '/dev/ttyACM0',          # Common port on Linux
                '/dev/ttyUSB0',          # Alternative Linux port
                'COM3'                   # Common Windows port
            ]
            
            import glob
            for pattern in ports_to_try:
                # Expand wildcards if present
                if '*' in pattern:
                    matching_ports = glob.glob(pattern)
                    self.log_message(f"Checking pattern {pattern}, found matches: {matching_ports}")
                    for port in matching_ports:
                        try:
                            self.serial_port = serial.Serial(port, 9600, timeout=1)
                            self.log_message(f"Successfully connected to Arduino at {port}")
                            return
                        except Exception as e:
                            self.log_message(f"Error connecting to port {port}: {str(e)}", error=True)
                else:
                    try:
                        self.serial_port = serial.Serial(pattern, 9600, timeout=1)
                        self.log_message(f"Successfully connected to Arduino at {pattern}")
                        return
                    except Exception as e:
                        self.log_message(f"Error connecting to port {pattern}: {str(e)}", error=True)
            
            self.log_message("Could not connect to Arduino. Will operate in manual mode only.", error=True)
            
        except Exception as e:
            self.log_message(f"Serial connection setup error: {str(e)}", error=True)
            
        return None
    
    def display_analysis_visualization(self, results, method):
        """Display analysis results in the speckle canvas"""
        try:
            # Clear the canvas
            self.speckle_canvas.axes.clear()
            
            # Determine which visualization to show based on method
            if method == 'histogram':
                if "saturation_map" in results:
                    self.speckle_canvas.axes.imshow(results["saturation_map"])
                    self.speckle_canvas.axes.set_title("Histogram Saturation Analysis")
                    self.speckle_canvas.axes.axis('off')
                    self.speckle_canvas.draw()
                
            elif method == 'pixel_count':
                if "saturation_map" in results:
                    self.speckle_canvas.axes.imshow(results["saturation_map"])
                    self.speckle_canvas.axes.set_title("Pixel Count Saturation Analysis")
                    self.speckle_canvas.axes.axis('off')
                    self.speckle_canvas.draw()
                
            elif method == 'contrast':
                if "contrast_vis_map" in results:
                    self.speckle_canvas.axes.imshow(results["contrast_vis_map"])
                    self.speckle_canvas.axes.set_title("Contrast Analysis")
                    self.speckle_canvas.axes.axis('off')
                    self.speckle_canvas.draw()
            
        except Exception as e:
            self.log_message(f"Error displaying analysis visualization: {e}", error=True)
            traceback.print_exc()

    def start_capture(self):
        """Begin continuous capture from the Basler camera"""
        if self.capturing:
            self.log_message("Capture already in progress")
            return
        
        try:
            # Initialize the camera if not already done
            if not hasattr(self, 'camera') or self.camera is None:
                # Get all available devices
                available_devices = pylon.TlFactory.GetInstance().EnumerateDevices()
                
                if len(available_devices) == 0:
                    self.log_message("No Basler cameras found. Please connect a camera and try again.", error=True)
                    # Show a message box with instructions
                    QMessageBox.warning(self, "No Camera Found", 
                                        "No Basler cameras were detected.\n\n"
                                        "Please ensure your camera is connected and powered on.\n\n"
                                        "You can still use the application in 'load image' mode to analyze "
                                        "existing raw files.")
                    return
                
                # Create an instant camera object with the first available camera
                self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
                self.camera.Open()
                
                # Log camera info
                self.log_message(f"Connected to camera: {self.camera.GetDeviceInfo().GetModelName()}")
                self.log_message(f"Serial Number: {self.camera.GetDeviceInfo().GetSerialNumber()}")
            
            # Get exposure time from UI (in milliseconds) and convert to microseconds
            try:
                exposure_ms = float(self.ui.exposureInput.text())
                if exposure_ms <= 0:
                    exposure_ms = 10  # Default to 10ms if not set
                    self.ui.exposureInput.setText("10")
                exposure_us = int(exposure_ms * 1000)  # Convert to microseconds
                self.camera.ExposureTime.SetValue(exposure_us)
                self.log_message(f"Exposure time set to {exposure_ms}ms ({exposure_us}µs)")
            except Exception as e:
                self.log_message(f"Failed to set exposure time: {str(e)}", error=True)
                self.log_message("Using default exposure time of 10ms")
                exposure_ms = 10  # Default to 10ms
                exposure_us = 10000  # 10ms in microseconds
                self.camera.ExposureTime.SetValue(exposure_us)
                self.ui.exposureInput.setText("10")
            
            # Set capture interval from UI
            try:
                update_frequency_ms = int(self.ui.frequencyInput.text())
                if update_frequency_ms <= 0:
                    update_frequency_ms = 10  # Default to 10ms if not set
                    self.ui.frequencyInput.setText("10")
                self.capture_timer.setInterval(update_frequency_ms)
                self.log_message(f"Update frequency set to {update_frequency_ms}ms")
            except Exception as e:
                self.log_message(f"Failed to set update frequency: {str(e)}", error=True)
                update_frequency_ms = 10  # Default to 10ms
                self.capture_timer.setInterval(update_frequency_ms)
                self.ui.frequencyInput.setText("10")
                self.log_message("Using default update frequency of 10ms")
            
            # Start the capture timer
            self.capture_timer.start()
            self.capturing = True
            self.log_message("Started continuous image capture")
            
            # Update UI state
            self.ui.startButton.setEnabled(False)
            self.ui.stopButton.setEnabled(True)
            
        except Exception as e:
            self.log_message(f"Error starting capture: {str(e)}", error=True)
            traceback.print_exc()
            
            # Show a detailed error dialog
            QMessageBox.critical(self, "Camera Error", 
                               f"Error connecting to the camera:\n\n{str(e)}\n\n"
                               "Please check your camera connection and settings.")
    
    def stop_capture(self):
        """Stop capturing images from the camera"""
        if not self.capturing:
            self.log_message("No capture in progress")
            return
        
        try:
            # Stop the timer
            self.capture_timer.stop()
            self.capturing = False
            
            # Close the camera
            if hasattr(self, 'camera') and self.camera is not None:
                if self.camera.IsOpen():
                    self.camera.Close()
                self.camera = None
            
            self.log_message("Stopped image capture")
            
            # Update UI state
            self.ui.startButton.setEnabled(True)
            self.ui.stopButton.setEnabled(False)
            
        except Exception as e:
            self.log_message(f"Error stopping capture: {str(e)}", error=True)
            traceback.print_exc()
    
    def capture_frame(self, force_analysis=False):
        """Capture a frame from the Basler camera and update UI"""
        if not hasattr(self, 'camera') or self.camera is None or not self.camera.IsOpen():
            self.log_message("Camera not initialized or not open", error=True)
            self.stop_capture()
            return
        
        # Skip this frame if ROI selection is in progress
        if hasattr(self, 'preview_canvas') and self.preview_canvas.is_selecting:
            return
            
        try:
            # Capture an image with 5000ms timeout
            grab_result = self.camera.GrabOne(5000)
            
            if grab_result is not None:
                # Get the image as numpy array
                img = grab_result.GetArray()
                
                # Store the captured image
                self.current_image = img
                
                # Convert to 8-bit for display if needed
                if img.dtype == np.uint16:
                    img_8bit = (img / 256).astype(np.uint8)
                else:
                    img_8bit = img
                
                # Update UI elements with proper error handling
                try:
                    # Update the preview panel (with ROI)
                    self.preview_canvas.update_image(img_8bit)
                except Exception as canvas_error:
                    self.log_message(f"Preview canvas update error: {canvas_error}", error=True)
                
                try:
                    # Update the raw image panel
                    self.raw_canvas.axes.clear()
                    self.raw_canvas.axes.imshow(img_8bit, cmap='gray')
                    self.raw_canvas.axes.set_title("Raw Image")
                    self.raw_canvas.axes.axis('off')
                    self.raw_canvas.draw()
                except Exception as canvas_error:
                    self.log_message(f"Raw canvas update error: {canvas_error}", error=True)
                
                # Perform auto-analysis if ROI is set and in auto mode
                if self.roi_center is not None and self.roi_radius is not None and self.auto_mode:
                    if not self.manual_override_active or force_analysis:
                    # Use a separate timer to avoid blocking the main thread
                        # For forced analysis, use a very short delay (50ms)
                        delay = 50 if force_analysis else 100
                        QTimer.singleShot(delay, self.generate_analysis)
                
                # Release the grab result to free resources
                grab_result.Release()
                
        except Exception as e:
            self.log_message(f"Error capturing frame: {str(e)}", error=True)
            traceback.print_exc()
    
    def save_results(self):
        """Save analysis results to disk and open them in the default viewer"""
        if not hasattr(self, 'last_analysis_path') or not self.last_analysis_path:
            self.log_message("No analysis results to save", error=True)
            return
            
        try:
            # Copy the last analysis results file to a user-selected location
            options = QFileDialog.Options()
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Analysis Results", "", 
                "PNG Files (*.png);;All Files (*)", options=options
            )
            
            if save_path:
                # Ensure file has .png extension
                if not save_path.lower().endswith('.png'):
                    save_path += '.png'
                
                # Copy the file
                import shutil
                shutil.copy2(self.last_analysis_path, save_path)
                
                self.log_message(f"Results saved to {save_path}")
                
                # Open the file using the default application
                import subprocess
                import platform
                
                if platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', save_path])
                elif platform.system() == 'Windows':
                    os.startfile(save_path)
                else:  # Linux
                    subprocess.run(['xdg-open', save_path])
                
        except Exception as e:
            self.log_message(f"Error saving results: {str(e)}", error=True)
            traceback.print_exc()

    def on_preview_resize(self, event):
        """Handle preview canvas resize events"""
        if hasattr(self, 'preview_canvas') and hasattr(self.preview_canvas, 'figure'):
            self.preview_canvas.figure.tight_layout()
            self.preview_canvas.draw_idle()
    
    def on_raw_resize(self, event):
        """Handle raw image canvas resize events"""
        if hasattr(self, 'raw_canvas') and hasattr(self.raw_canvas, 'figure'):
            self.raw_canvas.figure.tight_layout()
            self.raw_canvas.draw_idle()
    
    def on_speckle_resize(self, event):
        """Handle speckle canvas resize events"""
        if hasattr(self, 'speckle_canvas') and hasattr(self.speckle_canvas, 'figure'):
            self.speckle_canvas.figure.tight_layout()
            self.speckle_canvas.draw_idle()

    def calculate_current_adjustment(self, results, method, roi_image=None):
        """
        Calculate how much to adjust the laser current based on analysis results.
        Returns a percentage adjustment value between -5 and +5 percent.
        
        Parameters:
        -----------
        results : dict
            Analysis results dictionary
        method : str
            Analysis method used ('histogram', 'pixel_count', or 'contrast')
        roi_image : ndarray, optional
            Region of interest image data, only used for certain calculations
        """
        adjustment = 0.0
        
        # Add hysteresis - don't adjust unless change would be significant
        min_adjustment_threshold = 0.3  # Reduced to allow finer adjustments
        
        # Variables to track oscillation pattern
        self.last_mean_values = getattr(self, 'last_mean_values', [])
        self.last_adjustment_values = getattr(self, 'last_adjustment_values', [])
        oscillation_detected = False
        
        # Default norm_mean value - will be updated in each method
        norm_mean = 0
        
        if method == "histogram":
            # Get key metrics for balanced decision-making
            highest_bin = results.get("highest_bin_percentage", 0)
            weighted_sat = results.get("weighted_saturation_percentage", 0)
            high_sum = results.get("high_intensity_sum", 0)
            weighted_mean = results.get("weighted_mean", 0)
            max_intensity = results.get("max_intensity", 255)  # Default to 8-bit
            
            # Force 8-bit processing
            is_16bit = False
            
            # Log the key metrics for debugging
            self.log_message(f"Histogram analysis metrics - Mean: {weighted_mean:.1f} (raw: {results.get('unweighted_mean', 0):.1f}), High sum: {high_sum:.2f}% (raw: {results.get('unweighted_saturated_percentage', 0):.2f}%), Highest bin: {highest_bin:.2f}%, Bit depth: 8-bit")
            
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
            self.log_message(f"Normalized metrics - Mean: {norm_mean:.1f}% (optimal range: {optimal_mean_min}-{optimal_mean_max}%), Saturation: {high_sum:.2f}% (raw: {results.get('unweighted_saturated_percentage', 0):.2f}%) (optimal range: {optimal_sat_min}-{optimal_sat_max}%)")
            
            # Check if we're in a stable range
            if self.prev_high_sum is not None:
                # Calculate the change since last measurement
                delta_sum = abs(current_high_sum - self.prev_high_sum)
                
                if delta_sum < 0.1:  # If measurement is stable
                    self.stable_count += 1
                    self.log_message(f"Stable reading #{self.stable_count}: high_sum={high_sum:.3f}, mean={norm_mean:.1f}%")
                else:
                    # Reset stability counter if readings are fluctuating
                    self.stable_count = 0
                    self.log_message(f"Unstable reading: high_sum={high_sum:.3f}, delta={delta_sum:.3f}")
            
            # Store current values for next comparison
            self.prev_high_sum = current_high_sum
            
            # DECISION LOGIC - CONSIDERS BOTH MEAN AND SATURATION SIMULTANEOUSLY
            
            # CASE 0: EXTREMELY DARK - Aggressive increase for completely dark images
            if norm_mean < 2.0 or high_sum < 0.01:  # Near-zero mean or extremely few bright pixels
                # Scale adjustment based on how extreme the darkness is
                if norm_mean < 1.0:  # Practically no signal
                    adjustment = 3.0  # Very aggressive for truly dark images (increased from 2.0)
                    self.log_message(f"Image COMPLETELY DARK (mean {norm_mean:.1f}%) - increasing current by 3.0%")
                elif norm_mean < 2.0:  # Very dark
                    adjustment = 2.0  # More aggressive for very dark (increased from 1.0)
                    self.log_message(f"Image EXTREMELY DARK (mean {norm_mean:.1f}%) - increasing current by 2.0%")
                else:  # Dark but not extreme
                    adjustment = 1.0  # More aggressive for moderately dark (increased from 0.5)
                    self.log_message(f"Image VERY DARK (mean {norm_mean:.1f}%) - increasing current by 1.0%")
                
                # Check for the specific value that causes oscillation
                if self.current_value == 19:
                    # This is precisely the dark point that's causing oscillation
                    adjustment = 1.0  # Just go to 20% instead of 21%
                    self.log_message("⚠️ OSCILLATION PREVENTION - Current at critical dark point (19%)")
                    self.log_message("Using conservative adjustment to reach stability point (20%)")
                
                # Check for possible oscillation condition - we might be at the "cliff edge"
                if (self.current_value <= 20 and self.current_value >= 18 and
                    len(self.last_mean_values) >= 2 and 
                    any(val > 30 for val in self.last_mean_values[:-1])):
                    # We just dropped from bright to dark at this critical percentage
                    # Use a much smaller, more careful adjustment
                    adjustment = 0.3  # Very small adjustment to avoid oscillation
                    self.log_message(f"⚠️ CLIFF EDGE DETECTED at {self.current_value}% - using micro-adjustment of 0.3%")
            
            # CASE 1: SIGNIFICANT UNDERSATURATION - More moderate adjustment
            elif norm_mean < optimal_mean_min * 0.7 or high_sum < optimal_sat_min * 0.3:  # Using OR instead of AND and higher thresholds
                # Severely underexposed - use more aggressive increases
                adjustment = 1.5  # Increased from 0.7
                if norm_mean < optimal_mean_min * 0.5:  # Added missing colon here
                    self.log_message(f"Image SEVERELY underexposed (mean {norm_mean:.1f}%) - increasing current by 1.5%")
                else:
                    self.log_message(f"Image has too few bright pixels ({high_sum:.2f}%) - increasing current by 1.5%")
            
            # CASE 2: SIGNIFICANT OVERSATURATION - More moderate decrease
            elif highest_bin > 5.0 or weighted_sat > 2.0 or high_sum > optimal_sat_max * 3:
                # Scale adjustment based on how far into oversaturation we are
                if high_sum > 60:  # Extreme oversaturation
                    adjustment = -0.5
                    self.log_message("EXTREME oversaturation detected - decreasing current by 0.5%")
                elif high_sum > 40:  # Significant oversaturation
                    adjustment = -0.3
                    self.log_message("Significant oversaturation detected - decreasing current by 0.3%")
                elif high_sum > 20:  # Moderate oversaturation
                    adjustment = -0.2
                    self.log_message("Moderate oversaturation detected - decreasing current by 0.2%")
                else:  # Mild oversaturation
                    adjustment = -0.1
                    self.log_message("Mild oversaturation detected - decreasing current by 0.1%")
                
                # Check for the specific value that causes oscillation
                if self.current_value == 21:
                    # This is precisely the bright point that's causing oscillation
                    adjustment = -1.0  # Ensure we go down to 20% 
                    self.log_message("⚠️ OSCILLATION PREVENTION - Current at critical bright point (21%)")
                    self.log_message("Using precise adjustment to reach stability point (20%)")
                
                # Check for possible oscillation condition - we might be at the "cliff edge"
                if (self.current_value <= 20 and self.current_value >= 19 and
                    len(self.last_mean_values) >= 2 and 
                    any(val < 10 for val in self.last_mean_values[:-1])):
                    # We just jumped from dark to bright at this critical percentage
                    # Use a much smaller, more careful adjustment
                    adjustment = -0.1  # Tiny decrease to avoid oscillation
                    self.log_message(f"⚠️ CLIFF EDGE DETECTED at {self.current_value}% - using micro-adjustment of -0.1%")
            
            # CASE 3: Check for general saturation (second priority)
            elif highest_bin > 2.0 or weighted_sat > 1.0:
                # Moderate saturation - decrease but not as aggressively
                if highest_bin > 3.5 or weighted_sat > 1.5:
                    adjustment = -0.4
                    self.log_message("Moderate saturation detected - decreasing current by 0.4%")
                else:
                    adjustment = -0.2
                    self.log_message("Mild saturation detected - decreasing current by 0.2%")
            
            # CASE 4: Mean is too low (underexposed) AND saturation is low/acceptable
            elif norm_mean < optimal_mean_min and high_sum < optimal_sat_max:
                # How far below optimal are we?
                mean_deficit = optimal_mean_min - norm_mean
                sat_deficit = optimal_sat_min - high_sum
                
                # Print more detailed diagnostic info
                self.log_message(f"Underexposure analysis - Mean deficit: {mean_deficit:.1f}%, Saturation deficit: {sat_deficit:.2f}%")
                
                # Scale adjustment based on how far from optimal
                if mean_deficit > 15:  # Way too dark (adjusted for new range)
                    adjustment = 1.5
                    self.log_message(f"Image significantly underexposed (mean {norm_mean:.1f}%) - increasing current by 1.5%")
                elif mean_deficit > 7:  # Moderately dark (adjusted for new range)
                    adjustment = 1.0
                    self.log_message(f"Image moderately underexposed (mean {norm_mean:.1f}%) - increasing current by 1.0%")
                elif mean_deficit > 3:  # Slightly dark (adjusted for new range)
                    adjustment = 0.7
                    self.log_message(f"Image slightly underexposed (mean {norm_mean:.1f}%) - increasing current by 0.7%")
                else:  # Very close to optimal
                    adjustment = 0.3
                    self.log_message(f"Image near optimal range (mean {norm_mean:.1f}%) - small increase of 0.3%")
            
            # CASE 5: Mean is too high AND we have some saturation (potentially approaching saturation)
            elif norm_mean > optimal_mean_max and high_sum > optimal_sat_min:
                # How far above optimal are we?
                mean_excess = norm_mean - optimal_mean_max
                
                if mean_excess > 15:  # Way too bright (adjusted for new range)
                    adjustment = -0.5
                    self.log_message(f"Image too bright with saturation risk (mean {norm_mean:.1f}%) - reducing current by 0.5%")
                else:  # Getting close to optimal
                    adjustment = -0.2
                    self.log_message(f"Image slightly bright (mean {norm_mean:.1f}%) - gentle decrease")
            
            # CASE 6: Mean is good but saturation is too low (need more bright pixels)
            elif optimal_mean_min <= norm_mean <= optimal_mean_max and high_sum < optimal_sat_min:
                # How far below optimal saturation?
                sat_deficit = optimal_sat_min - high_sum
                
                if sat_deficit > 10:  # Significant deficit  
                    adjustment = 1.0
                    self.log_message(f"Good mean ({norm_mean:.1f}%) but too few bright pixels ({high_sum:.2f}%) - increasing current")
                else:  # Getting close
                    adjustment = 0.5  # Small adjustment when close
                    self.log_message(f"Good mean ({norm_mean:.1f}%), almost enough bright pixels ({high_sum:.2f}%) - small adjustment")
            
            # CASE 7: Mean is good but high_sum is too high (too many bright pixels, risk of saturation)
            elif optimal_mean_min <= norm_mean <= optimal_mean_max and high_sum > optimal_sat_max:
                # How far above optimal saturation?
                sat_excess = high_sum - optimal_sat_max
                
                if sat_excess > 10:  # Significant excess
                    adjustment = -0.5
                    self.log_message(f"Good mean ({norm_mean:.1f}%) but too many bright pixels ({high_sum:.2f}%) - decreasing current")
                else:  # Getting close
                    adjustment = -0.2  # Small adjustment when close
                    self.log_message(f"Good mean ({norm_mean:.1f}%), slightly too many bright pixels ({high_sum:.2f}%) - small adjustment")
            
            # CASE 8: Both metrics are in optimal range - PERFECT!
            elif optimal_mean_min <= norm_mean <= optimal_mean_max and optimal_sat_min <= high_sum <= optimal_sat_max:
                adjustment = 0.0
                self.log_message(f"OPTIMAL RANGE - mean: {norm_mean:.1f}%, high_sum: {high_sum:.2f}% - maintaining current")
            
            # CASE 9: Any other scenario (fallback)
            else:
                # Make a proportional decision based on distance from optimal
                mean_factor = 0
                sat_factor = 0
                
                # Calculate how far mean is from optimal (negative = too low, positive = too high)
                if norm_mean < optimal_mean_min:
                    mean_deficit = optimal_mean_min - norm_mean
                    # Using non-linear mapping for smoother approach
                    if mean_deficit < 3:  # Close to optimal
                        mean_factor = mean_deficit * 0.1  # Increased scaling
                    elif mean_deficit < 8:
                        mean_factor = 0.3 + (mean_deficit - 3) * 0.15  # More aggressive approach
                    else:
                        mean_factor = 1.05 + (mean_deficit - 8) * 0.25  # Much stronger
                    mean_factor = min(2.0, mean_factor)  # Cap at 2.0 (increased from 0.4)
                elif norm_mean > optimal_mean_max:
                    mean_excess = norm_mean - optimal_mean_max
                    # Non-linear mapping for decreases too
                    if mean_excess < 3:  # Close to optimal
                        mean_factor = -mean_excess * 0.1  # Increased scaling
                    elif mean_excess < 8:
                        mean_factor = -0.3 - (mean_excess - 3) * 0.15  # More aggressive
                    else:
                        mean_factor = -1.05 - (mean_excess - 8) * 0.25  # Much stronger
                    mean_factor = max(-2.0, mean_factor)  # Cap at -2.0 (increased magnitude)
                
                # Calculate how far saturation is from optimal (negative = too low, positive = too high)
                if high_sum < optimal_sat_min:
                    sat_deficit = optimal_sat_min - high_sum
                    # Non-linear mapping for saturation too
                    if sat_deficit < 0.1:  # Very close
                        sat_factor = sat_deficit * 0.8  # Increased scaling
                    elif sat_deficit < 0.3:
                        sat_factor = 0.08 + (sat_deficit - 0.1) * 2.0  # Increased scaling
                    else:
                        sat_factor = 0.48 + (sat_deficit - 0.3) * 1.0  # Increased scaling
                    sat_factor = min(1.5, sat_factor)  # Cap at 1.5 (increased from 0.3)
                elif high_sum > optimal_sat_max:
                    sat_excess = high_sum - optimal_sat_max
                    # Non-linear mapping for saturation excess
                    if sat_excess < 0.1:  # Very close
                        sat_factor = -sat_excess * 0.8  # Increased scaling
                    elif sat_excess < 0.3:
                        sat_factor = -0.08 - (sat_excess - 0.1) * 2.0  # Increased scaling
                    else:
                        sat_factor = -0.48 - (sat_excess - 0.3) * 1.0  # Increased scaling
                    sat_factor = max(-1.5, sat_factor)  # Cap at -1.5 (increased magnitude)
                
                # Combine factors (weighted average - mean is slightly more important)
                combined_factor = (mean_factor * 0.6) + (sat_factor * 0.4)
                
                # Scale combined factor to get adjustment
                if abs(combined_factor) < 0.1:
                    # Very close to optimal - tiny adjustments
                    adjustment = combined_factor * 0.5  # Still moderate for close values
                elif abs(combined_factor) < 0.5:
                    # Somewhat close - small adjustments
                    adjustment = combined_factor * 0.6  # More aggressive
                else:
                    # Further away - larger adjustments
                    adjustment = combined_factor * 0.8  # Much more aggressive
                
                self.log_message(f"Proportional adjustment: mean_factor={mean_factor:.2f}, sat_factor={sat_factor:.2f}, combined={combined_factor:.2f} → {adjustment:+.3f}%")
            
            # Apply different stability damping based on direction
            if self.stable_count >= 2 and adjustment != 0:
                # Different damping for underexposed vs. overexposed
                if adjustment > 0:  # For underexposed (increasing current)
                    # Less aggressive damping for underexposed images
                    damping = min(0.6, self.stable_count * 0.15)  # Max 60% for increases
                else:  # For overexposed (decreasing current)
                    # More aggressive damping for overexposed images
                    damping = min(0.8, self.stable_count * 0.2)  # Max 80% for decreases
                
                # Apply even stronger damping in the critical 19-21% range
                if 19 <= self.current_value <= 21:
                    if self.stable_count >= 5:  # Very stable readings at critical point
                        damping = 0.9  # 90% damping - extremely conservative
                        self.log_message(f"Critical region ultra-stability damping - using 90% reduction")
                    else:  # Not as stable in critical region
                        damping = min(0.8, damping + 0.2)  # Add 20% more damping in critical region
                        self.log_message(f"Critical region enhanced damping - using {damping:.0%} reduction")
                
                original = adjustment
                adjustment *= (1 - damping)
                self.log_message(f"Stability damping ({damping:.1%}) applied: {original:+.3f}% → {adjustment:+.3f}%")
            
            # Apply different hysteresis thresholds based on direction
            if adjustment < 0 and abs(adjustment) < 0.07:
                # For decreases (overexposed), use larger threshold
                self.log_message(f"Decreasing adjustment {adjustment:+.3f}% too small, maintaining current (hysteresis)")
                adjustment = 0.0
            elif adjustment > 0 and abs(adjustment) < 0.02:  # Reduced from 0.03 to make more increases happen
                # For increases (underexposed), use much smaller threshold
                self.log_message(f"Increasing adjustment {adjustment:+.3f}% too small, maintaining current (hysteresis)")
                adjustment = 0.0
            
            # Critical region hysteresis - even more conservative in 19-21% range
            elif 19 <= self.current_value <= 21:
                if adjustment < 0 and abs(adjustment) < 0.15:  # Much higher threshold for critical region
                    self.log_message(f"Critical region: Small decrease {adjustment:+.3f}% ignored for stability")
                    adjustment = 0.0
                elif adjustment > 0 and abs(adjustment) < 0.1:  # Higher threshold for increases too
                    self.log_message(f"Critical region: Small increase {adjustment:+.3f}% ignored for stability")
                    adjustment = 0.0
        
        elif method == "pixel_count":
            # Pixel count-based adjustment with more aggressive adjustments
            if "is_saturated" in results and results["is_saturated"]:
                # Saturation detected, recommend decreasing current
                sat_percent = results.get("weighted_saturation_percentage", 0)
                
                # Store normalized intensity for oscillation detection (estimated)
                norm_mean = 70  # Estimated normalized intensity for saturated images
                self.last_mean_values.append(norm_mean)
                if len(self.last_mean_values) > 5:
                    self.last_mean_values.pop(0)
                
                if sat_percent > 2.0:
                    # Significant saturation
                    adjustment = -5.0  # Increased to 5% for significant saturation
                    self.log_message("Significant saturation detected - decreasing current by 5%")
                elif sat_percent > 1.0:
                    # Moderate saturation
                    adjustment = -2.0
                    self.log_message("Moderate saturation detected - decreasing current")
                elif sat_percent > 0.5:
                    # Mild saturation
                    adjustment = -1.0
                    self.log_message("Mild saturation detected - decreasing current")
                else:
                    # Slight saturation
                    adjustment = -0.5
                    self.log_message("Slight saturation detected - decreasing current")
            elif "saturated_pixels" in results:
                # Check if image is underexposed
                sat_pixels = results.get("saturated_pixels", 0)
                total_pixels = results.get("total_pixels", 1)
                max_value = results.get("max_value", 255)  # Default to 8-bit
                
                # Calculate approximate norm_mean for oscillation detection
                norm_mean = (max_value / 255) * 100
                self.last_mean_values.append(norm_mean)
                if len(self.last_mean_values) > 5:
                    self.last_mean_values.pop(0)
                
                # Force 8-bit processing
                is_16bit = False
                
                # Calculate percentage for better judgment
                pixel_percentage = (sat_pixels / total_pixels) * 100
                
                # Log values for both weighted and unweighted analysis
                self.log_message(f"Pixel count metrics - Saturated pixels: {sat_pixels} ({pixel_percentage:.2f}%), Raw: {results.get('unweighted_saturated_pixels', 0)} ({results.get('unweighted_saturated_percentage', 0):.2f}%), Max value: {max_value}")
                
                if sat_pixels == 0:
                    # No saturated pixels - check how far from saturation
                    # For 8-bit images
                    if max_value < 50:  # Extremely dark (was 100)
                        adjustment = 3.0  # Much more aggressive increase (was 2.0)
                        self.log_message(f"8-bit image: Extremely dark (max value: {max_value}) - increasing by 3.0%")
                    elif max_value < 100:  # Far from saturation (for 8-bit images)
                        adjustment = 1.5  # More aggressive (was 0.7)
                        self.log_message(f"8-bit image: Severely undersaturated (max value: {max_value}) - increasing by 1.5%")
                    elif max_value < 150:  # Still underexposed
                        adjustment = 1.0  # More aggressive (was 0.3)
                        self.log_message(f"8-bit image: Underexposed (max value: {max_value}) - increasing by 1.0%")
                    elif max_value < 180:  # Moderately underexposed
                        adjustment = 0.7  # More aggressive (was 0.3)
                        self.log_message(f"8-bit image: Moderately underexposed (max value: {max_value}) - increasing by 0.7%")
                    elif max_value < 220:  # Moderate distance from saturation
                        adjustment = 0.5  # More aggressive (was 0.2)
                        self.log_message(f"8-bit image: Moderate distance from saturation (max value: {max_value}) - increasing by 0.5%")
                    else:  # Closer to saturation
                        adjustment = 0.3  # More aggressive (was 0.1)
                        self.log_message(f"8-bit image: Close to saturation (max value: {max_value}) - increasing by 0.3%")
                # Add optimal range where no adjustment is needed - widened range
                elif 35 <= pixel_percentage <= 45:  # Updated to match new optimal range
                    # Small but optimal amount of bright pixels
                    adjustment = 0.0
                    self.log_message("Optimal pixel saturation detected - maintaining current")
                elif 45 < pixel_percentage <= 55:
                    # Just above optimal - small decrease
                    adjustment = -0.5
                    self.log_message(f"Slightly above optimal saturation ({pixel_percentage:.2f}%) - small decrease")
                elif 55 < pixel_percentage <= 65:
                    # Moderate above optimal
                    adjustment = -1.0
                    self.log_message(f"Moderately above optimal saturation ({pixel_percentage:.2f}%) - decrease current")
                else:
                    # Well above optimal
                    adjustment = -2.0  # More aggressive
                    self.log_message(f"Well above optimal saturation ({pixel_percentage:.2f}%) - decrease current")
        
        elif method == "contrast":
            # Contrast-based adjustment with more aggressive adjustments
            if "mean_contrast" in results:
                contrast_value = results.get("mean_contrast", 0)
                max_value = results.get("max_intensity", 255)  # Default to 8-bit
                
                # Calculate unweighted contrast if not already computed
                unweighted_contrast = results.get("unweighted_contrast", 0)
                
                # Calculate approximate norm_mean for oscillation detection
                # Estimate based on contrast value - high contrast = medium brightness
                if contrast_value < 0.02:  # Very low contrast = likely very dark
                    norm_mean = 5  # Very dark estimation
                elif contrast_value > 0.3:  # High contrast = likely bright with some dark
                    norm_mean = 60  # Medium-bright estimation
                else:  # Medium contrast = likely good exposure
                    norm_mean = 30  # Medium estimation
                
                self.last_mean_values.append(norm_mean)
                if len(self.last_mean_values) > 5:
                    self.last_mean_values.pop(0)
                
                # Force 8-bit processing
                is_16bit = False
                
                # Log contrast value
                self.log_message(f"Contrast analysis: Weighted: {contrast_value:.4f}, Raw: {results.get('unweighted_contrast', 0):.4f} (8-bit image)")
                
                # Optimal contrast range is typically around 0.1-0.2
                if contrast_value < 0.005:  # Extremely low contrast (new case)
                    # Near-zero contrast - extremely dark image - aggressive increase
                    adjustment = 3.0  # Much more aggressive (increased from 2.0)
                    self.log_message(f"Extremely low contrast ({contrast_value:.4f}) - increasing current by 3.0%")
                elif contrast_value < 0.02:
                    # Very low contrast - gentler increase
                    adjustment = 2.0  # Doubled from 1.0
                    self.log_message(f"Very low contrast ({contrast_value:.4f}) - increasing current by 2.0%")
                elif contrast_value < 0.05:
                    # Low contrast
                    adjustment = 1.0  # Increased from 0.5
                    self.log_message(f"Low contrast ({contrast_value:.4f}) - increasing current by 1.0%")
                elif contrast_value < 0.08:
                    # Approaching optimal - moderate increase
                    adjustment = 1.0  # Kept the same
                    self.log_message(f"Below optimal contrast ({contrast_value:.4f}) - moderate increase")
                elif contrast_value < 0.09:
                    # Close to optimal - gentle increase
                    adjustment = 0.5  # Kept the same
                    self.log_message(f"Slightly below optimal contrast ({contrast_value:.4f}) - gentle increase")
                elif 0.09 <= contrast_value <= 0.26:  # Optimal range
                    # Optimal contrast range - no adjustment needed
                    adjustment = 0.0
                    self.log_message(f"Optimal contrast range ({contrast_value:.4f}) - maintaining current")
                elif 0.26 < contrast_value <= 0.28:
                    # Just above optimal - gentle decrease
                    adjustment = -0.5
                    self.log_message(f"Slightly above optimal contrast ({contrast_value:.4f}) - gentle decrease")
                elif 0.28 < contrast_value <= 0.32:
                    # Moderately high contrast
                    adjustment = -1.0
                    self.log_message(f"Moderately high contrast ({contrast_value:.4f}) - moderate decrease")
                elif 0.32 < contrast_value <= 0.4:
                    # High contrast
                    adjustment = -2.0
                    self.log_message(f"High contrast ({contrast_value:.4f}) - significant decrease")
                else:  # contrast_value > 0.4
                    # Very high contrast
                    adjustment = -0.5  # Use 0.5% instead of 1%
                    self.log_message(f"Very high contrast ({contrast_value:.4f}) - decreasing by 0.5%")
                
                # Apply more conservative adjustments for 8-bit images but still allow significant changes
                if not is_16bit and adjustment != 0:
                    original = adjustment
                    # We're keeping the adjustment as is, no scaling needed
                    # adjustment *= 0.9  # Only 10% smaller adjustments for 8-bit
                    # self.log_message(f"8-bit image adjustment scaling: {original:+.2f}% → {adjustment:+.2f}%")
                    pass  # No adjustment needed
        
        # Apply hysteresis to prevent oscillation - ignore very small adjustments
        if abs(adjustment) < min_adjustment_threshold:
            if adjustment != 0:  # Don't log if we already decided not to adjust
                self.log_message(f"Adjustment {adjustment:+.1f}% too small, maintaining current (hysteresis)")
            adjustment = 0.0
        
        # Enhanced hysteresis for critical region (19-21%) - be extremely conservative
        # REMOVED as requested by user - was causing incorrect behavior
        
        # Apply asymmetric limits - allow larger increases for underexposure
        if adjustment > 0:  # For increases (underexposed)
            adjustment = min(3.0, adjustment)  # Allow up to 3.0% increases (was 2.0%)
            self.log_message(f"Final adjustment (increase) limited to {adjustment:+.2f}%")
        else:  # For decreases (overexposed)
            adjustment = max(-0.5, adjustment)  # Strict -0.5% limit for decreases
            if adjustment < 0:  # Only log if there's actually a decrease
                self.log_message(f"Final adjustment (decrease) limited to {adjustment:+.2f}%")
        
        # Extra stabilization lock for 20% - REMOVED as requested by user - was causing incorrect behavior
        
        # Store this adjustment for oscillation detection
        self.last_adjustment_values.append(adjustment)
        if len(self.last_adjustment_values) > 5:  # Keep only the last 5 adjustments
            self.last_adjustment_values.pop(0)
        
        # Check for oscillation pattern (going between dark and bright repeatedly)
        if len(self.last_mean_values) >= 3 and len(self.last_adjustment_values) >= 3:
            # Check if we're seeing alternating bright and dark values
            is_oscillating = False
            
            # Detect large jumps between values (bright to dark to bright)
            if (len(self.last_mean_values) >= 3 and 
                abs(self.last_mean_values[-1] - self.last_mean_values[-2]) > 30 and
                abs(self.last_mean_values[-2] - self.last_mean_values[-3]) > 30):
                is_oscillating = True
            
            # Detect pattern of alternating positive and negative adjustments
            if (len(self.last_adjustment_values) >= 3 and 
                ((self.last_adjustment_values[-1] > 0 and self.last_adjustment_values[-2] < 0) or
                 (self.last_adjustment_values[-1] < 0 and self.last_adjustment_values[-2] > 0))):
                is_oscillating = True
            
            if is_oscillating:
                self.log_message("⚠️ OSCILLATION DETECTED - Using more conservative adjustment")
                
                # If we're about to decrease from a high value to a potentially too-low value,
                # use a more conservative approach
                if norm_mean > 40 and adjustment < 0:
                    # Make a very small decrease to avoid dropping off the cliff
                    original = adjustment
                    adjustment = max(-0.1, adjustment / 5.0)  # Very conservative decrease
                    self.log_message(f"Anti-oscillation decrease: {original:+.2f}% → {adjustment:+.2f}%")
                
                # If we're about to increase from a very low value, be more conservative
                elif norm_mean < 10 and adjustment > 0:  
                    # Make a smaller increase to avoid jumping to oversaturation
                    original = adjustment
                    adjustment = min(0.5, adjustment / 2.0)  # Conservative increase
                    self.log_message(f"Anti-oscillation increase: {original:+.2f}% → {adjustment:+.2f}%")
        
        return adjustment

    def view_results(self):
        """Open the most recent analysis results in the default viewer"""
        if not hasattr(self, 'last_analysis_path') or not self.last_analysis_path:
            self.log_message("No analysis results available to view", error=True)
            return
            
        try:
            # Open the file using the default application
            import subprocess
            import platform
            
            self.log_message(f"Opening analysis results: {self.last_analysis_path}")
            
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', self.last_analysis_path])
            elif platform.system() == 'Windows':
                os.startfile(self.last_analysis_path)
            else:  # Linux
                subprocess.run(['xdg-open', self.last_analysis_path])
        except Exception as e:
            self.log_message(f"Error opening results: {str(e)}", error=True)
            traceback.print_exc()

    def clean_storage(self):
        """Clean all saved raw captures and analysis results"""
        try:
            # Clean up raw_captures directory
            raw_captures_dir = Path("raw_captures")
            if raw_captures_dir.exists():
                # Get a list of all raw capture files
                raw_files = []
                for file in raw_captures_dir.glob("*"):
                    if file.is_file() and file.suffix == ".raw":
                        raw_files.append(file)
                
                if raw_files:
                    self.log_message(f"Found {len(raw_files)} raw capture files")
                    
                    # Delete each file
                    for file in raw_files:
                        file.unlink()
                    
                    self.log_message(f"Deleted {len(raw_files)} raw capture files")
                else:
                    self.log_message("No raw capture files found")
            
            # Clean up analysis_results directory
            analysis_dir = Path("analysis_results")
            if analysis_dir.exists():
                # Get a list of all analysis result files
                analysis_files = []
                for file in analysis_dir.glob("*"):
                    if file.is_file() and file.suffix in [".png", ".jpg", ".jpeg"]:
                        analysis_files.append(file)
                
                if analysis_files:
                    self.log_message(f"Found {len(analysis_files)} analysis result files")
                    
                    # Delete each file
                    for file in analysis_files:
                        file.unlink()
                    
                    self.log_message(f"Deleted {len(analysis_files)} analysis result files")
                else:
                    self.log_message("No analysis result files found")
            
            # Show a success message
            QMessageBox.information(self, "Clean Storage", 
                                  "Storage cleaned successfully.\n\n"
                                  "Raw captures and analysis results have been deleted.")
            
        except Exception as e:
            self.log_message(f"Error cleaning storage: {str(e)}", error=True)
            traceback.print_exc()
            
            # Show error message
            QMessageBox.warning(self, "Clean Storage Error", 
                               f"Error cleaning storage: {str(e)}\n\n"
                               "Some files may not have been deleted.")

    def update_current_ui_only(self, value):
        """Update the UI elements for current without sending to Arduino"""
        # Ensure the value is valid
        value = max(0, min(100, int(value)))
        
        # Block signals to prevent slider's valueChanged from calling update_laser_intensity
        self.ui.currentSlider.blockSignals(True)
        self.ui.currentSlider.setValue(value)
        self.ui.currentSlider.blockSignals(False)
        
        # Update the current value
        self.current_value = value
        
        # Update the label (remove voltage display)
        self.ui.currentLabel.setText(f"Current: {value}%")
        
        # Log for debugging (keep voltage in log)
        self.log_message(f"Slider position updated to {value}% ({value/100 * self.max_voltage:.2f}V)")

    def resume_auto_adjustment(self):
        """Resume auto-adjustment after manual override expires"""
        if self.auto_mode and self.manual_override_active:
            self.manual_override_active = False
            self.log_message("Manual override expired - resuming auto adjustment")
            
            # Immediately trigger analysis for auto-adjustment with priority 
            if self.capturing and self.current_image is not None:
                # Force immediate frame capture and analysis
                try:
                    if hasattr(self, 'camera') and self.camera.IsOpen():
                        # First capture a new frame to ensure we're analyzing current conditions
                        self.log_message("Capturing fresh frame for analysis...")
                        self.capture_frame(force_analysis=True)
                    else:
                        # Fall back to analyzing the existing image
                        self.generate_analysis()
                except Exception as e:
                    self.log_message(f"Error resuming auto-adjustment: {str(e)}", error=True)
                    # Still try to generate analysis with existing image
                    self.generate_analysis()
            else:
                self.log_message("Cannot resume auto-adjustment: No active capture or image", error=True)

    def calculate_laser_current(self, current_percent):
        """Calculate approximate laser current in mA based on percentage"""
        # Assuming linear relationship and maximum current of 200mA at 100%
        # Adjust max_current_mA based on your specific laser diode
        max_current_mA = 200.0  
        return (current_percent / 100.0) * max_current_mA

def create_radial_weight_mask(shape, center=None, sigma=None, flat_top_radius=None):
    """Create a radial Gaussian weight mask with optional flat top
    
    Parameters:
    -----------
    shape : tuple
        Shape of the image (height, width)
    center : tuple, optional
        Center coordinates of the weight mask (y, x)
    sigma : float, optional
        Standard deviation of the Gaussian
    flat_top_radius : float, optional
        Radius of the flat top region (pixels with weight=1)
    
    Returns:
    --------
    weight_mask : ndarray
        Weight mask with shape matching the input image
    """
    # Set default center to middle of image if not provided
    if center is None:
        center = (shape[0] // 2, shape[1] // 2)
    
    # Set default sigma to 1/2 of min dimension if not provided (was 1/4)
    if sigma is None:
        sigma = min(shape) // 2  # Increased from // 4 to create more even weighting
    
    # Create coordinate grids
    y, x = np.ogrid[:shape[0], :shape[1]]
    
    # Calculate squared distance from center
    squared_dist = (y - center[0])**2 + (x - center[1])**2
    
    # If flat_top_radius is specified, create a flat top in the center
    if flat_top_radius is not None and flat_top_radius > 0:
        # Create flat region with weight 1.0
        flat_mask = squared_dist <= (flat_top_radius ** 2)
        
        # Create Gaussian fall-off for outer region
        outer_mask = ~flat_mask
        weight_mask = np.ones(shape, dtype=float)
        
        # Apply Gaussian only to outer region, starting from flat_top_radius
        # Shift the Gaussian so it starts at 1.0 at the boundary of flat region
        if np.any(outer_mask):
            outer_dist = squared_dist[outer_mask] - (flat_top_radius ** 2)
            weight_mask[outer_mask] = np.exp(-outer_dist / (2 * sigma**2))
    else:
        # Create standard Gaussian weight mask (higher at center, lower at edges)
        weight_mask = np.exp(-squared_dist / (2 * sigma**2))
    
    return weight_mask

def main():
    app = QApplication(sys.argv)
    widget = LaserSpeckleUI()
    widget.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 