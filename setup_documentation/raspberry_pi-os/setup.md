# New Image Setup (From Scratch) On Raspberry Pi OS

1. Download the latest version of Trixie, "OS Lite" version: https://www.raspberrypi.com/software/operating-systems/
2. Use Balena Etcher to flash the image to a 16GB SD card

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
sudo apt install python3-setuptools python3-pytest python-requests-docY
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