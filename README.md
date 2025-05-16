# Laser Speckle Analysis Project

This project implements a sophisticated system for capturing and analyzing laser speckle patterns in real-time. It consists of several components:

1. A modern Python-based UI application for laser speckle analysis
2. Arduino-based hardware control for laser intensity adjustment
3. Image analysis tools for contrast and saturation measurements
4. Basler camera integration for image capture

## Project Structure

- `laser_speckle_UI/` - Main UI application for laser speckle analysis
  - `updated_widget.py` - **Complete, all-in-one solution** with camera integration and Arduino control
  - `main.py` - **New modularized entry point** that uses components from the modules directory
  - `modules/` - **Modularized components**
    - `ui/` - User interface components
      - `canvas.py` - MatplotlibCanvas class for image display and ROI selection
    - `hardware/` - Hardware control modules
      - `camera_controller.py` - Basler camera integration
      - `arduino_controller.py` - Arduino communication
    - `analysis/` - Image analysis modules
      - `analyzer.py` - Image analysis algorithms
    - `utils/` - Utility functions
      - `image_utils.py` - Image processing utilities
  - `updated_ui.py` and `updated_ui.ui` - UI definitions
- `user_controlled_UI/` - Alternative simple UI for controlling laser intensity (not needed if using updated_widget.py)
  - `UI.py` - Simple UI implementation
  - `user_controlled_UI.ino` - Arduino code for laser control
- `camera/` - Camera integration code
  - `camera_setup.py` - Basler camera setup and configuration
- `raw_images/` - Sample captured raw images with different exposure times (available locally, not in Git)
  - Contains raw image files (*.raw) and histogram analysis results (*.png)
  - Note: These files are excluded from Git via .gitignore due to their large size
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

### Main Application (Recommended)

You can run the application in either the original all-in-one version or the new modularized version. Make sure you're in the project root directory when running any of these commands.

#### Option 1: Original All-in-One Implementation

```bash
python -m laser_speckle_UI.updated_widget
```

#### Option 2: New Modularized Implementation (Recommended)

```bash
python -m laser_speckle_UI.main
```

Both implementations provide identical functionality, but the modularized version is more maintainable and easier to extend.

**Important Note:** The modularized implementation uses relative imports, so you must run it as a module with the `-m` flag as shown above, from the project root directory.

**Alternative method:** If you prefer to run the script directly, you can add the project root to your Python path:

```bash
# From the project root directory
export PYTHONPATH=$PYTHONPATH:$(pwd)  # On Windows: set PYTHONPATH=%PYTHONPATH%;%CD%
python laser_speckle_UI/main.py
```

**Note:** When using either version, you don't need to separately run the simple UI or upload Arduino code - the application handles all communication with both the camera and Arduino.

### Alternative: Simple Laser Control UI

The simple UI is an alternative, minimal interface just for controlling laser intensity. Only use this if you're not using the main application:

```bash
python user_controlled_UI/UI.py
```

For this simple UI to work, you must first upload the `user_controlled_UI.ino` sketch to your Arduino.

### Camera Setup/Testing

To test the camera setup and capture raw images:

```bash
python camera/camera_setup.py
```

## Troubleshooting Import Issues

If you encounter import errors when running the modularized application, try these solutions:

1. Always run the application as a module from the project root with the `-m` flag:
   ```bash
   python -m laser_speckle_UI.main
   ```

2. Set the Python path to include the project root:
   ```bash
   export PYTHONPATH=$PYTHONPATH:$(pwd)  # On macOS/Linux
   set PYTHONPATH=%PYTHONPATH%;%CD%      # On Windows
   ```

3. Create a `.pth` file in your virtual environment's site-packages directory with the path to your project.

## Debugging Guide

### Serial Connection Issues
- Check the Arduino connection port (common ports are `/dev/cu.usbmodem*` on macOS, `/dev/ttyACM*` on Linux, and `COM*` on Windows)
- The code includes a retry mechanism to establish serial connection

### Camera Connection Issues
- Ensure Basler Pylon SDK is properly installed
- Check if the camera is detected using Basler's Pylon Viewer application
- Verify permissions for camera access

### UI Display Issues
- The UI files are designed for PySide6. Ensure you have the correct version installed
- Form paths may need to be adjusted based on your installation location

## Data Analysis Tools

The project includes several standalone analysis scripts that can be run from the project root:

- `contrast_analyzer.py` - Analyzes contrast in speckle patterns
  ```bash
  python contrast_analyzer.py --image raw_images/your_image.raw --width 960 --height 1200
  ```

- `histogram_saturation_analyzer.py` - Analyzes image saturation
  ```bash
  python histogram_saturation_analyzer.py --image raw_images/your_image.raw
  ```
  