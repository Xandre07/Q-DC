#include <Arduino_RouterBridge.h>
#include <Arduino.h>
#include <U8g2lib.h>
#include "FastIMU.h"
#include <Wire.h>

static const unsigned char image_speed_16dp_000000_FILL0_wght200_GRAD0_opsz48_bits[] U8X8_PROGMEM = {
  0x00,0x00,0x00,0x00,0x60,0x00,0x08,0x01,0x04,0x03,0xc0,0x00,0x62,0x04,0x62,0x04,
  0x00,0x00,0xfc,0x03,0x00,0x00,0x00,0x00
};

// Full Frame Buffer constructor for SH1106 OLED over HW I2C
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);

#define BMI160_ADDR 0x69 

// 1. Bind FastIMU to Wire2 (I2C3 on D18/D19)
BMI160 IMU(Wire2); 

calData calib = { 0 };
AccelData accelData;
GyroData gyroData;

#define buzzer 11

// Global telemetry variables
int currentSpeed = 0;
int currentHour = 12;
int currentMin = 0;
int speedLim = 100;
int ldw = -1;
int tip = 0;

// G-Force Thresholds (1.0G = 1g resting gravity)
const float ACCEL_MODERATE_THRES = 1.4;  // Moderate Throttle (+X)
const float ACCEL_HARD_THRES     = 2.2;  // Hard Throttle (+X)

const float BRAKE_MODERATE_THRES = -1.4; // Moderate Braking (-X)
const float BRAKE_HARD_THRES     = -2.2; // Hard Braking (-X)

const float STEER_HARD_THRES     = 1.6;  // Hard Steering (|Y|)

// Latch Duration: How long warnings stay visible (3000ms = 3 seconds)
const unsigned long LATCH_DURATION_MS = 3000;
int currentLatchedCode = 0;
unsigned long lastTriggerTime = 0;

void drawScreen(int speed, int hour, int min, int speedLim, int ldw, int tip) {
  u8g2.setFontMode(1);
  u8g2.setBitmapMode(1);

  // Left lane markings
  u8g2.drawLine(87, 23, 80, 54);
  u8g2.drawLine(90, 23, 83, 54);

  // Right lane markings
  u8g2.drawLine(115, 23, 122, 54);
  u8g2.drawLine(118, 23, 125, 54);

  switch(ldw){
    case 0:
      u8g2.drawLine(88, 23, 81, 54);
      u8g2.drawLine(89, 23, 82, 54);
      u8g2.drawLine(116, 23, 123, 54);
      u8g2.drawLine(117, 23, 124, 54);
      break;
    case 1:
      u8g2.drawLine(116, 23, 123, 54);
      u8g2.drawLine(117, 23, 124, 54);
      break;
    case 2:
      u8g2.drawLine(88, 23, 81, 54);
      u8g2.drawLine(89, 23, 82, 54);
      break;
    case -1:
      // Disabled LDW: Do nothing
    default:
      break;
  }

  // UI Separators
  u8g2.drawLine(77, 14, 0, 14);
  u8g2.drawLine(77, 64, 77, 0);

  // Speedometer Icon
  u8g2.drawXBMP(4, 1, 12, 12, image_speed_16dp_000000_FILL0_wght200_GRAD0_opsz48_bits);

  // Dynamic Speed Value
  u8g2.setFont(u8g2_font_helvB08_tr);
  u8g2.setCursor(18, 11);
  u8g2.print(speed);

  // Dynamic Clock Value (HH:MM)
  char timeBuf[6];
  snprintf(timeBuf, sizeof(timeBuf), "%02d:%02d", hour, min);
  u8g2.setFont(u8g2_font_haxrcorp4089_tr);
  u8g2.drawStr(51, 10, timeBuf);

  if (tip != 0) {
    u8g2.setFont(u8g2_font_t0_14b_tr);
    char limBuf[4];
    switch (tip) {
      case 1:
        u8g2.drawStr(2, 30, "Speed");
        u8g2.drawStr(2, 45, "check");
        u8g2.drawStr(2, 59, "ahead");

        // Speed Limit Sign
        u8g2.drawEllipse(58, 40, 12, 12);
        snprintf(limBuf, sizeof(limBuf), "%d", speedLim);
        u8g2.setFont(u8g2_font_profont12_tr);
        u8g2.drawStr(58 - (u8g2.getStrWidth(limBuf) / 2), 44, limBuf);
        break;
      case 2:
        u8g2.drawStr(2, 30, "Watch");
        u8g2.drawStr(2, 43, "your");
        u8g2.drawStr(2, 57, "speed");

        // Speed Limit Sign
        u8g2.drawEllipse(58, 40, 12, 12);
        snprintf(limBuf, sizeof(limBuf), "%d", speedLim);
        u8g2.setFont(u8g2_font_profont12_tr);
        u8g2.drawStr(58 - (u8g2.getStrWidth(limBuf) / 2), 44, limBuf);
        break;
      case 3:
        u8g2.drawStr(2, 37, "Reduce");
        u8g2.drawStr(2, 52, "Throttle");
        break;
      case 4:
        u8g2.drawStr(2, 30, "Brake");
        u8g2.drawStr(2, 42, "with");
        u8g2.drawStr(2, 54, "Moderation");
        break;
      case 5:
        u8g2.drawStr(2, 37, "Plan your");
        u8g2.drawStr(2, 52, "stops");
        break;
      case 6:
        u8g2.drawStr(2, 30, "Smooth");
        u8g2.drawStr(2, 42, "your");
        u8g2.drawStr(2, 54, "steering");
        break;
      default:
        break; 
    }
  } else {
    if (speedLim > 0) {
      u8g2.drawEllipse(38, 39, 24, 23);
      u8g2.drawEllipse(38, 39, 23, 22);  
  
      char limitStr[8];
      snprintf(limitStr, sizeof(limitStr), "%d", speedLim);
  
      u8g2.setFont(u8g2_font_profont22_tr);
      u8g2.drawStr(38 - (u8g2.getStrWidth(limitStr) / 2), 46, limitStr);
    }
  }
}

