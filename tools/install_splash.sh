#! /bin/sh

sudo apt install fbi
sudo cp ./splashscreen.service /etc/systemd/system/splashscreen.service
sudo sudo systemctl enable splashscreen