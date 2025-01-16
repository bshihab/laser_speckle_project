# laser_speckle_project

This project implements a user interface (UI) for controlling and adjusting the contrast of a laser speckle pattern. It consists of a Python-based UI built with PySide6 and an Arduino program for hardware control.

## Overview

The system allows users to adjust the contrast of a laser speckle pattern through a graphical slider in the UI. The Python application communicates with an Arduino microcontroller, which in turn controls a digital-to-analog converter (DAC) to adjust the intensity of a laser. The UI also displays feedback from the Arduino, including the current laser intensity and temperature.

## Features

-   **Graphical UI**: A slider for adjusting the laser speckle contrast.
-   **Real-time Feedback**: Displays the current laser intensity and temperature.
-   **Serial Communication**: Utilizes serial communication to send control signals to the Arduino and receive feedback.
-   **Data Plotting**: Plots the relationship between the applied voltage and the resulting current in real-time.
-   **Error Handling**: Includes a retry mechanism for establishing serial communication and checksum verification for data integrity.

## Components

### Python Application (`UI.py`)

-   **UI Design**: Uses a `.ui` file created with Qt Designer for the graphical interface.
-   **Serial Communication**: Sets up and manages serial communication with the Arduino.
-   **Data Handling**: Sends control signals to the Arduino based on user input and processes feedback data.
-   **Plotting**: Uses `matplotlib` to plot the current vs. voltage data.

### Arduino Program (`user_controlled_UI.ino`)

-   **DAC Control**: Controls the laser intensity via a DAC connected to pin `A0`.
-   **Serial Communication**: Receives control signals from the Python application and sends back periodic feedback.
-   **Checksum Verification**: Ensures the integrity of received data using a checksum.
-   **Periodic Feedback**: Sends the current laser intensity and temperature to the Python application at regular intervals.

## Setup

### Prerequisites

-   Python 3.x
-   PySide6
-   `matplotlib`
-   `pyserial`
-   Arduino IDE
-   Arduino board (e.g., Arduino Uno)

### Installation

1. **Python Dependencies**: Install the required Python packages:

    ```bash
    pip install PySide6 matplotlib pyserial
    ```

2. **Arduino Setup**:
    -   Connect the Arduino board to your computer.
    -   Open the `user_controlled_UI.ino` file in the Arduino IDE.
    -   Upload the program to the Arduino board.

3. **Hardware Connections**:
    -   Connect the DAC output pin (`A0` on the Arduino) to the laser control circuit.

### Running the Application

1. Ensure the Arduino is connected and the correct serial port is specified in `UI.py`.
2. Run the Python application:

    ```bash
    python UI.py
    ```

3. Use the slider in the UI to adjust the laser speckle contrast. The feedback data will be displayed in the UI, and the plot will update in real-time.

## Usage

-   **Adjust Contrast**: Move the slider in the UI to change the laser speckle contrast.
-   **Stop and Plot**: Click the "Stop" button to stop data collection and display the plot of current vs. voltage.
-   **Monitor Feedback**: Observe the real-time feedback from the Arduino in the UI labels.