// Track the timestamp of the last hard brake event
unsigned long lastHardBrakeTime = 0;
const unsigned long HARD_BRAKE_STOP_BUFFER_MS = 3000; // 3-second buffer

int processTip(int speed, int limit) {
  // 1. Map API / Vision Events
  if (false) {
    // NOT IMPLEMENTED
    return 1; // "Speed check ahead"
  }

  // 2. Speed Limit Checks
  if (speed > limit + 5) {
    return 2; // "Watch your speed"
  }

  // 3. Read IMU
  IMU.update();
  IMU.getAccel(&accelData);

  unsigned long now = millis();

  // 4. Record timestamp if a hard brake is detected
  if (accelData.accelX <= BRAKE_HARD_THRES) {
    lastHardBrakeTime = now;
    return 4; // "Brake with Moderation" (Immediate hard braking alert)
  }

  // 5. Hard Brake + Standstill Buffer Check
  // Triggered if current speed is 0 AND a hard brake happened in the last 3 seconds
  if (speed == 0 && (now - lastHardBrakeTime <= HARD_BRAKE_STOP_BUFFER_MS) && lastHardBrakeTime > 0) {
    return 5; // "Plan your stops"
  }

  // 6. Longitudinal (+X) & Lateral (|Y|) Dynamic Triggers
  if (accelData.accelX >= ACCEL_HARD_THRES) {
    return 3; // "Reduce Throttle"
  }

  if (abs(accelData.accelY) >= STEER_HARD_THRES) {
    return 6; // "Smooth your steering"
  }

  return 0; // All parameters normal
}

// Map warning state urgency to numerical priority
int getPriority(int code) {
  switch (code) {
    case 4: return 6; // Hard Braking (Highest urgency)
    case 3: return 5; // Hard Acceleration
    case 6: return 4; // Hard Steering
    case 1: return 3; // Speed Check Ahead
    case 2: return 2; // Watch Your Speed
    case 5: return 1; // Plan Your Stops (Advisory)
    default: return 0;
  }
}

// Priority-aware timer holding state
int getLatchedTip(int speed, int limit) {
  int rawCode = processTip(speed, limit);
  unsigned long now = millis();

  int newPriority = getPriority(rawCode);
  int currentPriority = getPriority(currentLatchedCode);

  // Timer expired: accept next state
  if (now - lastTriggerTime > LATCH_DURATION_MS) {
    currentLatchedCode = rawCode;
    if (rawCode != 0) lastTriggerTime = now;
  }
  // Active window: override only if new warning has higher or equal priority
  else if (rawCode != 0 && newPriority >= currentPriority) {
    currentLatchedCode = rawCode;
    lastTriggerTime = now;
  }

  return currentLatchedCode;
}

// Handler bound to Linux Python Bridge
void updateDisplay(int speed, int limit, int ldw, int hour, int min) {
  currentSpeed = speed;
  speedLim = limit;

  // Process latched warning
  tip = getLatchedTip(speed, limit);
  
  u8g2.clearBuffer();
  drawScreen(currentSpeed, hour, min, speedLim, ldw, tip);
  u8g2.sendBuffer();
}

void setup() {
  // Initialize RPC Bridge
  Bridge.begin();
  Bridge.provide("updateDisplay", updateDisplay);
  
  // Initialize Graphical Engine
  u8g2.begin();
  u8g2.enableUTF8Print();

  // Initialize IMU on Wire2
  Wire2.begin(); 
  int err = IMU.init(calib, BMI160_ADDR);
  if (err != 0) {
    Monitor.print("IMU init failed with code: ");
    Monitor.println(err);
    
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_helvB08_tr);
    u8g2.setCursor(10, 32);
    u8g2.print("IMU INIT ERROR!");
    u8g2.sendBuffer();
    while (1);
  }

  Monitor.println("BMI160 online via FastIMU!");

  // Display boot splash screen
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_helvB08_tr);
  u8g2.setCursor(18, 25);
  u8g2.print("Q-DC v1.0");
  u8g2.setCursor(30, 45);
  u8g2.print("SYSTEM READY");
  u8g2.sendBuffer();
  delay(1000);
}

void loop() {
  Bridge.update();
}