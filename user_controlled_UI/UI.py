import sys
import serial
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer
import matplotlib.pyplot as plt


class MyApp(QWidget):
    def __init__(self):
        super().__init__()

        # Load the UI from the .ui file created in Qt Designer
        loader = QUiLoader()
        file = QFile("/Users/bilalshihab/dev/laser_speckle_project/laser_speckle_UI/form.ui")
        file.open(QFile.ReadOnly)
        self.ui = loader.load(file, self)
        file.close()

        # Setup serial communication for Arduino
        self.serial = self.setup_serial_connection()

        # Connect UI elements to functions
        self.ui.horizontalSlider.setRange(0, 4095)  # Set slider for 12-bit range
        self.ui.horizontalSlider.valueChanged.connect(self.update_contrast)
        self.ui.stop_button.clicked.connect(self.stop_and_plot)  # Connect "Stop" button

        # Data storage for plotting
        self.voltages = []
        self.currents = []

        # Start a timer to continuously collect feedback from Arduino
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.collect_data_and_update_ui)
        self.timer.start(50)  # Call every 100 ms

    def setup_serial_connection(self):
        # Serial connection retry mechanism
        for attempt in range(3):  # Retry up to 3 times
            try:
                ser = serial.Serial('/dev/cu.usbmodem101', 9600, timeout=1)
                print("Serial connection established.")
                return ser
            except serial.SerialException as e:
                print(f"Attempt {attempt + 1} failed. Error connecting to serial port: {e}")
        print("Failed to establish a connection after 3 attempts.")
        return None

    def update_contrast(self):
        contrast_value = self.ui.horizontalSlider.value()//2
        print("Contrast value is: ", contrast_value)
        flag = 0x01  # Flag to indicate data change
        present_current = 2048  # Example 12-bit placeholder for present current
        present_current_high = (present_current >> 8) & 0xFF  # High byte of present current
        present_current_low = present_current & 0xFF          # Low byte of present current
        target_current_high = (contrast_value >> 8) & 0xFF  # High byte of 12-bit value
        target_current_low = contrast_value & 0xFF          # Low byte of 12-bit value
        temperature = 25  # Placeholder for temperature
        checksum = (flag % 10 + present_current_high % 10 + present_current_low % 10 +
                    target_current_high % 10 + target_current_low % 10 + temperature % 10) % 10

        # Construct and send packet
        packet = bytes([0xFF, flag, present_current_high, present_current_low,
                        target_current_high, target_current_low, temperature, checksum, 0xFE])
        if self.serial is not None:
            try:
                self.serial.write(packet)
                print(f"Sent contrast value: {contrast_value} to Arduino")
            except serial.SerialTimeoutException as e:
                print(f"Timeout error when sending data: {e}")
            except Exception as e:
                print(f"Error writing to serial port: {e}")

    def collect_data_and_update_ui(self):
        if self.serial is not None and self.serial.in_waiting > 0:  # Check if there's data in the buffer
            try:
                while self.serial.in_waiting > 0:
                    byte = self.serial.read(1)[0]
                    if byte == 0xFF:  # Start byte detected
                        if self.serial.in_waiting >= 8:
                            data = self.serial.read(8)
                            data = b'\xFF' + data

                            if data[0] == 0xFF and data[-1] == 0xFE:
                                flag = data[1]
                                present_current_high = data[2]
                                present_current_low = data[3]
                                target_current_high = data[4]
                                target_current_low = data[5]
                                temp = data[6]
                                checksum = data[7]

                                present_current = (present_current_high << 8) | present_current_low
                                target_current = (target_current_high << 8) | target_current_low
                                calculated_checksum = (flag % 10 + present_current_high % 10 +
                                                       present_current_low % 10 + target_current_high % 10 +
                                                       target_current_low % 10 + temp % 10) % 10
                                if calculated_checksum == checksum:
                                    voltage = (target_current / 4095.0) * 5.0  # Convert to voltage
                                    self.voltages.append(voltage)
                                    self.currents.append(present_current)
                                    self.update_ui(present_current, temp, voltage)
                                else:
                                    print("Checksum mismatch in received packet.")
                        break
            except Exception as e:
                print(f"Error reading from serial port: {e}")

    def update_ui(self, current, temp, voltage):
        self.ui.label.setText(f"Current: {current}")
        self.ui.label_2.setText(f"T: {temp}°C")
        print(f"Received feedback: Current {current}, Temp {temp}°C, Voltage {voltage:.2f}V")

    def stop_and_plot(self):
        # Stop data collection
        self.timer.stop()
        print("Data collection stopped. Plotting the graph...")

        # Plot the graph
        if self.voltages and self.currents:
            plt.figure()
            plt.plot(self.voltages, self.currents, 'r-')
            plt.xlabel("Voltage (V)")
            plt.ylabel("Current (Digital Value)")
            plt.title("Current vs Voltage")
            plt.grid()
            plt.show()
        else:
            print("No data collected to plot. Please try again.")

        # Clear data for the next session
        self.voltages.clear()
        self.currents.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
