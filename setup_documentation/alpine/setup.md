# Running On Alpine Linux

This describes how to setup an image so StratuxHUD may run on a Pi 3, Pi 4, or Pi 5 using Alpine Linux

## Obtaining The Image

Use The Raspberry Pi imager to flash an SD card with Alpine

<https://wiki.alpinelinux.org/wiki/Raspberry_Pi?__goaway_challenge=cookie&__goaway_id=489c704f8ef90ebd0df02f36ee2931b8&__goaway_referer=https%3A%2F%2Fwww.google.com%2F>

Use a fresh SD card as the target.

If you are flashing from a Linux system, using gparted to expand the filesystem before boot is HIGHLY suggested. Expanding the filesystem from within the Alpine installation is hard and error prone

## First Boot

Please note that the default user is `root` without a password

### Setting Up The Pi

First you must prepare the APK package manager to see packages from the internet. By default it will only look at local media

```bash
apk add dhcpcd
rc-update add dhcpcd boot
service dhcpcd start
```

#### Expand the filesystem to the full memory card

```
apk add cfdisk
cfdisk
```

`reboot`


`vi /etc/apk/repositories`, Add these lines:

```text
https://dl-cdn.alpinelinux.org/alpine/v3.24/main
https://dl-cdn.alpinelinux.org/alpine/v3.24/community
```

### Version Note

The version (3.24.1) in the repositories file will need to match the version of Alpine you are using.

`cat /etc/alpine-release` will give you the EXACT version you will need to match.

If there is a minor version, that will be dropped in the config file. So 3.24.1 => 3.24

### Additional Software Installation

```bash
apk add sdl2 sdl2_image sdl2_mixer sdl2_ttf
apk add nodejs npm
apk add python3 py3-pip
apk add python3-dev build-base sdl2-dev sdl2_image-dev sdl2_mixer-dev sdl2_ttf-dev

```

### Verifying The Framebuffer Device Exists

Make sure the framebuffer device exists:

```bash
sh
ls -l /dev/fb0
```

If it doesn’t, install the kernel framebuffer drivers:

```bash
apk add linux-firmware
apk add mesa-dri-gallium
```

#### Force SDL to use the framebuffer

Place these settings in `/etc/profile.d/fb.sh:`

```bash
echo 'export SDL_VIDEODRIVER=fbcon' > /etc/profile.d/fb.sh
echo 'export SDL_FBDEV=/dev/fb0' >> /etc/profile.d/fb.sh
echo 'export SDL_AUDIODRIVER=alsa' >> /etc/profile.d/fb.sh
chmod +x /etc/profile.d/fb.sh
```

### Getting The StratuxHUD Suite

### StratuxHUD Configuration

```bash
cd ~
git clone https://github.com/JohnMarzulli/StratuxHud.git
cd ~
git clone https://github.com/JohnMarzulli/TrafficToHud.git
cd ~
git clone https://github.com/JohnMarzulli/DynonToHud.git
```

pip3 install pygame-ce

### Notes

You may want to checkout development versions to get latest versions, development, or testing.

### Validation
