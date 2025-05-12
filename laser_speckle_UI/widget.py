# This Python file uses the following encoding: utf-8
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QPushButton
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

# Path handling for imports
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the analysis modules
from histogram_saturation_analyzer import analyze_saturation_by_histogram, create_radial_weight_mask
from saturation_pixel_count_analyzer import analyze_saturation_by_pixel_count
from contrast_analyzer import analyze_contrast

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from laser_speckle_UI.ui_form import Ui_Widget

import traceback
import serial
import time
from datetime import datetime

class MatplotlibCanvas(FigureCanvasQTAgg):
    """Canvas for displaying the image and allowing ROI selection"""
    
    roi_selected = Signal(tuple)  # Signal to emit when ROI is selected (center_y, center_x, radius)
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        self.setParent(parent)
        
        # Variables for ROI selection
        self.roi_center = None
        self.roi_radius = None
        self.drawing_roi = False
        self.start_point = None
        
        # Connect events
        self.mpl_connect('button_press_event', self.on_mouse_press)
        self.mpl_connect('button_release_event', self.on_mouse_release)
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
    
    def on_mouse_press(self, event):
        if event.inaxes != self.axes:
            return
        
        # Start drawing ROI
        self.drawing_roi = True
        self.start_point = (event.xdata, event.ydata)
        self.roi_center = self.start_point
        self.roi_radius = 0
        
        # Clear any existing ROI circles
        self.redraw_roi()
    
    def on_mouse_move(self, event):
        if not self.drawing_roi or event.inaxes != self.axes:
            return
        
        # Update ROI radius based on mouse movement
        dx = event.xdata - self.start_point[0]
        dy = event.ydata - self.start_point[1]
        self.roi_radius = np.sqrt(dx**2 + dy**2)
        
        # Redraw the ROI
        self.redraw_roi()
    
    def on_mouse_release(self, event):
        if not self.drawing_roi:
            return
        
        self.drawing_roi = False
        
        # Finalize ROI selection
        if self.roi_center and self.roi_radius > 0:
            # Convert to image coordinates (y, x)
            center_x, center_y = self.roi_center
            # Emit signal with ROI information
            self.roi_selected.emit((center_y, center_x, self.roi_radius))
    
    def redraw_roi(self):
        # Clear the current figure and redraw the image
        self.axes.clear()
        if hasattr(self, 'img_data'):
            self.axes.imshow(self.img_data, cmap='gray')
        
        # Draw the ROI circle if defined
        if self.roi_center and self.roi_radius > 0:
            circle = plt.Circle(self.roi_center, self.roi_radius, 
                               fill=False, color='r', linewidth=2)
            self.axes.add_artist(circle)
        
        self.fig.canvas.draw()
    
    def update_image(self, img_data):
        """Update the displayed image"""
        self.img_data = img_data
        self.axes.clear()
        self.axes.imshow(img_data, cmap='gray')
        self.fig.canvas.draw()

