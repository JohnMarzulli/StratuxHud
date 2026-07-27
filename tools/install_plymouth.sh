#!/bin/bash
set -e

sudo apt install -y plymouth plymouth-themes

THEME_DIR=/usr/share/plymouth/themes/stratuxhud
sudo mkdir -p "$THEME_DIR"
sudo cp ./plymouth/stratuxhud.plymouth "$THEME_DIR/"
sudo cp ./plymouth/stratuxhud.script "$THEME_DIR/"
sudo cp ../media/hud_logo.jpg "$THEME_DIR/hud_logo.jpg"

sudo plymouth-set-default-theme -R stratuxhud

echo "Now add 'splash' to /boot/firmware/cmdline.txt and reboot."
