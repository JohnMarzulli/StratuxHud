# STRATUX HUD

## Introduction

This project aims to bring an affordable heads up display system into ANY cockpit.

There are two versions that can be built:

1. Self contained system that uses a 3D printed case and teleprompter glass. This version can be built for the cost of a Raspberry Pi and the 3D print.
2. Version using the HUDLY projector system. The project costs about $215 (on sale) and will still need a Raspberry Pi.

![Teleprompter Glass Version In Flight](media/in_flight.jpg)

## Install instructions

### First Boot

1. Flash latest Raspbian to an SD card
2. Plug in a keyboard and a monitor
3. Plug in the power to the Pi.
4. Press ctrl+alt+f1 to quit from the GUI to the desktop
5. `sudo raspi-config`
6. boot options -> desktop / cli -> "Console auto-login"
7. "Advanced options" -> "Expand Filesystem"
8. "OK"
9. "Finish"
10. "Yes"
11. Wait for the reboot
12. `sudo raspi-config`
13. "Network options" -> "WiFi"
14. Choose your country. Pressing "u" will take you to USA.
15. Enter your network name and password.
16. "Interfacing Options" -> "Enable SSH"
17. "Localization" -> "Change Keyboard Layout" -> "Generic 104"
18. "Other" -> "English US" -> "Default" -> "No compose" -> "Yes"
19. "Finish"

### Install Software

1. Enter `ping google.com`. Press ctrl+c after a while. This will confirm that you have internet access. If you do not, then use rasp-config to re-enter your wi-fi
2. `pip install ws4py`
3. `pip install pygame`
4. `pip install requests`
5. `cd ~`
6. `git clone https://github.com/JohnMarzulli/StratuxHud.git`

### HUDLY Based Setup

### Teleprompter Glass Based Setup

## Appendix

<http://wiki.sunfounder.cc/index.php?title=5_Inch_LCD_Touch_Screen_Monitor_for_Raspberry_Pi>

<https://s3.amazonaws.com/sunfounder/Raspberry/images/LCD-show.tar.gz>

<https://www.raspberrypi.org/forums/viewtopic.php?t=160620>

Teleprompter sample: <https://telepromptermirror.com/sample/>
