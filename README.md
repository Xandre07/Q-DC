# Q-DC: An Arduino Uno Q-based driving companion

An integrated driver-assistance logic layer and real-time telemetry HUD built for the Arduino Uno Q hardware. Q-DC merges multi-bus telemetry, real-time inertial sensing, and state-machine-driven safety warnings to deliver actionable driver feedback on a high-contrast display.

## Overview

The Q-DC (Driving Companion) monitors vehicle motion parameters and environmental flags in real time. Running on the Zephyr core of the Arduino Uno Q architecture, the system reads dynamic X/Y-axis acceleration vectors alongside speed metrics routed from a Linux host bridge. When dangerous driving patterns, such as hard braking, excessive acceleration or swerving are detected, Q-DC overrides standard telemetry displays to render clear, prioritized driver safety tips. Beyond warning states, the device serves as a central dash HUD displaying vehicle speed, speed limits, lane departure warnings (LDW), and system time.

## Key Features

- IMU-Driven Safety Logic: Real-time evaluation of longitudinal (+X / -X) and lateral (|Y|) acceleration thresholds using FastIMU.
- Linux RPC Integration: Inter-process communication via Arduino_RouterBridge streaming speed, lane departure warning (LDW) graphics, and speed limit data.
- Dynamic Graphical HUD: Rendered using [u8g2](https://github.com/olikraus/u8g2) on a 128x64 SH1106 OLED, featuring visual lane-marking indicators, speed limit signs, and dynamic clock display.
- Absolute Peripheral Abstraction: Leverages u8g2 and [FastIMU](https://github.com/LiquidCGS/FastIMU) abstractions, allowing seamless swapping of underlying display hardware (e.g., SSD1306, SH1106, ST7565) and IMU chipsets (e.g., BMI160, MPU6050, ICM20689) without rewriting application logic.

## Hardware used

- [Arduino Uno Q 4GB](https://store.arduino.cc/products/uno-q-4gb?srsltid=AfmBOorqBfFNVFOgjOrmVuKIDB0OPeVvKVLLb1IpTboHPuIZCUn8YswK)
- [DFRobot BMI160 IMU](https://www.dfrobot.com/product-1716.html?srsltid=AfmBOora2AfnW4iJCpC4KNgwnL2ZakSLMWDbT5YI4_OkGGsTdMXFVWO5)
- Generic SH1106 OLED Display

## License
Distributed under the MIT License. See LICENSE for details.
