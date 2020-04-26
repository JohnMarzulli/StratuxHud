#! /bin/sh

sudo apt-get install fbi
sudo cp media/hud_logo.jpg /etc/splash.jpg

FILE = /etc/init.d/asplashscreen

if [ -f "$FILE" ]; then
    echo "Skipping"
else
    echo "Setting up boot logo."
    
    cp asplashscreen /etc/init.d/
    sudo chmod a+x /etc/init.d/asplashscreen
    sudo insserv /etc/init.d/asplashscreen
fi