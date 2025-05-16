#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Signal

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