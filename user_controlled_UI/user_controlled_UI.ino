#include <Arduino.h>

byte startByte = 0xFF;
byte endByte = 0xFE;
int presentCurrent = 2048; // 12-bit current value (example placeholder)
int targetCurrent = 0;    // Target current received from Python (12-bit value)
byte temperature = 25;    // Placeholder for temperature

const int dacPin = A0; // Pin to control the lightbulb via DAC
const float MAX_VOLTAGE = 2.5;
unsigned long lastFeedbackTime = 0; // Track the last time feedback was sent
const unsigned long feedbackInterval = 50; // Interval in milliseconds for periodic feedback

void setup() {
    Serial.begin(9600);
    Serial.println("Arduino ready for contrast control");

    // Set the DAC resolution to 12 bits (0-4095)
    analogWriteResolution(12);
}

void loop() {
    // Check if a full packet is available
    while (Serial.available() >= 9) {
        if (Serial.read() == startByte) {
            byte data[8];
            Serial.readBytes(data, 8);  // Read the remaining 8 bytes
            byte flag = data[0];
            byte presentCurrentHigh = data[1];
            byte presentCurrentLow = data[2];
            byte targetCurrentHigh = data[3];
            byte targetCurrentLow = data[4];
            byte receivedTemperature = data[5];
            byte checksum = data[6];
            byte receivedEndByte = data[7];

            if (receivedEndByte == endByte &&
                verifyChecksum(flag, presentCurrentHigh, presentCurrentLow, targetCurrentHigh, targetCurrentLow, receivedTemperature, checksum)) {
                targetCurrent = (targetCurrentHigh << 8) | targetCurrentLow;
                setContrast(targetCurrent);
            }
        }
    }

    // Periodically send feedback
    if (millis() - lastFeedbackTime >= feedbackInterval) {
        sendFeedback();
        lastFeedbackTime = millis();
    }
}

bool verifyChecksum(byte flag, byte presentHigh, byte presentLow, byte targetHigh, byte targetLow, byte temp, byte checksum) {
    byte calculatedChecksum = (flag % 10 + presentHigh % 10 + presentLow % 10 + targetHigh % 10 + targetLow % 10 + temp % 10) % 10;
    return calculatedChecksum == checksum;
}

void setContrast(int target) {
    // Scale target to voltage range
    float scaledVoltage = target;//(target / 4095.0) * MAX_VOLTAGE;
    
    // Output the scaled voltage
    analogWrite(dacPin, target);
    presentCurrent = target; // Update the current to reflect the new target

    Serial.print("DAC output value: ");
    Serial.println(target);
    Serial.print("Target Voltage (V): ");
    Serial.println(scaledVoltage, 2);
}

void sendFeedback() {
    byte presentCurrentHigh = (presentCurrent >> 8) & 0xFF;
    byte presentCurrentLow = presentCurrent & 0xFF;
    byte targetCurrentHigh = (targetCurrent >> 8) & 0xFF;
    byte targetCurrentLow = targetCurrent & 0xFF;
    byte checksum = (0x01 % 10 + presentCurrentHigh % 10 + presentCurrentLow % 10 +
                     targetCurrentHigh % 10 + targetCurrentLow % 10 + temperature % 10) % 10;

    Serial.write(startByte);
    Serial.write(0x01);               // Flag
    Serial.write(presentCurrentHigh); // High byte of present current
    Serial.write(presentCurrentLow);  // Low byte of present current
    Serial.write(targetCurrentHigh);  // High byte of target current
    Serial.write(targetCurrentLow);   // Low byte of target current
    Serial.write(temperature);        // Placeholder for temperature
    Serial.write(checksum);
    Serial.write(endByte);
}
