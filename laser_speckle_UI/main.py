#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import numpy as np
import traceback
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QTimer, Slot
import matplotlib.pyplot as plt

# Import the generated UI
from updated_ui import Ui_LaserSpeckleUI

# Import modularized components
from modules.ui.canvas import MatplotlibCanvas
from modules.hardware.camera_controller import CameraController
from modules.hardware.arduino_controller import ArduinoController
from modules.analysis.analyzer import ImageAnalyzer
from modules.utils.image_utils import create_radial_weight_mask

class LaserSpeckleUI(QWidget):
    """
    Main application for laser speckle analysis
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set up UI
        self.ui = Ui_LaserSpeckleUI()
        self.ui.setupUi(self)
        
        # Initialize application state
        self.current_image = None
        self.current_method = 'histogram'  # Default analysis method
        self.is_auto_mode = False
        self.capturing = False
        self.current_value = 20  # Default laser intensity (percentage)
        
        # Set default values for exposure and frequency inputs
        self.ui.exposureInput.setText("10")
        self.ui.frequencyInput.setText("10")
        
        # Initialize components
        self.camera = CameraController(logger_callback=self.log_message)
        self.arduino = ArduinoController(logger_callback=self.log_message)
        self.analyzer = ImageAnalyzer(logger_callback=self.log_message)
        
        # Create a label for current recommendations
        self.recommendation_label = self.ui.recommendationLabel
        self.recommendation_label.setText("Current Recommendation: Analyze an image to get laser current recommendations")
        
        # Set up visualization canvases
        self.setup_canvases()
        
        # Connect UI signals to slots
        self.connect_signals()
        
        # Initialize hardware connections
        self.arduino.connect()
        
        # Set up capture timer
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.capture_frame)
        
        # Set initial UI mode
        self.set_manual_mode()
        
        # Log startup
        self.log_message("Laser Speckle Analysis UI started")
    
    def setup_canvases(self):
        """Set up the Matplotlib canvases for visualization"""
        # Preview canvas for live camera feed
        self.preview_canvas = MatplotlibCanvas(self.ui.previewFrame)
        self.ui.previewLayout.addWidget(self.preview_canvas)
        self.preview_canvas.roi_selected.connect(self.update_roi)
        
        # Raw image canvas for displaying loaded images
        self.raw_canvas = MatplotlibCanvas(self.ui.rawFrame)
        self.ui.rawLayout.addWidget(self.raw_canvas)
        
        # Speckle analysis canvas for visualization
        self.speckle_canvas = MatplotlibCanvas(self.ui.speckleFrame)
        self.ui.speckleLayout.addWidget(self.speckle_canvas)
    
    def connect_signals(self):
        """Connect UI signals to slots"""
        # Button connections
        self.ui.loadButton.clicked.connect(self.load_image)
        self.ui.captureButton.clicked.connect(self.start_capture)
        self.ui.stopButton.clicked.connect(self.stop_capture)
        self.ui.analyzeButton.clicked.connect(self.generate_analysis)
        self.ui.resetRoiButton.clicked.connect(self.reset_roi)
        self.ui.saveButton.clicked.connect(self.save_results)
        self.ui.cleanButton.clicked.connect(self.clean_storage)
        self.ui.viewResultsButton.clicked.connect(self.view_results)
        
        # Radio button connections
        self.ui.histogramRadio.toggled.connect(self.update_analysis_method)
        self.ui.pixelCountRadio.toggled.connect(self.update_analysis_method)
        self.ui.contrastRadio.toggled.connect(self.update_analysis_method)
        
        # Mode selection
        self.ui.autoRadio.toggled.connect(self.handle_mode_change)
        self.ui.manualRadio.toggled.connect(self.handle_mode_change)
        
        # Slider connection
        self.ui.currentSlider.valueChanged.connect(self.update_laser_intensity)
    
    def log_message(self, message, error=False):
        """Add a message to the log display"""
        # Format with timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = "ERROR: " if error else "INFO: "
        formatted_msg = f"[{timestamp}] {prefix}{message}"
        
        # Add to log display
        self.ui.logText.appendPlainText(formatted_msg)
        
        # Auto-scroll to bottom
        self.ui.logText.verticalScrollBar().setValue(
            self.ui.logText.verticalScrollBar().maximum()
        )
        
        # If error, print to console as well
        if error:
            print(f"ERROR: {message}")
    
    def handle_mode_change(self, checked):
        """Handle changes between auto and manual modes"""
        if checked:  # Only process when a button is checked (not when unchecked)
            if self.sender() == self.ui.autoRadio:
                self.set_auto_mode()
            else:
                self.set_manual_mode()
    
    def set_auto_mode(self):
        """Enable automatic laser adjustment mode"""
        self.is_auto_mode = True
        self.ui.currentSlider.setEnabled(False)
        self.ui.currentLabel.setText("Auto Mode (Current: {:.1f}%)".format(self.current_value))
        self.log_message("Switched to AUTO mode - laser intensity will adjust automatically")
        self.update_mode_ui()
    
    def set_manual_mode(self):
        """Enable manual laser adjustment mode"""
        self.is_auto_mode = False
        self.ui.currentSlider.setEnabled(True)
        self.ui.currentLabel.setText("Manual Mode (Current: {:.1f}%)".format(self.current_value))
        self.log_message("Switched to MANUAL mode - adjust laser intensity with slider")
        self.update_mode_ui()
    
    def update_mode_ui(self):
        """Update UI elements based on current mode"""
        # Set slider position to match current value
        self.ui.currentSlider.blockSignals(True)
        self.ui.currentSlider.setValue(int(self.current_value * 10))  # Scale to slider range
        self.ui.currentSlider.blockSignals(False)
        
        # Update current value display
        self.ui.currentValue.setText(f"{self.current_value:.1f}%")
    
    def update_analysis_method(self, checked):
        """Update the current analysis method based on radio button selection"""
        if not checked:
            return
            
        if self.sender() == self.ui.histogramRadio:
            self.current_method = 'histogram'
        elif self.sender() == self.ui.pixelCountRadio:
            self.current_method = 'pixel_count'
        elif self.sender() == self.ui.contrastRadio:
            self.current_method = 'contrast'
            
        self.log_message(f"Analysis method changed to: {self.current_method}")
    
    def update_roi(self, roi_info):
        """Update the region of interest"""
        center_y, center_x, radius = roi_info
        self.analyzer.set_roi(roi_info)
        
        # Update ROI display
        self.ui.roiLabel.setText(f"ROI: ({center_x}, {center_y}) r={radius}")
        
        # If we have an image, analyze it with the new ROI
        if self.current_image is not None:
            self.generate_analysis()
    
    def reset_roi(self):
        """Reset the region of interest"""
        self.analyzer.reset_roi()
        self.ui.roiLabel.setText("ROI: None")
        
        # Clear ROI from canvases
        self.preview_canvas.clear_roi()
        self.raw_canvas.clear_roi()
        
        # If we have an image, reanalyze without ROI
        if self.current_image is not None:
            self.generate_analysis()
    
    def update_laser_intensity(self, value):
        """Update the laser intensity based on slider value"""
        if self.is_auto_mode:
            return  # Ignore manual adjustments in auto mode
            
        # Convert slider value (0-1000) to percentage (0-100)
        percentage = value / 10.0
        
        # Update current value
        self.current_value = percentage
        
        # Update display
        self.ui.currentValue.setText(f"{percentage:.1f}%")
        self.ui.currentLabel.setText(f"Manual Mode (Current: {percentage:.1f}%)")
        
        # Send to Arduino
        self.arduino.send_current(percentage)
    
    def load_image(self):
        """Load an image file for analysis"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Raw Images (*.raw);;All Files (*)"
        )
        
        if not file_path:
            return
            
        self.log_message(f"Loading image: {file_path}")
        
        try:
            # For raw files, need width and height
            # Default to 960x1200 if not specified
            width, height = 960, 1200
            
            # Read image data
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Convert to numpy array (assuming 16-bit)
            img_data = np.frombuffer(data, dtype=np.uint16).reshape(height, width)
            
            # Store image
            self.current_image = img_data
            
            # Display in raw canvas
            self.raw_canvas.update_image(img_data)
            
            # Log success
            self.log_message(f"Image loaded successfully: {width}x{height}, 16-bit")
            
            # Automatically analyze
            self.generate_analysis()
            
        except Exception as e:
            self.log_message(f"Error loading image: {str(e)}", error=True)
            traceback.print_exc()
    
    def generate_analysis(self):
        """Analyze the current image"""
        if self.current_image is None:
            self.log_message("No image to analyze", error=True)
            return
            
        self.log_message(f"Generating analysis using method: {self.current_method}")
        
        # Run the analysis
        results = self.analyzer.analyze_image(self.current_image, method=self.current_method)
        
        if results:
            # Display results based on method
            if self.current_method == 'histogram':
                self.display_histogram_results(results)
            elif self.current_method == 'pixel_count':
                self.display_pixel_count_results(results)
            elif self.current_method == 'contrast':
                self.display_contrast_results(results)
            
            # Display visualization
            self.display_analysis_visualization(results, self.current_method)
            
            # Calculate adjustment if in auto mode
            if self.is_auto_mode:
                adjustment = self.analyzer.calculate_adjustment(
                    results, self.current_method, self.current_value
                )
                
                # Apply adjustment if needed
                if abs(adjustment) > 0.01:  # Small threshold to prevent tiny adjustments
                    new_value = max(0, min(100, self.current_value + adjustment))
                    self.log_message(f"Auto-adjusting laser intensity: {self.current_value:.1f}% → {new_value:.1f}% (Δ{adjustment:+.1f}%)")
                    self.current_value = new_value
                    self.arduino.send_current(new_value)
                    self.update_mode_ui()
                    
                    # Update recommendation label
                    if adjustment > 0:
                        status = "INCREASING"
                        recommendation = "Image too dark, increasing laser intensity"
                    else:
                        status = "DECREASING"
                        recommendation = "Image too bright, decreasing laser intensity"
                    
                    self.update_recommendation_label(status, recommendation, adjustment)
                else:
                    # Update recommendation label for optimal/stable condition
                    self.update_recommendation_label("OPTIMAL", "Image analysis indicates optimal laser intensity")
            else:
                # In manual mode, just show recommendation
                adjustment = self.analyzer.calculate_adjustment(
                    results, self.current_method, self.current_value
                )
                
                if abs(adjustment) > 0.01:
                    if adjustment > 0:
                        status = "RECOMMENDED"
                        recommendation = "Image appears dark, recommend increasing intensity"
                    else:
                        status = "RECOMMENDED"
                        recommendation = "Image appears bright, recommend decreasing intensity"
                    
                    self.update_recommendation_label(status, recommendation, adjustment)
                else:
                    self.update_recommendation_label("OPTIMAL", "Current intensity appears optimal")
    
    def display_histogram_results(self, results):
        """Display results from histogram analysis"""
        # Update stats labels
        self.ui.meanLabel.setText(f"Mean Intensity: {results.get('weighted_mean', 0):.1f} | Raw: {results.get('unweighted_mean', 0):.1f}")
        self.ui.saturationLabel.setText(f"Saturated Pixels: {results.get('weighted_saturation_percentage', 0):.2f}% | Raw: {results.get('unweighted_saturated_percentage', 0):.2f}%")
        high_sum = results.get('high_intensity_sum', 0)
        self.ui.contrastLabel.setText(f"High Intensity: {high_sum:.2f}% | Highest Bin: {results.get('highest_bin_percentage', 0):.2f}%")
    
    def display_pixel_count_results(self, results):
        """Display results from pixel count analysis"""
        # Update stats labels
        self.ui.meanLabel.setText(f"Mean Intensity: {results.get('mean_intensity', 0):.1f}")
        self.ui.saturationLabel.setText(f"Saturated Pixels: {results.get('saturation_percentage', 0):.2f}%")
        self.ui.contrastLabel.setText(f"Bright Pixels: {results.get('bright_pixel_percentage', 0):.2f}%")
    
    def display_contrast_results(self, results):
        """Display results from contrast analysis"""
        # Update stats labels
        self.ui.meanLabel.setText(f"Mean Intensity: {results.get('weighted_mean', 0):.1f}")
        self.ui.contrastLabel.setText(f"Contrast Ratio: {results.get('global_contrast', 0):.3f} | Local: {results.get('mean_contrast', 0):.3f}")
        self.ui.saturationLabel.setText(f"Optimal Contrast: {results.get('optimal_contrast_percentage', 0):.1f}%")
    
    def update_recommendation_label(self, status, recommendation, value=None):
        """Update the recommendation label with current status"""
        if value is not None:
            value_text = f" ({value:+.1f}%)"
        else:
            value_text = ""
            
        styled_text = f"<b>{status}{value_text}:</b> {recommendation}"
        
        # Set color based on status
        if status == "OPTIMAL":
            color = "#007700"  # Green
        elif status == "INCREASING" or status == "DECREASING":
            color = "#FF6600"  # Orange
        elif status == "RECOMMENDED":
            color = "#0055AA"  # Blue
        else:
            color = "#555555"  # Gray
            
        self.recommendation_label.setStyleSheet(f"color: {color}; background-color: #e0f0ff; padding: 8px; border-radius: 4px;")
        self.recommendation_label.setText(styled_text)
    
    def display_analysis_visualization(self, results, method):
        """Display analysis visualization in the speckle canvas"""
        try:
            # Clear the canvas
            self.speckle_canvas.axes.clear()
            
            # Determine which visualization to show based on method
            if method == 'histogram' and "saturation_map" in results:
                self.speckle_canvas.axes.imshow(results["saturation_map"])
                self.speckle_canvas.axes.set_title("Histogram Saturation Analysis")
                
            elif method == 'pixel_count' and "saturation_map" in results:
                self.speckle_canvas.axes.imshow(results["saturation_map"])
                self.speckle_canvas.axes.set_title("Pixel Count Saturation Analysis")
                
            elif method == 'contrast' and "contrast_vis_map" in results:
                self.speckle_canvas.axes.imshow(results["contrast_vis_map"])
                self.speckle_canvas.axes.set_title("Contrast Analysis")
                
            self.speckle_canvas.axes.axis('off')
            self.speckle_canvas.draw()
            
        except Exception as e:
            self.log_message(f"Error displaying analysis visualization: {e}", error=True)
            traceback.print_exc()
    
    def start_capture(self):
        """Begin continuous capture from the camera"""
        if self.capturing:
            self.log_message("Capture already in progress")
            return
            
        # Connect camera if not already connected
        if not hasattr(self.camera, 'camera') or self.camera.camera is None:
            success = self.camera.connect_camera()
            if not success:
                QMessageBox.warning(
                    self, "No Camera Found",
                    "No Basler cameras were detected.\n\n"
                    "Please ensure your camera is connected and powered on.\n\n"
                    "You can still use the application in 'load image' mode to analyze "
                    "existing raw files."
                )
                return
        
        # Get exposure time from UI
        try:
            exposure_ms = float(self.ui.exposureInput.text())
            if exposure_ms <= 0:
                exposure_ms = 10  # Default to 10ms if not set
                self.ui.exposureInput.setText("10")
            self.camera.set_exposure(exposure_ms)
        except:
            self.log_message("Invalid exposure time, using default 10ms", error=True)
            exposure_ms = 10
            self.ui.exposureInput.setText("10")
            self.camera.set_exposure(exposure_ms)
        
        # Set capture interval from UI
        try:
            update_frequency_ms = int(self.ui.frequencyInput.text())
            if update_frequency_ms <= 0:
                update_frequency_ms = 10  # Default to 10ms if not set
                self.ui.frequencyInput.setText("10")
            self.capture_timer.setInterval(update_frequency_ms)
        except:
            self.log_message("Invalid frequency, using default 10ms", error=True)
            update_frequency_ms = 10
            self.ui.frequencyInput.setText("10")
            self.capture_timer.setInterval(update_frequency_ms)
        
        # Start the timer
        self.capturing = True
        self.capture_timer.start()
        self.log_message(f"Started capture with {exposure_ms}ms exposure, {update_frequency_ms}ms interval")
        
        # Update UI
        self.ui.captureButton.setEnabled(False)
        self.ui.stopButton.setEnabled(True)
    
    def stop_capture(self):
        """Stop continuous capture"""
        if not self.capturing:
            return
            
        # Stop the timer
        self.capture_timer.stop()
        self.capturing = False
        self.log_message("Stopped capture")
        
        # Update UI
        self.ui.captureButton.setEnabled(True)
        self.ui.stopButton.setEnabled(False)
    
    def capture_frame(self):
        """Capture a single frame from the camera"""
        # Capture image from camera
        img = self.camera.capture_frame()
        
        if img is not None:
            # Store the current image
            self.current_image = img
            
            # Display the image
            self.preview_canvas.update_image(img)
            
            # Analyze the image if in auto mode
            if self.is_auto_mode:
                self.generate_analysis()
    
    def save_results(self):
        """Save the current image and analysis results"""
        if self.current_image is None:
            self.log_message("No image to save", error=True)
            return
            
        try:
            # Create timestamp for filenames
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # Save raw image
            save_dir = Path("raw_captures")
            os.makedirs(save_dir, exist_ok=True)
            img_path = save_dir / f"capture_{timestamp}.raw"
            self.current_image.tofile(img_path)
            self.log_message(f"Saved raw image to {img_path}")
            
            # Save analysis visualization
            save_dir = Path("analysis_results")
            os.makedirs(save_dir, exist_ok=True)
            
            # Save matplotlib figure
            fig_path = save_dir / f"analysis_{timestamp}_{self.current_method}.png"
            self.speckle_canvas.figure.savefig(fig_path)
            self.log_message(f"Saved analysis visualization to {fig_path}")
            
        except Exception as e:
            self.log_message(f"Error saving results: {str(e)}", error=True)
            traceback.print_exc()
    
    def view_results(self):
        """Open the analysis results directory"""
        try:
            save_dir = Path("analysis_results")
            os.makedirs(save_dir, exist_ok=True)
            
            # Use system-specific commands to open directory
            import platform
            if platform.system() == "Windows":
                os.startfile(save_dir)
            elif platform.system() == "Darwin":  # macOS
                os.system(f"open {save_dir}")
            else:  # Linux
                os.system(f"xdg-open {save_dir}")
                
        except Exception as e:
            self.log_message(f"Error opening results directory: {str(e)}", error=True)
            traceback.print_exc()
    
    def clean_storage(self):
        """Clean up old raw captures and analysis results"""
        try:
            # Confirm with user
            reply = QMessageBox.question(
                self, "Clean Storage",
                "This will delete all raw captures and analysis results. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
                
            # Delete raw captures
            raw_dir = Path("raw_captures")
            if raw_dir.exists():
                for file in raw_dir.glob("*.*"):
                    file.unlink()
                self.log_message(f"Cleaned raw captures directory")
                
            # Delete analysis results
            results_dir = Path("analysis_results")
            if results_dir.exists():
                for file in results_dir.glob("*.*"):
                    file.unlink()
                self.log_message(f"Cleaned analysis results directory")
                
        except Exception as e:
            self.log_message(f"Error cleaning storage: {str(e)}", error=True)
            traceback.print_exc()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop capture if running
        if self.capturing:
            self.stop_capture()
            
        # Disconnect hardware
        self.camera.disconnect()
        self.arduino.disconnect()
        
        # Accept the close event
        event.accept()


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    window = LaserSpeckleUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 