class ColorLegendWidget(QFrame):
    """A widget to display color meanings for analysis results"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setMinimumHeight(100)
        self.setMaximumHeight(100)
        
        layout = QVBoxLayout(self)
        title = QLabel("Color Key for Analysis Results:")
        title.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title)
        
        color_layout = QHBoxLayout()
        
        # Create color boxes with labels
        self.add_color_item(color_layout, "darkred", "Severe Saturation:\nDecrease Current by 40%")
        self.add_color_item(color_layout, "orange", "Moderate Saturation:\nDecrease Current by 25%")
        self.add_color_item(color_layout, "gold", "Mild Saturation:\nDecrease Current by 10%")
        self.add_color_item(color_layout, "lightgreen", "Optimal Conditions:\nMaintain Current")
        self.add_color_item(color_layout, "lightblue", "Low Contrast:\nIncrease Current by 5%")
        
        layout.addLayout(color_layout)
        self.setLayout(layout)
    
    def add_color_item(self, layout, color_name, text):
        """Add a color box with label to the layout"""
        item_layout = QVBoxLayout()
        
        # Color square
        color_box = QFrame()
        color_box.setMinimumSize(20, 20)
        color_box.setMaximumSize(20, 20)
        color_box.setStyleSheet(f"background-color: {color_name};")
        
        # Label
        label = QLabel(text)
        label.setFont(QFont("Arial", 8))
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        
        box_layout = QHBoxLayout()
        box_layout.addStretch()
        box_layout.addWidget(color_box)
        box_layout.addStretch()
        
        item_layout.addLayout(box_layout)
        item_layout.addWidget(label)
        
        layout.addLayout(item_layout)

class Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set up UI
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        
        # Set up image layout in groupBox_3
        self.image_layout = QVBoxLayout(self.ui.groupBox_3)
        self.image_layout.setObjectName("image_layout")
        
        # Add color legend widget
        self.color_legend = ColorLegendWidget(self)
        self.ui.verticalLayout.addWidget(self.color_legend)
        
        # Create a recommendation label
        self.recommendation_label = QLabel(self)
        self.recommendation_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.recommendation_label.setStyleSheet("color: #004080; background-color: #e0f0ff; padding: 8px; border-radius: 4px;")
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setMinimumHeight(60)
        self.recommendation_label.setText("Laser Current Recommendation: Analyze an image to get recommendations")
        self.recommendation_label.setAlignment(Qt.AlignCenter)
        self.ui.verticalLayout.addWidget(self.recommendation_label)
        
        # Initialize variables
        self.current_image = None
        self.original_image = None
        self.roi_start = None
        self.roi_end = None
        self.roi_rect = None
        self.custom_weight_mask = None
        self.current_value = 50  # Default current value (0-100%)
        self.serial_port = None
        
        # Initialize analysis caches
        self.last_histogram_results = None
        self.last_pixel_count_results = None
        self.last_contrast_results = None
        
        # Try to connect to Arduino
        self.connect_to_arduino()
        
        # Set up matplotlib canvas
        self.canvas = MatplotlibCanvas(self)
        self.image_layout.addWidget(self.canvas)
        
        # Connect signals and slots
        self.canvas.roi_selected.connect(self.update_roi)
        self.ui.load_button.clicked.connect(self.load_image)
        self.ui.reset_roi_button.clicked.connect(self.reset_roi)
        self.ui.analyze_button.clicked.connect(self.analyze_roi)
        self.ui.horizontalSlider.valueChanged.connect(self.current_changed)
        
        # Update slider position
        self.ui.horizontalSlider.setValue(self.current_value)
        
        # Initial reset
        self.reset_roi()
    
    def connect_to_arduino(self):
        """Try to connect to Arduino for laser control"""
        try:
            # Try common serial ports
            ports_to_try = ['/dev/cu.usbmodem101', '/dev/ttyACM0', '/dev/ttyUSB0', 'COM3']
            
            for port in ports_to_try:
                try:
                    self.serial_port = serial.Serial(port, 9600, timeout=1)
                    print(f"Connected to Arduino on {port}")
                    # Set initial slider position
                    self.ui.horizontalSlider.setValue(self.current_value)
                    return
                except (serial.SerialException, OSError):
                    continue
            
            print("Could not connect to Arduino. Manual mode only.")
        except Exception as e:
            print(f"Arduino connection error: {e}")
    
    def update_current_value(self, value):
        """Update the current value and send to Arduino if connected"""
        self.current_value = value
        self.ui.current_label.setText(f"Laser Current: {value}%")
        
        # Send to Arduino if connected
        if self.serial_port and self.serial_port.is_open:
            try:
                # Map 0-100% to PWM value (0-255)
                pwm_value = int(value * 255 / 100)
                command = f"CURRENT:{pwm_value}\n"
                self.serial_port.write(command.encode())
                time.sleep(0.1)  # Allow time for Arduino to process
                print(f"Sent current value: {value}% (PWM: {pwm_value})")
            except Exception as e:
                print(f"Error sending to Arduino: {e}")
    
    def auto_adjust_current(self):
        """Automatically adjust current based on last recommendation"""
        if self.last_recommendation is None:
            self.recommendation_label.setText("No recommendation available. Analyze image first.")
            return
        
        # Get current value from slider
        current_value = self.ui.horizontalSlider.value()
        
        # Apply the adjustment
        new_value = max(0, min(100, current_value + self.last_recommendation))
        
        # Update the slider which will trigger the update_current_value method
        self.ui.horizontalSlider.setValue(int(new_value))
        
        self.recommendation_label.setText(f"Auto-adjusted: {current_value}% → {int(new_value)}% ({self.last_recommendation:+.1f}%)")
        
    def calculate_current_adjustment(self, results, method_type):
        """
        Calculate how much to adjust the laser current based on the analysis results.
        Returns a percentage adjustment value (positive = increase, negative = decrease)
        """
        current_adjustment = 0.0
        
        if method_type == "histogram":
            # Histogram-based adjustment
            if "saturation_status" in results:
                status = results["saturation_status"]
                if status == "HIGH_SATURATION":
                    # Significant saturation detected, reduce current
                    current_adjustment = -5.0
                elif status == "MODERATE_SATURATION":
                    # Some saturation detected, reduce current slightly
                    current_adjustment = -2.0
                elif status == "LOW_CONTRAST":
                    # Low contrast, increase current
                    current_adjustment = 2.0
                elif status == "OPTIMAL":
                    # Optimal settings, no adjustment needed
                    current_adjustment = 0.0
            
            # Fine-tune based on percentage of saturated pixels
            if "saturation_percentage" in results:
                sat_percent = results["saturation_percentage"]
                if sat_percent > 5.0:
                    # Adjust down proportionally to saturation percentage
                    current_adjustment = max(-10.0, -sat_percent)
                elif sat_percent <= 0.1 and current_adjustment == 0.0:
                    # Almost no saturation and not already optimal, try increasing slightly
                    current_adjustment = 1.0
        
        elif method_type == "pixel_count":
            # Pixel count-based adjustment
            if "saturation_status" in results:
                status = results["saturation_status"]
                if status == "HIGH_SATURATION":
                    # Significant saturation detected, reduce current
                    current_adjustment = -5.0
                elif status == "MODERATE_SATURATION":
                    # Some saturation detected, reduce current slightly
                    current_adjustment = -2.0
                elif status == "LOW_SATURATION":
                    # Low saturation, increase current slightly
                    current_adjustment = 1.0
                elif status == "OPTIMAL":
                    # Optimal settings, no adjustment needed
                    current_adjustment = 0.0
            
            # Fine-tune based on percentage of saturated pixels
            if "saturated_pixel_percentage" in results:
                sat_percent = results["saturated_pixel_percentage"]
                if sat_percent > 2.0:
                    # Adjust down proportionally to saturation percentage
                    current_adjustment = max(-10.0, -sat_percent * 2)
                elif sat_percent <= 0.05 and current_adjustment == 0.0:
                    # Almost no saturation and not already optimal, try increasing slightly
                    current_adjustment = 1.0
        
        elif method_type == "contrast":
            # Contrast-based adjustment
            if "mean_contrast" in results:
                mean_contrast = results["mean_contrast"]
                
                # Optimal contrast is around 0.1-0.2
                if mean_contrast < 0.05:
                    # Very low contrast, significant increase needed
                    current_adjustment = 5.0
                elif 0.05 <= mean_contrast < 0.1:
                    # Low contrast, moderate increase needed
                    current_adjustment = 2.0
                elif 0.1 <= mean_contrast <= 0.2:
                    # Optimal contrast range, no adjustment needed
                    current_adjustment = 0.0
                elif 0.2 < mean_contrast <= 0.3:
                    # Slightly high contrast, small decrease needed
                    current_adjustment = -1.0
                elif mean_contrast > 0.3:
                    # Very high contrast, significant decrease needed
                    current_adjustment = -3.0
                    
                # Further adjustment if high standard deviation
                if "contrast_std" in results:
                    std = results["contrast_std"]
                    if std > 0.2 and current_adjustment == 0:
                        # High variability in contrast, might indicate localized issues
                        current_adjustment = -1.0
        
        return current_adjustment
    
    def current_changed(self, value):
        """Handle slider value change"""
        self.current_value = value
        self.ui.current_label.setText(f"Laser Current: {value}%")
        self.update_current_value(value)
    
    def load_image(self):
        """Load a speckle image from file"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Speckle Image", "", 
            "Raw Files (*.raw);;All Files (*)", options=options
        )
        
        if not file_path:
            return
        
        try:
            # Reset ROI
            self.roi_start = None
            self.roi_end = None
            self.roi_rect = None
            
            # Load raw image
            # Assumptions:
            # - 16 bit
            # - 1024x1024 resolution (if different, need to specify in dialog)
            img_data = np.fromfile(file_path, dtype=np.uint16)
            width = 1024  # Default width
            height = 1024  # Default height
            
            # Reshape based on dimensions
            try:
                img_data = img_data.reshape((height, width))
            except ValueError:
                # Try to determine dimensions from file size
                total_pixels = img_data.size
                # Assuming square image
                side_length = int(np.sqrt(total_pixels))
                img_data = img_data.reshape((side_length, side_length))
            
            # Store the image
            self.current_image = img_data
            self.original_image = img_data.copy()
            
            # Convert to 8-bit for display
            img_8bit = np.interp(img_data, (0, 65535), (0, 255)).astype(np.uint8)
            
            # Clear the figure
            self.canvas.axes.clear()
            
            # Display the image
            self.canvas.axes.imshow(img_8bit, cmap='gray')
            self.canvas.axes.set_title(f"Loaded: {Path(file_path).name}")
            self.canvas.axes.axis('off')
            
            # Update the plot
            self.canvas.fig.tight_layout()
            self.canvas.draw()
            
            self.ui.status_label.setText(f"Loaded {Path(file_path).name}")
            self.ui.image_path_label.setText(f"File: {Path(file_path).name}")
            
            # Create the weight mask for this image
            self.custom_weight_mask = create_radial_weight_mask(img_data.shape)
                
            except Exception as e:
            traceback.print_exc()
            self.ui.status_label.setText(f"Error loading image: {str(e)}")
    
    def update_roi(self, roi_info):
        """Update the ROI parameters and weight mask"""
        center_y, center_x, radius = roi_info
        self.roi_start = (center_x, center_y)
        self.roi_end = (center_x + radius, center_y + radius)
        
        if self.current_image is not None:
            # Create custom weight mask based on ROI
            self.custom_weight_mask = self.create_custom_weight_mask()
            
            # Update UI
            self.ui.label_2.setText(f"ROI: Center=({center_x:.1f}, {center_y:.1f}), Radius={radius:.1f}")
    
    def reset_roi(self):
        """Reset ROI to default (center of image)"""
        if self.current_image is None:
            return
        
        # Set ROI to center of image with default radius
        height, width = self.current_image.shape
        self.roi_start = (width//2, height//2)
        self.roi_end = (width//2 + min(height, width)//4, height//2 + min(height, width)//4)
        
        # Update weight mask
        self.custom_weight_mask = self.create_custom_weight_mask()
        
        # Update canvas
        self.canvas.roi_center = (self.roi_start[0], self.roi_start[1])  # Convert to (x,y) for display
        self.canvas.roi_radius = min(height, width) // 4
        self.canvas.redraw_roi()
        
        # Update UI
        self.ui.label_2.setText(f"ROI: Center=({self.roi_start[0]}, {self.roi_start[1]}) to ({self.roi_end[0]}, {self.roi_end[1]})")
    
    def create_custom_weight_mask(self):
        """Create a custom weight mask based on the selected ROI"""
        if self.current_image is None or self.roi_start is None or self.roi_end is None:
            return None
        
        height, width = self.current_image.shape
        mask = np.zeros((height, width), dtype=np.float32)
        
        # Create distance map from ROI center
        y, x = np.ogrid[:height, :width]
        y_dist = ((y - self.roi_start[1]) ** 2)
        x_dist = ((x - self.roi_start[0]) ** 2)
        dist_from_center = np.sqrt(y_dist + x_dist)
        
        # Create Gaussian weight mask centered on ROI
        sigma = min(self.roi_end[0] - self.roi_start[0], self.roi_end[1] - self.roi_start[1]) / 2  # Adjust sigma based on ROI size
        weight_mask = np.exp(-0.5 * (dist_from_center / sigma) ** 2)
        
        # Further emphasize center by applying power function
        weight_mask = weight_mask ** 2
        
        # Normalize weights to [0, 1]
        weight_mask = weight_mask / weight_mask.max()
        
        return weight_mask
    
    def analyze_roi(self):
        """Analyze the selected ROI using the chosen method"""
        if self.current_image is None:
            self.ui.status_label.setText("Please select a ROI first")
            return
        
        # Determine which analysis method to use based on radio button selection
        use_histogram = self.ui.histogram_radio.isChecked() or self.ui.all_methods_radio.isChecked()
        use_pixel_count = self.ui.pixel_count_radio.isChecked() or self.ui.all_methods_radio.isChecked()
        use_contrast = self.ui.contrast_radio.isChecked() or self.ui.all_methods_radio.isChecked()
        
        # Flag to track if any analysis was performed
        analysis_performed = False
        
        # Store overall recommendation details
        recommendations = []
        status_colors = []
        
        try:
            # Create output directory if needed
            output_dir = Path("../analysis_results")
            output_dir.mkdir(exist_ok=True)
            
            # Create timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Histogram-based saturation analysis
            if use_histogram:
                analysis_performed = True
                
                # Create a modified image path for saving
                img_path = f"ROI_histogram_{timestamp}.raw"
                
                # Run the analysis
                results = analyze_saturation_by_histogram(
                    self.current_image, 
                    weight_mask=self.custom_weight_mask,
                    num_bins=256
                )
                
                # Store results for later use
                self.last_histogram_results = results
                
                # Get recommendation
                sat_prob = results.get("saturation_probability", 0)
                if sat_prob > 0.8:
                    recommendations.append("Decrease laser current by 40% (Histogram: High saturation)")
                    status_colors.append("darkred")
                elif sat_prob > 0.5:
                    recommendations.append("Decrease laser current by 25% (Histogram: Moderate saturation)")
                    status_colors.append("orange")
                elif sat_prob > 0.2:
                    recommendations.append("Decrease laser current by 10% (Histogram: Mild saturation)")
                    status_colors.append("gold")
                elif sat_prob < 0.05:
                    recommendations.append("Consider increasing laser current by 5% (Histogram: Low saturation)")
                    status_colors.append("lightblue")
                else:
                    recommendations.append("Maintain current laser settings (Histogram: Optimal)")
                    status_colors.append("lightgreen")
                
                # Plot and save results
                plt.figure(figsize=(10, 8))
                from histogram_saturation_analyzer import plot_results
                plot_results(self.current_image, results, img_path, save_output=True)
                plt.close()
            
            # Pixel count-based saturation analysis
            if use_pixel_count:
                analysis_performed = True
                
                # Create a modified image path for saving
                img_path = f"ROI_pixel_count_{timestamp}.raw"
                
                # Run the analysis
                results = analyze_saturation_by_pixel_count(
                    self.current_image, 
                    saturation_threshold=65000,
                    weight_mask=self.custom_weight_mask
                )
                
                # Store results for later use
                self.last_pixel_count_results = results
                
                # Get recommendation
                weighted_sat = results.get("weighted_saturation_percentage", 0)
                if weighted_sat > 5.0:
                    recommendations.append("Decrease laser current by 40% (Pixel Count: Severe saturation)")
                    status_colors.append("darkred")
                elif weighted_sat > 2.0:
                    recommendations.append("Decrease laser current by 25% (Pixel Count: Moderate saturation)")
                    status_colors.append("orange")
                elif weighted_sat > 0.5:
                    recommendations.append("Decrease laser current by 10% (Pixel Count: Mild saturation)")
                    status_colors.append("gold")
                elif weighted_sat < 0.1:
                    recommendations.append("Consider increasing laser current by 5% (Pixel Count: Very low saturation)")
                    status_colors.append("lightblue")
                else:
                    recommendations.append("Maintain current laser settings (Pixel Count: Optimal)")
                    status_colors.append("lightgreen")
                
                # Plot and save results
                plt.figure(figsize=(16, 6))
                from saturation_pixel_count_analyzer import plot_results
                plot_results(self.current_image, results, img_path, save_output=True)
                plt.close()
            
            # Contrast analysis
            if use_contrast:
                analysis_performed = True
                
                # Create a modified image path for saving
                img_path = f"ROI_contrast_{timestamp}.raw"
                
                # Run the analysis
                results = analyze_contrast(
                    self.current_image, 
                    window_size=7,
                    weight_mask=self.custom_weight_mask
                )
                
                # Store results for later use
                self.last_contrast_results = results
                
                # Get recommendation
                mean_contrast = results.get("mean_contrast", 0)
                if mean_contrast > 0.6:
                    recommendations.append("Decrease laser current by 20% (Contrast: Too high)")
                    status_colors.append("orange")
                elif mean_contrast < 0.15:
                    recommendations.append("Increase laser current by 10% (Contrast: Too low)")
                    status_colors.append("lightblue")
                elif mean_contrast < 0.25:
                    recommendations.append("Increase laser current by 5% (Contrast: Slightly low)")
                    status_colors.append("lightblue")
                else:
                    recommendations.append("Maintain current laser settings (Contrast: Optimal)")
                    status_colors.append("lightgreen")
                
                # Plot and save results
                plt.figure(figsize=(14, 10))
                from contrast_analyzer import plot_results
                plot_results(self.current_image, results, img_path, save_output=True)
                plt.close()
            
            # Show a message if no analysis was performed
            if not analysis_performed:
                self.ui.status_label.setText("Please select at least one analysis method")
                return
            
            # Update status and recommendation
            self.ui.status_label.setText("Analysis complete. Results saved.")
            
            # Determine overall recommendation
            if status_colors:
                # Prioritize preventing saturation over increasing contrast
                if "darkred" in status_colors:
                    recommendation = "DECREASE laser current by 40% (Significant saturation detected)"
                    self.recommendation_label.setStyleSheet("background-color: #ff9090; color: #900; padding: 8px; border-radius: 4px; border: 1px solid #c00;")
                elif "orange" in status_colors:
                    recommendation = "DECREASE laser current by 25% (Moderate saturation detected)"
                    self.recommendation_label.setStyleSheet("background-color: #ffb060; color: #930; padding: 8px; border-radius: 4px; border: 1px solid #960;")
                elif "gold" in status_colors:
                    recommendation = "DECREASE laser current by 10% (Mild saturation detected)"
                    self.recommendation_label.setStyleSheet("background-color: #ffee90; color: #960; padding: 8px; border-radius: 4px; border: 1px solid #c90;")
                elif "lightblue" in status_colors and "lightgreen" not in status_colors:
                    recommendation = "INCREASE laser current by 5% (Low contrast detected)"
                    self.recommendation_label.setStyleSheet("background-color: #d0e0ff; color: #006; padding: 8px; border-radius: 4px; border: 1px solid #00c;")
                else:
                    recommendation = "MAINTAIN current laser settings (Optimal conditions)"
                    self.recommendation_label.setStyleSheet("background-color: #d0ffd0; color: #060; padding: 8px; border-radius: 4px; border: 1px solid #090;")
                
                self.recommendation_label.setText(f"Laser Current Recommendation: {recommendation}")
            
        except Exception as e:
            traceback.print_exc()
            self.ui.status_label.setText(f"Error during analysis: {str(e)}")
    
    def generate_analysis(self):
        """Generate analysis based on current image and ROI settings"""
        if self.current_image is None:
            print("No image loaded")
            return
        
        if self.custom_weight_mask is None:
            self.custom_weight_mask = create_radial_weight_mask(self.current_image.shape)
        
        try:
            # Determine which analysis method to use based on radio button selection
            run_histogram = self.ui.histogram_radio.isChecked() or self.ui.all_methods_radio.isChecked()
            run_pixel_count = self.ui.pixel_count_radio.isChecked() or self.ui.all_methods_radio.isChecked()
            run_contrast = self.ui.contrast_radio.isChecked() or self.ui.all_methods_radio.isChecked()
            
            # Create a cropped image from the ROI
            x1, y1 = min(self.roi_start[0], self.roi_end[0]), min(self.roi_start[1], self.roi_end[1])
            x2, y2 = max(self.roi_start[0], self.roi_end[0]), max(self.roi_start[1], self.roi_end[1])
            roi_image = self.current_image[y1:y2, x1:x2]
            
            # Initialize variables for combined recommendation
            results_combined = {}
            adjustments = []
            methods_used = []
            
            # Run histogram-based saturation analysis
            if run_histogram:
                try:
                    results = analyze_saturation_by_histogram(
                        roi_image, 
                        weight_mask=self.custom_weight_mask[y1:y2, x1:x2] if self.custom_weight_mask is not None else None
                    )
                    results_combined.update(results)
                    
                    # Calculate current adjustment
                    adjustment = self.calculate_current_adjustment(results, "histogram")
                    adjustments.append(adjustment)
                    methods_used.append("histogram")
                    
                    print("Histogram Analysis - Recommendation:", adjustment)
                except Exception as e:
                    print(f"Error in histogram analysis: {e}")
                    traceback.print_exc()
            
            # Run pixel-count saturation analysis
            if run_pixel_count:
                try:
                    results = analyze_saturation_by_pixel_count(
                        roi_image, 
                        weight_mask=self.custom_weight_mask[y1:y2, x1:x2] if self.custom_weight_mask is not None else None
                    )
                    results_combined.update(results)
                    
                    # Calculate current adjustment
                    adjustment = self.calculate_current_adjustment(results, "pixel_count")
                    adjustments.append(adjustment)
                    methods_used.append("pixel_count")
                    
                    print("Pixel Count Analysis - Recommendation:", adjustment)
                except Exception as e:
                    print(f"Error in pixel count analysis: {e}")
                    traceback.print_exc()
            
            # Run contrast analysis
            if run_contrast:
                try:
                    results = analyze_contrast(
                        roi_image, 
                        weight_mask=self.custom_weight_mask[y1:y2, x1:x2] if self.custom_weight_mask is not None else None
                    )
                    results_combined.update(results)
                    
                    # Calculate current adjustment
                    adjustment = self.calculate_current_adjustment(results, "contrast")
                    adjustments.append(adjustment)
                    methods_used.append("contrast")
                    
                    print("Contrast Analysis - Recommendation:", adjustment)
        except Exception as e:
                    print(f"Error in contrast analysis: {e}")
                    traceback.print_exc()
            
            # Calculate final adjustment recommendation (average of all used methods)
            if adjustments:
                final_adjustment = sum(adjustments) / len(adjustments)
                self.last_recommendation = final_adjustment
                
                # Format recommendation text
                current_value = self.ui.horizontalSlider.value()
                new_value = max(0, min(100, current_value + final_adjustment))
                
                recommendation_text = f"Recommendation: {final_adjustment:+.1f}% ({current_value}% → {int(new_value)}%)\n"
                recommendation_text += "Methods: " + ", ".join(methods_used)
                
                # Set color based on recommendation
                if abs(final_adjustment) < 1:
                    color = "green"
                    recommendation_text = "OPTIMAL: " + recommendation_text
                elif final_adjustment < 0:
                    color = "orange"
                    recommendation_text = "DECREASE CURRENT: " + recommendation_text
                else:
                    color = "#CC8800"  # Dark yellow
                    recommendation_text = "INCREASE CURRENT: " + recommendation_text
                
                self.recommendation_label.setStyleSheet(f"color: white; background-color: {color}; padding: 8px; border-radius: 4px;")
                self.recommendation_label.setText(recommendation_text)
                
                # Enable auto-adjust button if it exists
                if hasattr(self.ui, 'auto_adjust_button'):
                    self.ui.auto_adjust_button.setEnabled(True)
                
        except Exception as e:
            print(f"Error in analysis: {e}")
            traceback.print_exc()
            self.ui.status_label.setText(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    sys.exit(app.exec())
