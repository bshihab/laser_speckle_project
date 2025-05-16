# Laser Speckle Analysis Project

This project implements a system for capturing and analyzing laser speckle patterns in real-time. It consists of several components:

1. A modern Python-based UI application for laser speckle analysis
2. Arduino-based hardware control for laser intensity adjustment
3. Image analysis tools for contrast and saturation measurements
4. Basler camera integration for image capture

## Project Structure

- `laser_speckle_UI/` - Main UI application for laser speckle analysis
  - `updated_widget.py` - Modern UI implementation with advanced features
  - `updated_ui.py` and `updated_ui.ui` - UI definitions
- `user_controlled_UI/` - Simple UI for controlling laser intensity via Arduino
  - `UI.py` - Simple UI implementation
  - `user_controlled_UI.ino` - Arduino code for laser control
- `camera/` - Camera integration code
  - `camera_setup.py` - Basler camera setup and configuration
- `analysis_results/` - Output directory for analysis results
- Analysis modules:
  - `histogram_saturation_analyzer.py` - Analyzes image saturation using histograms
  - `saturation_pixel_count_analyzer.py` - Analyzes image saturation using pixel counts
  - `contrast_analyzer.py` - Analyzes contrast in speckle patterns
  - `exposure_calibration.py` - Calibrates camera exposure settings
  - `optimal_exposure_finder.py` - Finds optimal exposure settings for speckle patterns

## Prerequisites

### Hardware Requirements
- Arduino board
- Basler camera (pylon SDK required)
- Digital-to-Analog Converter (DAC) connected to Arduino pin A0
- Laser source connected to DAC output

### Software Dependencies
1. Python 3.8+ environment (Python 3.10 recommended)
2. PySide6 for UI
3. PyPylon for Basler camera integration
4. NumPy, Matplotlib for analysis
5. Basler Pylon SDK (must be installed separately)
6. Arduino IDE for uploading Arduino code

## Installation

### 1. Setting Up the Python Environment

Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install the required Python packages:
```bash
pip install PySide6 numpy matplotlib pyserial pypylon opencv-python
```

Note: PyPylon may require additional installation steps. Please refer to the [Basler Pylon SDK documentation](https://docs.baslerweb.com/overview).

### 2. Arduino Setup

1. Open the Arduino IDE
2. Load the `user_controlled_UI/user_controlled_UI.ino` file
3. Connect your Arduino board to your computer
4. Upload the sketch to the Arduino

### 3. Hardware Connections

1. Connect the DAC to Arduino pin A0
2. Connect the laser source to the DAC output
3. Connect the Basler camera to the computer via USB

## Running the Applications

### Laser Speckle UI (Advanced)

This is the main application for advanced laser speckle analysis:

```bash
cd laser_speckle_UI
python updated_widget.py
```

Features:
- Capture images from Basler camera with configurable exposure
- Analyze speckle contrast with advanced algorithms
- Automatic ROI selection
- Auto-adjustment of laser intensity based on analysis
- Save and visualize analysis results

### User Controlled UI (Simple)

A simple UI for manually controlling laser intensity:

```bash
cd user_controlled_UI
python UI.py
```

Features:
- Slider for manually adjusting laser intensity
- Real-time feedback of laser current and temperature
- Current vs. Voltage plotting

### Camera Setup/Testing

To test the camera setup and capture raw images:

```bash
cd camera
python camera_setup.py
```

## Debugging Guide

### Serial Connection Issues
- Check the Arduino connection port in UI.py (currently set to `/dev/cu.usbmodem101`)
- The code includes a retry mechanism to establish serial connection

### Camera Connection Issues
- Ensure Basler Pylon SDK is properly installed
- Check if the camera is detected using Basler's Pylon Viewer application
- Verify permissions for camera access

### UI Display Issues
- The UI files are designed for PySide6. Ensure you have the correct version installed
- Form paths may need to be adjusted based on your installation location

## Data Analysis Tools

The project includes several standalone analysis scripts:

- `contrast_analyzer.py` - Analyzes contrast in speckle patterns
  ```bash
  python contrast_analyzer.py --image path/to/your/image.raw --width 960 --height 1200
  ```

- `histogram_saturation_analyzer.py` - Analyzes image saturation
  ```bash
  python histogram_saturation_analyzer.py --image path/to/your/image.raw
  ```

## Known Issues

- The UI.py file has a hardcoded path to the UI file that may need to be updated:
  ```python
  file = QFile("/Users/bilalshihab/dev/laser_speckle_project/laser_speckle_UI/form.ui")
  ```
  