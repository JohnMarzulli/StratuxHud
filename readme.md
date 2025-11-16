# STRATUX HUD

## 1 Table of Contents

[[TOC]]

## 2 Introduction

This project aims to bring an affordable heads up display system into ANY cockpit.

The focus is to improve traffic awareness and to reduce the amount of time pilots reference tablets or an EFB.

**NOTE:** This project relies on having a [Stratux](http://stratux.me/) build with AHRS and GPS. A suitable build can be done for less than \$150 (USD).

There are two versions that can be built:

### 2.1 Configurations

There are two main ways to configure the StratuxHud.

The first is as a stand-alone unit. For the standalone configuration, the HUD code runs on its own Raspberry Pi.

The second is in an "All-In-One" (AIO) configuration. With an AIO setup, the HUD code runs on the Stratux.

| Feature                    | Stand Alone | AIO          |
|----------------------------|-------------|--------------|
| Keypad Control             | Yes         | No           |
| Dynon D180 Support         | Yes         | No           |
| Aithre CO Monitor          | Yes         | Experimental |
| Illyrian SPO/Pulse Monitor | Yes         | Experimental |
| Raspberry Pi 3b+           | Yes         | No           |
| Raspberry Pi 4             | Yes         | No           |

### 2.2 Recommended Projector

Projector availability is subject to change, and compatability is subject to your choice of Pi.

My reccomendation is a R-Pi 4 with a Hudly Wireless OR with the [StratuxHudDisplay](https://github.com/JohnMarzulli/StratuxHudDisplay)

![HUDLY Version](media/hudly-in-flight.jpg)

While the HUDway Drive looked promising, getting video signal into it was a failure.

**NOTE:** This project initially used and recommended the "HUDLY Classic" projector which is no longer available.

### 2.3 Recommended Stratux Configuration

To get the most out of the StratuxHud, the following configuration for the Stratux is suggested:

- V3 receiver for 978 (UAT)
- V2 receiver for 1090
- Stratux GPYes u-blox 7

Picking the correct GPS solution for your HUD can be difficult.

The Vk-162, while less tidy due to the cable, has FAR superior GPS reception.
GPS reception with the GP-Yes unit can be a problem.

I have two two Vk-162 units fail. With each failure the AHRS reports from the Stratux have been VERY slow.

This behavior has not been observed with a GPYes unit.

If you are running the HUD as a standalone unit AND using the optional Dynon interface, then this is not a problem.

For the StratuxHud to work correctly, you MUST have the AHRS chip and a GPS solution installed on the Stratux

**NOTE:** To have full functionality with a Stratux based unit, please use Stratux Version 1.6r1 or higher.

### 2.4 Dynon Integration

New with v1.7 is integration with Dynon D10/D100 Series Products.

This is achieved using the serial output.

At this time, integration with a Dynon D180 has only been tested.

The DynonToHud service is included with the Stand Alone image of the StratuxHud.

While the DynonToHud service does decode and make available both the EFIS and EMS data, at this time only the EFIS/AHRS data is presented by any of the HUD views.

For more information on the setup, and installation of the DynonToHud service, please visit the project page.

[DynonToHud](<https://github.com/JohnMarzulli/DynonToHud>)

## 3 In-Flight Controls

You may use a number pad as an input device. I used velcro to secure the number pad to my dashboard.

| Key         | Action                                                                       |
|-------------|------------------------------------------------------------------------------|
| Backspace   | Tell the Stratux that you are in a level position. Resets the AHRS to level. |
| +           | Next view                                                                    |
| Right Arrow | Next view                                                                    |
| -           | Previous view                                                                |
| Left Arrow  | Previous view                                                                |
| =           | Toggle rendering debug information                                           |
| Esc         | Send shutdown commands to both the HUD controller **and** the Stratux        |
| q           | (_Full keyboard only_) Quit to the command line.                             |
| 0/Ins       | Force a connection reset between the HUD and the Stratux                     |
| Up Arrow    | Zoom Out, or Previous Page (not all displays)                                |
| Down Arrow  | Zoom In, or next Page (not all displays)                                     |

## 4 Included (Default) Views

### 4.1 AHRS Only

![AHRS Only View](media/ahrs_with_dynon_view.png)

Displays attitude information including pitch, roll, and heading without traffic information.

**Information Displayed:**

- Artificial horizon with pitch and roll
- Heading indicator
- Altitude
- Ground speed and ground track
- G-force indicator
- Optional: Aithre CO detector readings
- Optional: Dynon AHRS data if available

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view
- Backspace to reset AHRS to level

---

### 4.2 AHRS + ADS-B

![AHRS + ADS-B View](media/ahrs_ads-b.jpg)

Primary view combining attitude information with real-time traffic targeting. Shows artificial horizon and targeting bugs for nearby aircraft.

**Information Displayed:**

- Artificial horizon with pitch and roll
- Heading indicator
- Altitude and indicated/ground speed
- Traffic targeting bugs showing relative position and distance
- Information cards with aircraft details
- G-force indicator
- Optional: Dynon EFIS data (IAS, G-force, heading from Dynon)

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view
- Backspace to reset AHRS to level

_Note: This is the default view on startup._

---

### 4.3 Traffic Scope

![Traffic Scope View](media/radar.jpg)
![Traffic Scope View](media/radar-in-flight.jpg)

Top-down radar scope display showing traffic targets relative to your current heading and position.

**Information Displayed:**

- Heading strip at top
- Scope with target bugs at relative positions
- Targeting reticles for nearby aircraft
- Distance and bearing information for visible targets
- Altitude information for traffic

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view
- Use Up/Down arrows to zoom in/out on scope

---

### 4.4 Weather Scope

![Weather Scope View](media/NEXRAD.jpg)

Weather radar display showing NEXRAD reflectivity and precipitation patterns in your area.

**Information Displayed:**

- Reflectivity radar data
- Weather targets and storm cells
- Relative distance and bearing
- Weather intensity indicators

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view
- Use Up/Down arrows to zoom in/out on weather map

---

### 4.5 Airport Frequencies

![Airport Frequencies View](media/freqs.jpg)

Lists nearby airport information including ATIS, UNICOM, ground, tower, and other relevant frequencies.

**Information Displayed:**

- Nearest airports
- Distance to each airport
- Available frequencies (ATIS, UNICOM, Ground, Tower, Approach, Departure)
- Runway information

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view
- Use Up/Down arrows to navigate through airport list (if multiple pages)

---

### 4.6 METARS (Experimental, Off By Default)

![METARS View](media/metar.jpg)

Displays METAR data for nearby airports including weather conditions, wind, visibility, and temperature.

**Information Displayed:**

- Raw METAR reports
- Decoded weather information
- Wind speed and direction
- Visibility
- Temperature and dewpoint
- Flight category indicators

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view
- Use Up/Down arrows to navigate through METAR list (if multiple pages)

---

### 4.7 TAFS (Experimental, Off By Default)

![TAFS View](media/tafs_view.png)

Terminal Aerodrome Forecasts (TAF) for nearby airports showing predicted weather conditions.

**Information Displayed:**

- TAF reports for nearby airports
- Forecast weather conditions
- Wind forecasts
- Visibility forecasts
- Change indicators (BECMG, TEMPO)

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view
- Use Up/Down arrows to navigate through TAF list (if multiple pages)

---

### 4.8 AIRMETS (Experimental, Off By Default)

![AIRMETS View](media/airmets_view.png)

Airmen's Meteorological Information showing significant weather in your flight information region.

**Information Displayed:**

- AIRMET reports
- Affected areas
- Weather phenomena (turbulence, icing, low visibility, etc.)
- Valid time periods
- Hazard type and intensity

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view
- Use Up/Down arrows to navigate through AIRMET list

---

### 4.9 Traffic

![Traffic View](media/traffic.jpg)

Detailed traffic information display with aircraft cards showing identification, distance, bearing, and altitude.

**Information Displayed:**

- Heading strip at top
- Target bugs and targeting reticles
- Information cards with:
  - Aircraft identifier (tail number or ICAO code)
  - Distance (statute miles)
  - Bearing (relative to current heading)
  - Altitude (relative to your altitude)
- Traffic icon indicators

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view

_Note: Bearing is calculated from aircraft heading, NOT ground track._

---

### 4.10 Traffic List

![Traffic List View](media/traffic-list.jpg)

Tabular list of nearest aircraft showing up to eight closest targets with key information.

**Information Displayed:**

- IDENT (tail number, ICAO, or callsign)
- BEAR (bearing to target)
- DIST (distance in statute miles)
- ALT (relative altitude with two digits dropped)
- Aircraft type and squawk code (when available)

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view
- Use Up/Down arrows to navigate through traffic list (if multiple pages)

---

### 4.11 Time

![Time View](media/time_view.png)

Displays current Zulu (UTC) time prominently. Useful for logging and flight planning.

**Information Displayed:**

- Current UTC time
- Optional: Local time
- Date information

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view

---

### 4.12 Aithre

![Aithre View](media/aithre_view.png)

Carbon monoxide detector readings and status from paired Aithre CO monitor.

**Information Displayed:**

- CO PPM (parts per million) level
- Alert status
- Signal strength
- Battery status
- Historical trend data

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view

_Note: Requires Aithre device paired via Bluetooth. Only works on Raspberry Pi units with Bluetooth capability (Pi 3, 3B+, 4)._

---

### 4.13 Diagnostics

![Diagnostics View](media/diagnostics_view.png)

System diagnostics and status information for troubleshooting HUD connectivity and health.

**Information Displayed:**

- HUD CPU temperature (Celsius)
- Connection status to Stratux
- Traffic Manager service status
- Aithre/Illyrian sensor status (if connected)
- IP address of HUD
- OWNSHIP configuration
- GPS status

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view

_Note: This view is critical for resolving connectivity issues. If "TRAFFIC UNAVAILABLE" appears, the Traffic Manager address shown here is needed for diagnosis._

---

### 4.14 Intentionally Blank

A blank screen with no information displayed. Useful for reducing power consumption or when you want a clear view without HUD overlay.

**Information Displayed:**

- None

**Interactions:**

- Use `+` or Right Arrow to cycle to next view
- Use `-` or Left Arrow to cycle to previous view

## 5 Parts List

### 5.1 All Builds

_NOTE:_ This _does not_ include a power source. You will need to supply ship power from a 5V USB port or from a battery. _NOTE:_ This is for a build that uses a separate Raspberry Pi to drive the display. If you wish to have an "All-In-One" solution where the HUD software runs on the Stratux, you will not need an additional Pi.

- [Aviator Systems Display](https://shop.aviatorsys.com/product/stratux-hud/) Choose "HUD Standalone"
- [_OPTIONAL_ 3/4" Wire Braiding](https://www.amazon.com/gp/product/B073YL3HMC/ref=ppx_yo_dt_b_asin_title_o00_s01?ie=UTF8&psc=1)

### 5.2 Recommended Stand Alone Build

- [Raspberry Pi 3B+](https://www.amazon.com/ELEMENT-Element14-Raspberry-Pi-Motherboard/dp/B07P4LSDYV/ref=sr_1_6?dchild=1&keywords=raspberry+pi+3B%2B&qid=1586751198&sr=8-6)
- [Case For Raspberry Pi](https://www.amazon.com/iPhoenix-Raspberry-White-Compatible-Model/dp/B06XQSXZ97/ref=sr_1_3?s=electronics&dd=iYEspjjyeRXfqDW9BHwJFw%2C%2C&ddc_refnmnt=pfod&ie=UTF8&qid=1529215794&sr=1-3&keywords=white+raspberry+pi+3+case&refinements=p_97%3A11292772011)
- [Cooling Fan for Raspberry Pi](https://www.amazon.com/gp/product/B075R4S9GH/ref=od_aui_detailpages00?ie=UTF8&psc=1)
- [Micro USB Cable](https://www.amazon.com/AmazonBasics-Male-Micro-Cable-Black/dp/B0711PVX6Z/ref=sr_1_6?s=electronics&ie=UTF8&qid=1529215888&sr=1-6&keywords=micro+usb+cable)
- [Micro SD Card](https://www.amazon.com/SanDisk-Ultra-Micro-Adapter-SDSQUNC-016G-GN6MA/dp/B010Q57SEE/ref=sr_1_10?s=pc&ie=UTF8&qid=1529215944&sr=1-10&keywords=micro+sd+card)
- [Rottay Mechanical Keypad](https://www.amazon.com/Number-Rottay-Mechanical-Numeric-backlit/dp/B076FTSY6J/ref=sr_1_3?ie=UTF8&qid=1529215627&sr=8-3&keywords=mechanical+keypad)

## 6 Recommended Software Install

Please use one of the provided images from the "Release" page on GitHub.

1. Download the image for your scenario from the GitHub [Releases Page](<https://github.com/JohnMarzulli/StratuxHud/releases>)
2. Use [Etcher](<https://www.balena.io/etcher/>) to flash the image onto a Micro SD card.
3. Plug in your Projector to the Raspberry Pi
4. It is recommended that you SSH into the HUD and use `raspi-config` to ["expand the filesystem"](<https://geek-university.com/raspberry-pi/expand-raspbian-filesystem/>).

## 7 Development/From Scratch Install instructions

### 7.1 First Boot

1. Flash the latest [Raspbian](https://www.raspberrypi.org/downloads/raspbian/) to an SD card
2. Plug in a keyboard and a monitor
3. Plug in the power to the Pi.
4. Press ctrl+alt+f1 to quit from the GUI to the desktop
5. `sudo raspi-config`
6. `Boot Options` -> `Desktop / CLI` -> `Console Autologin`
7. `Advanced Options` -> `Expand Filesystem`
8. `Advanced Options` -> `Memory Split` -> "128"
9. "OK"
10. "Finish"
11. "Yes"
12. Wait for the reboot
13. `sudo raspi-config`
14. "Network options" -> "WiFi"
15. Choose your country. Pressing "u" will take you to USA.
16. Enter your network name and password.
17. "Interfacing Options" -> "Enable SSH"
18. "Localization" -> "Change Keyboard Layout" -> "Generic 104"
19. "Other" -> "English US" -> "Default" -> "No compose" -> "Yes"
20. "Finish"

#### 7.1.1 Raspberry Pi 3B+

If you are using a 3B+, and are experiencing under-voltage warnings, these may be relieved by the following command to update your Linux install to the latest:

```bash
sudo apt-get update && sudo apt-get dist-upgrade -y
```

Other causes of under-voltage warnings are low-quality USB cables, lose power port on the Pi, or a low quality power supply.

Make sure you are using a high-quality power cable if you are using a Pi 3B+

### 7.2 Install Software

1. Enter `ping google.com`. Press ctrl+c after a while. This will confirm that you have internet access. If you do not, then use rasp-config to re-enter your wi-fi
2. `cd ~`
3. `git clone https://github.com/JohnMarzulli/StratuxHud.git`
4. `cd StratuxHud`
5. `sudo apt-get install libgtk2.0-dev` a. Choose `Y` if prompted
6. `cd tools; ./install_splash.sh`
7. `python --version`. Verify that your version is 2.7.14
8. `sudo python3 setup.py develop` For Linux systems where you wish to develop or debug: `sudo setcap 'cap_net_raw,cap_net_admin+eip' ~/.local/lib/python2.7/site-packages/bluepy/bluepy-helper`
9. `sudo raspi-config`
10. Choose "WiFi" again, and enter `stratux` as the SSID. No password.
11. `sudo vim /etc/wpa_supplicant/wpa_supplicant.conf`
12. Delete the section that contains your WiFi network, leaving the section that contains the Stratux network.
13. More info on configuring Linux WiFi: <https://www.raspberrypi.org/forums/viewtopic.php?t=160620>
14. Save and quit.
15. Type "crontab -e"
16. Select "Nano" (Option 1)
17. Enter the following text at the _bottom_ of the file:

```bash
@reboot sudo python3 /home/pi/AithreToHud/aithre_manager.py &
@reboot nodejs       /home/pi/TrafficToHud/build/traffic_manager.js &
@reboot python3      /home/pi/DynonToHud/dynon_to_hud.py &
@reboot sudo python3 /home/pi/StratuxHud/stratux_hud.py &
@reboot nodejs       /home/pi/HudConfig/build/index.js &
```

1. Save and quit.

#### Alternative

Use LXDE autostart:

<https://www.raspberrypi.org/forums/viewtopic.php?t=275703>

#### 7.2.1 Developer Note

To ensure proper operation, if you are a developer the order services are brought online is important.

The following order is suggested:

1. Stratux
1. AithreManager
1. DynonToHud
1. TrafficManager
1. StratuxHud
1. HudConfig

The AithreManager has no external dependencies.

The DynonToHud service has no external dependencies.

The TrafficManager uses the Stratux ADS-B services and received.

The StratuxHud depends on the AithreManager and the TrafficManager. It can optionally use DynonToHud.

The HudConfig depends on the StratuxHud

#### 7.2.1 Upgrading From v1.7

If you are compiling from source code and upgrading from V1.7, some additional steps will need to be taken.

First, you will need to delete all .pyc files.
It is also reccomended that you delete the `__pycache__` directory.
The `traffic manager`, `node_modules`, `lib`, and `aithre_manager` directories are no longer used and should be removed.

### 7.3 Ownship

You may have the HUD ignore your own aircraft using a "OWNSHIP" functionality. The OWNSHIP value is set using the Stratux. The HUD retrieves the Mode S code set as the OWNSHIP and then filters out all reports so they are ignored.

Please refer to the Stratux documentation on how to set the OWNSHIP value.

### 7.4 Aithre Support

Support for Aithre was added in V1.5

Values for the CO PPM are shown in the default `AHRS Only`, `AHRS + ADS-B`, and `System Information` views.

No additional setup is required, just simply turn on your Aithre and place it within range of the StratuxHud processing unit.

NOTE: Aithre support will only work on Raspberry Pi units that have a Bluetooth chip, such as the 3, and 3B+. The RPi2 and earlier will not work.

NOTE: The Aithre hardware supports only a single device at a time. If you wish to use the phone app to display your CO PPM values:

1. Use the HudConfig tool to disable Aithre support

Alternatively:

1. Open `/root/hud_config.json`
2. Set the "aithre" line to: `"aithre": false,`
3. Save and close.

#### 7.4.1 BlueTooth for AIO Setups

**EXPERIMENTAL**

For All In One (Stratux + HUD on the same machine) setups, additional steps need to be taken.

Due to the needs of the GPS, the normal BlueTooth functions are disabled. Edit the /boot/config.txt to include the following line **beneath** the line that sets the overlay to value of `dtoverlay` to "miniuart".

```
enable_uart=1
```

Edit the line towards the bottom to have `core_freq=250`

More details on Pi3 Bluetooth can be found here: <https://www.cnet.com/how-to/how-to-setup-bluetooth-on-a-raspberry-pi-3/>

_**Warning**_

It has been found that enabling BlueTooth and the GPS simultaneously can cause hardware instability. This needs to be considered an experimental feature and only used if you are willing to potentially lose the Stratux during flight.

### 7.5 Kivic Based Setup

1. Install the Kivic projector per the Kivic directions. Please note that there is a release clip and the unit is removable. Also note that the combiner glass can be adjusted fore and aft.
2. Plug in the 3.5mm TRS cable between the Raspberry Pi and the Kivic. This is the same hole as the audio adapter for the Pi.
3. Plug the number pad into the Raspberry Pi.
4. You will need to run two Micro USB (5v) power cables. One to the HUD and one to the Raspberry Pi processing unit. These may be run from a battery bank, or from the ship's power **if** you have 5V USB outlets.
5. You may use the _optional_ sleeving to help keep the install tidy.

## 8 Appendix

### 8.1 Updating StratuxHud Code

If you would like to update from an earlier version to V1.5

1. Connect to a network using the ethernet cable.
2. Connect your Pi to a monitor using an HDMI cable. Connect a keyboard.
3. Reboot.
4. Press "Q" while the HUD is running to quit to a command line.
5. cd /home/pi/StratuxHud
6. `git fetch`
7. If you are currently running a version earlier than 1.5 _only_: `sudo cp *.json /root/`
8. `git stash`
9. `git checkout master`
10. `git pull`
11. If you have any errors, please report them immediately. Otherwise you are updated.
12. `sudo shutdown -h now`

### 8.2 Barrel Jack Connector (Raspberry Pi 3 only _**NOT 3B+**_)

You may consider using a barrel jack connector to supply power to your Pi unit.

These connectors are more durable than the Micro USB connector on the board, or are a good repair if your connector becomes damaged.

- [Barrel Jack (Female) To Wire Adapter](https://www.amazon.com/gp/product/B00QJAW9F4/ref=ppx_yo_dt_b_asin_title_o00_s00?ie=UTF8&psc=1)
- [USB A to Barrel Jack Plug (Male)](https://www.amazon.com/Onite-5-5x2-1mm-Positive-Electronic-Organorgan/dp/B01MZ0FWSK/ref=sr_1_1?keywords=Usb+2.0+a+to+5.5%2F2.1mm+Barrel+Connector+Jack+Dc+Power+Cable&qid=1567660324&s=gateway&sr=8-1)

You will find the solder pads on the bottom of the Raspberry Pi 3, near the Micro USB power Jack.

- Solder +5V (Red) to PP2
- Solder GND (White) to PP3

### 8.3 Revision History

| Date       | Version | Major Changes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|------------|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 2025-11-15 | 2.2     | Major refactor, addition of NEXRAD, weather products, radio frequencies, and more |
| 2020-10-31 | 2.0     | Migration to Python V3, with major refactoring of underlying code. New TopDownScope element and view.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2020-04-20 | 1.7     | Now able to cycle through views using the HudConfig page. Support for Illyrian by Aithre. Split Aithre data collection into a micro-service. Improve warning on some elements when GPS lock is lost. Fix user configuration files not always being used or saved. Support new V3 radio and Stratux 1.6\. Experimental support for Aithre in Stratux + HUD AIO configurations. Updates to distance conversion. Use the same naming strategy for aircraft as popular EFBs. Support data collected from Dynon serial output using the DynonToHud project. Indicate which speeds are IAS and groundspeed when GPS and Avionics data are both available. Update element positions. Added new indication when the Traffic service is not available. |
| 2019-09-04 | 1.6     | Traffic manager moved to a stand-alone service in NodeJs/TypeScript.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2019-06-30 | 1.5     | Support for the Aithre CO detector. New roll indicator. Various performance improvements. Visual warning if GPS is not plugged in. Use the OWNSHIP config from the receiver instead of the local config.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2019-03-31 | 1.4     | Add connection reset button. Fixes issues with the Diagnostic view running out of space. Initial port to Python 3.7                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2019-01-31 | 1.3     | Improvements to the communication with the Stratux. Update directions for Kivic install.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2018-10-13 | 1.2     | Major performance increases                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2018-09-07 | 1.1     | New system to allow views to be configurable                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2018-07-17 | 1.0     | Initial release                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

### 8.4 Hardware Performance

Please note that performance characteristics are only shown for displays that are currently available for purchase. The Hudly Classic is intentionally not listed.

| Board                          | Screen         | Frames Per Second (AHRS View Only) | Notes              |
|--------------------------------|----------------|------------------------------------|--------------------|
| Rasp Pi 2 (stand-alone)        | Sun Founder 5" | ~25FPS to ~30FPS                   | Not recommended    |
| Rasp Pi 3 (stand-alone)        | Kivic          | 50FPS - 60FPS                      | Recommended        |
| Rasp Pi 3 (stand-alone)        | Hudly Wireless | 30FPS - 50FPS                      | Recommended        |
| Rasp Pi 3 (Running on Stratux) | Kivic          | 30FPS                              | Highly Recommended |
| Rasp Pi 3 (Running on Stratux) | Hudly Wireless | 25FPS                              | Highly Recommended |
| Rasp Pi 3B+ (stand-alone)      | Kivic          | 55FPS - 60FPS                      | Recommended        |
| Rasp Pi 3B+ (stand-alone)      | Hudly Wireless | 40FPS - 60FPS                      | Recommended        |
| Rasp Pi 4 (stand-alone)        | Kivic          | 60FPS                              | Highly Recommended |
| Rasp Pi 4 (stand-alone)        | Hudly Wireless | 60FPS                              | Highly Recommended |

Please note that the frame rate is capped at 60FPS. Drawing any faster will not be detectable using the recommended output systems. Reducing the framerate will reduce the powerdraw.

## 9 Acknowledgements And Credits

This project uses the Liberation family of fonts. They can be found at <https://pagure.io/liberation-fonts/>

The initial project was inspired by Kris Knigga's PyAhrs project <https://github.com/kdknigga/pyahrs>

Many thanks to the Aithre team for providing the unit used to develop the plugin, and for their support in understanding the Aithre interface.

The following components are used:

- Python
- PyGame

... and of course Stratux

## 10 License

This project is covered by the GPL v3 license.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## NOTES

- Python 3.9 introduces issues with `isAlive`
- PyGame 1.9.6 is the last known working version. v2.0 instroduces issues with window creation.

## AIO Jessie Install

```bash
cd ~
wget https://www.openssl.org/source/openssl-1.1.1g.tar.gz
tar zxvf openssl-1.1.1g.tar.gz
cd openssl-1.1.1g
./config --prefix=/home/pi/openssl --openssldir=/home/pi/openssl no-ssl2
make
make install

cd~
wget https://www.python.org/ftp/python/3.8.8/Python-3.8.8.tgz
sudo tar zxf Python-3.8.8.tgz
cd Python-3.8.8
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/home/pi/openssl/lib/
sudo ./configure --enable-optimizations  --with-openssl=/home/pi/openssl/
sudo make
sudo make install
```

```bash
sudo apt install libsdl-mixer1.2-dev
sudo apt install libsdl2-ttf-dev libsdl2-mixer-dev libsdl2-image-dev libsdl-sound1.2-dev python3-pygame python3-pygame-sdl2

pip3 install setuptools
sudo python3 setup.py develop
pip3 install pygame==1.9.6
```

Installing Pygame V1.9.6 is important as 2.0 and newer do not allow for the creation of the framebuffer device.

## OpenGl

sudo apt install freeglut3 freeglut3-dev

pip3 install PyOpenGL PyOpenGL_accelerate

<https://www.raspberrypi.org/forums/viewtopic.php?t=223592>
<https://www.raspberrypi.org/forums/viewtopic.php?t=243892>
<https://www.raspberrypi.org/forums/viewtopic.php?t=266277>

## 11 Roadmap

- Dynon Skyview support
- Airball support
- Engine instruments and displays
- Audio alerts
- Turn "projection" on the radar map.
- Nearby airports
- View improvements

## Code Cleanliness Commands

```powershell
Get-ChildItem *.py -File | ForEach-Object {[PSCustomObject]@{FileName  = $_.Name; LineCount = (Get-Content $_.FullName | Measure-Object).Count}} | Sort-Object LineCount -Descending | Format-Table
```
