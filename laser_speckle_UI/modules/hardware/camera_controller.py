#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
from pypylon import pylon
import traceback
import time
from pathlib import Path
import os

class CameraController:
    """
    Class to handle Basler camera operations
    """
    
    def __init__(self, logger_callback=None):
        """
        Initialize the camera controller
        
        Args:
            logger_callback: Function to call for logging messages
        """
        self.camera = None
        self.logger = logger_callback if logger_callback else print
        self.exposure_time_us = 10000  # Default 10ms
    
    def log(self, message, error=False):
        """Log a message using the provided logger callback"""
        if self.logger:
            self.logger(message, error)
    
    def connect_camera(self):
        """Connect to the first available Basler camera"""
        try:
            # Get all available devices
            available_devices = pylon.TlFactory.GetInstance().EnumerateDevices()
            
            if len(available_devices) == 0:
                self.log("No Basler cameras found. Please connect a camera and try again.", error=True)
                return False
            
            # Create an instant camera object with the first available camera
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            self.camera.Open()
            
            # Log camera info
            self.log(f"Connected to camera: {self.camera.GetDeviceInfo().GetModelName()}")
            self.log(f"Serial Number: {self.camera.GetDeviceInfo().GetSerialNumber()}")
            
            # Set default exposure
            self.set_exposure(10)  # 10ms default
            
            return True
            
        except Exception as e:
            self.log(f"Error connecting to camera: {str(e)}", error=True)
            traceback.print_exc()
            self.camera = None
            return False
    
    def disconnect(self):
        """Disconnect from the camera"""
        if self.camera:
            try:
                self.camera.Close()
                self.log("Camera disconnected")
            except Exception as e:
                self.log(f"Error disconnecting camera: {str(e)}", error=True)
            self.camera = None
    
    def set_exposure(self, exposure_ms):
        """
        Set the camera exposure time in milliseconds
        
        Args:
            exposure_ms: Exposure time in milliseconds
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.camera:
            self.log("Cannot set exposure: No camera connected", error=True)
            return False
            
        try:
            # Convert milliseconds to microseconds
            exposure_us = int(exposure_ms * 1000)
            self.camera.ExposureTime.SetValue(exposure_us)
            self.exposure_time_us = exposure_us
            self.log(f"Exposure time set to {exposure_ms}ms ({exposure_us}µs)")
            return True
        except Exception as e:
            self.log(f"Failed to set exposure time: {str(e)}", error=True)
            return False
    
    def capture_frame(self):
        """
        Capture a single frame from the camera
        
        Returns:
            numpy.ndarray: The captured image or None if capture failed
        """
        if not self.camera:
            self.log("Cannot capture frame: No camera connected", error=True)
            return None
            
        try:
            # Capture an image with timeout (5 seconds)
            grab_result = self.camera.GrabOne(5000)
            
            if grab_result.GrabSucceeded():
                # Convert to numpy array
                img = grab_result.GetArray()
                
                # Release the grab result
                grab_result.Release()
                
                return img
            else:
                self.log(f"Error: {grab_result.GetErrorCode()} {grab_result.GetErrorDescription()}", error=True)
                grab_result.Release()
                return None
                
        except Exception as e:
            self.log(f"Error capturing frame: {str(e)}", error=True)
            traceback.print_exc()
            return None
    
    def save_raw_image(self, img, directory="raw_captures", basename=None):
        """
        Save a raw image to disk
        
        Args:
            img: Numpy array image data
            directory: Directory to save the image in
            basename: Base filename (without extension)
            
        Returns:
            str: Path to the saved file or None if save failed
        """
        if img is None:
            self.log("Cannot save: No image data", error=True)
            return None
            
        try:
            # Ensure directory exists
            save_dir = Path(directory)
            os.makedirs(save_dir, exist_ok=True)
            
            # Generate filename if not provided
            if basename is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                exposure_ms = self.exposure_time_us / 1000
                basename = f"capture_{timestamp}_exp{int(exposure_ms)}ms"
            
            # Full path with .raw extension
            filepath = save_dir / f"{basename}.raw"
            
            # Save raw data
            img.tofile(filepath)
            
            self.log(f"Saved raw image to {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.log(f"Error saving raw image: {str(e)}", error=True)
            traceback.print_exc()
            return None 