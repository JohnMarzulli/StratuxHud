# New Image Setup (From Scratch) On Raspberry Pi OS

1. Download the latest version of Trixie, "OS Lite" version: <https://www.raspberrypi.com/software/operating-systems/>
1. Use Balena Etcher to flash the image to a 16GB SD card
1. If you use the Raspberry Pi Imager, set the default user account to `pi` and the password to `raspberry`. These are the defaults.

```bash
sudo apt update
sudo apt upgrade
```

```bash
sudo apt raspi-config
```

- Turn on SSH
- Set hostname to `stratuxhud`
- set SSID to `stratux` without a password
- Expand filesystem
- Save & reboot

```bash
sudo apt install nodejs
sudo apt install npm
sudo apt install python3-pip
sudo apt install libsdl2-2.0-0 libsdl2-dev libsdl2-mixer-2.0-0 libsdl2-mixer-dev libsdl2-ttf-2.0-0 libsdl2-ttf-dev
sudo apt install libsdl2-image-dev python3-pygame python3-pygame-sdl2 libsdl-sound1.2 libsdl-sound1.2-dev
sudo apt install python3-setuptools python3-pytest python-requests-docY python3-serial
```

```bash
git clone https://github.com/JohnMarzulli/StratuxHud.git
git clone https://github.com/JohnMarzulli/TrafficToHud.git
git clone https://github.com/JohnMarzulli/DynonToHud.git
```

```bash
cd StratuxHud
#python -m venv .venv
#chmod +x ./.venv/bin/activate
#./.venv/bin/activate
#pip3 install requests
```

## Starting The HUD Start On Boot

1. `sudo raspi-config`
1. Choose "WiFi" again, and enter `stratux` as the SSID. No password.
1. `sudo vim /etc/wpa_supplicant/wpa_supplicant.conf`
1. Delete the section that contains your WiFi network, leaving the section that contains the Stratux network.
1. More info on configuring Linux WiFi: <https://www.raspberrypi.org/forums/viewtopic.php?t=160620>
1. Save and quit.
1. Copy the StratuxHud.service file to /etc/systemd/system/
1. systemctl daemon-reload
1. systemctl enable StratuxHud

You will need to follow the similar instructions for TrafficToHud and DynonToHud (if using a Dynon)
