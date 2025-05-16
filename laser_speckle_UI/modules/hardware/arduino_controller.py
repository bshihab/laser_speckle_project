#!/usr/bin/env python
# -*- coding: utf-8 -*-

import serial
import serial.tools.list_ports
import time
import glob

class ArduinoController:
    """
    Class to handle Arduino communication for laser control
    """
    
    def __init__(self, logger_callback=None):
        """
        Initialize the Arduino controller
        
        Args:
            logger_callback: Function to call for logging messages
        """
        self.serial_port = None
        self.logger = logger_callback if logger_callback else print
    
    def log(self, message, error=False):
        """Log a message using the provided logger callback"""
        if self.logger:
            self.logger(message, error)
    
    def connect(self):
        """
        Establish connection to Arduino for laser control with enhanced detection
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        self.serial_port = None
        try:
            # Get a list of available serial ports
            available_ports = list(serial.tools.list_ports.comports())
            self.log(f"Found {len(available_ports)} serial ports")
            
            # First, look for a port specifically containing 'UNO R4 Minima' in the description
            for port in available_ports:
                if "UNO R4 Minima" in port.description:
                    self.log(f"Found Arduino Uno R4 Minima at: {port.device}")
                    try:
                        self.serial_port = serial.Serial(port.device, 9600, timeout=1)
                        self.log(f"Successfully connected to Arduino at {port.device}")
                        return True
                    except Exception as e:
                        self.log(f"Error connecting to detected Arduino at {port.device}: {str(e)}", error=True)
            
            # If specific detection failed, try common port names
            ports_to_try = [
                '/dev/cu.usbmodem1101',  # Common port for Uno R4 Minima on macOS
                '/dev/cu.usbmodem*',     # Wildcard for macOS Arduino ports
                '/dev/ttyACM0',          # Common port on Linux
                '/dev/ttyUSB0',          # Alternative Linux port
                'COM3'                   # Common Windows port
            ]
            
            for pattern in ports_to_try:
                # Expand wildcards if present
                if '*' in pattern:
                    matching_ports = glob.glob(pattern)
                    self.log(f"Checking pattern {pattern}, found matches: {matching_ports}")
                    for port in matching_ports:
                        try:
                            self.serial_port = serial.Serial(port, 9600, timeout=1)
                            self.log(f"Successfully connected to Arduino at {port}")
                            return True
                        except Exception as e:
                            self.log(f"Error connecting to port {port}: {str(e)}", error=True)
                else:
                    try:
                        self.serial_port = serial.Serial(pattern, 9600, timeout=1)
                        self.log(f"Successfully connected to Arduino at {pattern}")
                        return True
                    except Exception as e:
                        self.log(f"Error connecting to port {pattern}: {str(e)}", error=True)
            
            self.log("Could not connect to Arduino. Will operate in manual mode only.", error=True)
            return False
            
        except Exception as e:
            self.log(f"Serial connection setup error: {str(e)}", error=True)
            return False
            
    def disconnect(self):
        """Disconnect from the Arduino"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
                self.log("Arduino disconnected")
            except Exception as e:
                self.log(f"Error disconnecting Arduino: {str(e)}", error=True)
        self.serial_port = None
    
    def send_current(self, current_percent):
        """
        Send current value (as percentage) to Arduino
        Uses the protocol defined in user_controlled_UI.ino
        
        Args:
            current_percent: Current value as percentage (0-100)
            
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        if self.serial_port is None:
            self.log("Cannot send to Arduino: No connection established", error=True)
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
            self.log(f"Sending to Arduino: Current {current_percent}% → {current_mA:.1f} mA")
            
            # Send the packet
            self.serial_port.write(packet)
            
            # Check for response (non-blocking)
            time.sleep(0.1)  # Give Arduino time to respond
            if self.serial_port.in_waiting > 0:
                response = self.serial_port.read(self.serial_port.in_waiting)
                # We don't log the response hex data
            
            return True
            
        except Exception as e:
            self.log(f"Error sending to Arduino: {str(e)}", error=True)
            # Try to reconnect if connection was lost
            if "write operation" in str(e).lower() or "port is closed" in str(e).lower():
                self.log("Connection appears to be lost. Attempting to reconnect...", error=True)
                self.connect()
            return False
    
    def calculate_laser_current(self, percentage):
        """
        Calculate the actual laser current in mA based on the percentage value
        
        Args:
            percentage: Current value as percentage (0-100)
            
        Returns:
            float: Current in mA
        """
        # Example conversion function - customize based on your laser specs
        # This assumes a linear relationship between percentage and current
        # with 100% corresponding to 200mA
        return percentage * 2.0  # 2mA per percent 