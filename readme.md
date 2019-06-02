# STRATUX HUD

## Introduction

This project aims to bring an affordable heads up display system into ANY cockpit.

The focus is to improve traffic awareness and to reduce the amount of time pilots reference tablets or an EFB.

**NOTE:** This project relies on having a [Stratux](http://stratux.me/) build with AHRS and GPS. A suitable build can be done for less than $150 (USD).

There are two versions that can be built:

### Recommended

Using the "Kivic HUD 2nd Gen" projector and a Raspberry Pi 3.

![Kivic Version](media/kivic_in_flight.jpg)

Estimated cost is $270

- $40 for RaspberryPi 3
- $195 for Kivic 2nd Gen projector
- Fans, case, cables

Uses 5V USB power.

**NOTE:** This project initially used and reccomendedly the "HUDLY Classic" projector which is no longer available.

**NOTE:** To have full functionality with a Stratux based unit, please use Stratux Version 1.4R5 or higher.

### Alternative, Less Expensive Version

A self contained system that uses a 3D printed case and teleprompter glass. This version can be built for the cost of a Raspberry Pi and the 3D print.

_NOTE:_ This version does have visibility issues in daylight conditions. Using an automotic HUD projector will result in full daylight visibility.

![Teleprompter Glass Version In Flight](media/in_flight.jpg)

Estimated Cost is $140

- $40 for a RaspberryPi 3
- $45 for the LCD screen
- $20 for Teleprompter Glass and shipping.
- Cost of 3D printing the special case.
- Cables

Can be powered by a USB powerbank or USB power.

## In Flight Controls

You may use a number pad as input device. I used velcro to secure the number pad to my dashboard.

Key       | Action
--------- | ----------------------------------------------------------------------------
Backspace | Tell the Stratux that you are in a level position. Resets the AHRS to level.
+         | Next view
-         | Previous view
=         | Toggle rendering debug information
Esc       | Send shutdown commands to both the HUD controller **and** the Stratux
q         | (_Full keyboard only_) Quit to the command line.
0/Ins     | Force a connection reset between the HUD and the Stratux

## Included (Default) Views

- AHRS + ADS-B
- Traffic
- Traffic List
- Universal Time
- Diagnostics
- (Blank)
- AHRS Only

### AHRS + ADS-B View

![AHRS + ADS-B](media/ahrs_plus_adsb_view.jpg)

This view shows attitude information along with targetting bugs that show the relative position and distance of traffic.

In this example:

- There are three (3) potential targets, all at a higher altitude. Two are relatively far away, one is closer.
- One of the targets is within our field of view and has a targetting reticle.
- With are rolled to the left slightly, less then 15 degrees.
- We are 309 feet MSL.
- We are stopped, with a groundspeed of 0MPH
- We have a GPS heading of 236, but do not have enough forward speed to obtain a heading from the AHRS chip. If the AHRS chip is unable to produce a reliable heading, `---` is shown for that portion of the heading.

_NOTE:_ This is the default view on startup. If you would like to switch to the `AHRS Only` You may press `-` on the keypad.

### Traffic View

![Traffic View Screenshot](media/traffic_view.jpg)

This view shows a heading strip, target bugs, targetting reticles, and "information cards" about our potential traffic.

In this example, `N2849K` is almost directly behind us (far left screen). The plane is 1.5 statute miles away, with a bearing of 70 degrees, and 100 feet above us.

### Traffic Listing View

![Traffic Listing View Screenshot](media/traffic_listing_view.jpg)

This shows us _at most_ the eight closest planes.

The *IDENT*ifier will be the tail number when available, otherwise the IACO identifier or callsign may be used. The *BEAR*ing is the heading to take to fly to that target. The *DIST*ance is the distance to the target. The *ALT*itude is given in relative terms, with two digits dropped.

In this example, the closest target is N1213S. The plane is only 1.2 statue mile away, and 1,500 feet above us.

### Diagnostics View

![Diagnostics View Screenshot](media/diagnostics_view.jpg)

The diagnostics view is designed to help give some troubleshooting ability. If a value is set for "OWNSHIP" (See the configuration file section), then any report from that tailnumber is ignored. The IP addressis provided so you may use the configuration webpage if you set it up.

### Universal Time

![Diagnostics View Screenshot](media/time_view.jpg)

Shows the current time in UTC at the bottom of the screen.

### Blank

A blank screen so no information is displayed.

### AHRS View

![Traffic View Screenshot](media/ahrs_view.jpg)

This is a similar view to `AHRS + ADS-B`, but removes any AHRS information.

## Parts List

### All Builds

_NOTE:_ This _does not_ include a power source. You will need to supply ship power from a 5V USB port or from a battery.

- [Raspberry Pi 3](https://www.amazon.com/Raspberry-Pi-RASPBERRYPI3-MODB-1GB-Model-Motherboard/dp/B01CD5VC92/ref=sr_1_3?s=electronics&ie=UTF8&qid=1529215701&sr=1-3&keywords=raspberry+pi+3)
- [Case For Raspberry Pi](https://www.amazon.com/iPhoenix-Raspberry-White-Compatible-Model/dp/B06XQSXZ97/ref=sr_1_3?s=electronics&dd=iYEspjjyeRXfqDW9BHwJFw%2C%2C&ddc_refnmnt=pfod&ie=UTF8&qid=1529215794&sr=1-3&keywords=white+raspberry+pi+3+case&refinements=p_97%3A11292772011)
- [Cooling Fan for Raspberry Pi](https://www.amazon.com/gp/product/B075R4S9GH/ref=od_aui_detailpages00?ie=UTF8&psc=1)
- [Micro USB Cable](https://www.amazon.com/AmazonBasics-Male-Micro-Cable-Black/dp/B0711PVX6Z/ref=sr_1_6?s=electronics&ie=UTF8&qid=1529215888&sr=1-6&keywords=micro+usb+cable)
- [Micro SD Card](https://www.amazon.com/SanDisk-Ultra-Micro-Adapter-SDSQUNC-016G-GN6MA/dp/B010Q57SEE/ref=sr_1_10?s=pc&ie=UTF8&qid=1529215944&sr=1-10&keywords=micro+sd+card)
- [Rottay Mechanical Keypad](https://www.amazon.com/Number-Rottay-Mechanical-Numeric-backlit/dp/B076FTSY6J/ref=sr_1_3?ie=UTF8&qid=1529215627&sr=8-3&keywords=mechanical+keypad)

### Recommended Kivic Build

- [Kiviv HUD 2nd Gen](https://www.amazon.com/gp/product/B078GHFMG5/ref=ppx_yo_dt_b_asin_title_o01__o00_s00?ie=UTF8&psc=1)
- [6' 3.5mm Analog Cable](https://www.amazon.com/gp/product/B074TDHRCC/ref=ppx_yo_dt_b_asin_title_o00_s01?ie=UTF8&psc=1)
- [_OPTIONAL_ 3/4" Wire Braiding](https://www.amazon.com/gp/product/B073YL3HMC/ref=ppx_yo_dt_b_asin_title_o00_s01?ie=UTF8&psc=1)

### 3D Print Build

- [Teleprompter Glass Sample of both thickness of the 60/40 glass](https://telepromptermirror.com/sample/)
- [SunFounder 5" TFT LCD](https://www.amazon.com/SunFounder-Monitor-Display-800X480-Raspberry/dp/B01HXSFIH6)

## Install instructions

### First Boot

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

#### Raspberry Pi 3B+

If you are using a 3B+, it may suffer from undervoltage alerts. These may be relieved by the following command to update your Linux install to the latest:

```bash
sudo apt-get update && sudo apt-get dist-upgrade -y
```

Make sure you are using a high quality power cable if you are using a Pi 3B+

### Install Software

1. Enter `ping google.com`. Press ctrl+c after a while. This will confirm that you have internet access. If you do not, then use rasp-config to re-enter your wi-fi
2. `cd ~`
3. `git clone https://github.com/JohnMarzulli/StratuxHud.git`
4. `cd StratuxHud`
5. `sudo apt-get install libgtk2.0-dev` a. Choose `Y` if prompted
6. `sudo cp ./media/hud_logo.png /usr/share/plymouth/themes/pix/splash.png`
7. `python --version`. Verify that your version is 2.7.14
8. `sudo python setup.py develop`
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
@reboot sudo python /home/pi/StratuxHud/stratux_hud.py &
```

1. Save and quit.

### Kivic Based Setup

1. Install the Kivic projector per the Kivic directions. Please note that there is a release clip and the unit is removable. Also note that the combiner glass can be adjusted fore and aft.
2. Plug in the 3.5mm TRS cable between the Raspberry Pi and the Kivic. This is the same hole as the audio adapter for the Pi.
3. Plug the number pad into the Raspberry Pi.
4. You will need to run two Micro USB (5v) power cables. One to the HUD and one to the Raspberry Pi processing unit. These may be run from a battery bank, or from the ship's power **if** you have 5V USB outlets.
5. You may use the _optional_ sleeving to help keep the install tidy.

### Teleprompter Glass Based Setup

1. Print the case.
2. Attach the LCD screen to the "GPIO Board" of the Raspberry Pi
3. Download the LCD drivers. <https://s3.amazonaws.com/sunfounder/Raspberry/images/LCD-show.tar.gz>
4. Install the LCD driver per SunFounder's instructions. <http://wiki.sunfounder.cc/index.php?title=5_Inch_LCD_Touch_Screen_Monitor_for_Raspberry_Pi>
5. Edit the StratuxHud config.json file so "flip_vertical" is True.
6. Plug the number pad into the Raspberry Pi

## Appendix

### Revision History

Date       | Version | Major Changes
---------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------
TBD        | 1.5     | Support for the Aithre CO detector. New roll indicator. Various performance improvements. Visual warning if GPS is not plugged in.
2019-03-31 | 1.4     | Add connection reset button. Fixes issues with the Diagnostic view running of of space. Initial port to Python 3.7
2019-01-31 | 1.3     | Improvements to the communication with the Stratux. Update directions for Kivic install.
2018-10-13 | 1.2     | Major performance increases
2018-09-07 | 1.1     | New system to allow views to be configurarable
2018-07-17 | 1.0     | Initial release

### Hardware Performance

Please note that performance characteristics are only shown for displays that are currently available for purchase. The Hudly Classic is intentionally not listed.

Board                          | Screen         | Frames Per Second (AHRS View Only) | Notes
------------------------------ | -------------- | ---------------------------------- | ---------------
Rasp Pi 2                      | Sun Founder 5" | ~25FPS to ~30FPS                   | Not reccomended
Rasp Pi 3 (stand alone)        | Kivic          | 50FPS - 60FPS                      | Reccomended
Rasp Pi 3 (stand alone)        | Hudly Wireless | 25FPS - 30FPS                      | Reccomended
Rasp Pi 3 (Running on Stratux) | Kivic          | 30FPS                              | Not supported
Rasp Pi 3B+                    | Kivic          | 55FPS - 60FPS                      | Reccomended
Rasp Pi 3B+                    | Hudly Wireless | 30FPS - 40FPS                      | Reccomended

Please note that the frame rate is capped at 60FPS. Drawing any faster will not be detectable using the reccomended output systems. Reducing the framerate will reduce the powerdraw.

## Acknowledgements And Credits

This project uses the Liberation family of fonts. They can be found at <https://pagure.io/liberation-fonts/>

The initial project was inspired by Kris Knigga's PyAhrs project <https://github.com/kdknigga/pyahrs>

The following components are used:

- Python
- PyGame
- Ws4Py

... and of course Stratux

## License

This project is covered by the GPL v3 license.

Please see

<license>
</license>
