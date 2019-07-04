#!/bin/bash

# Script to provide a simplier instalation process
# that is friendlier to users who are not familar with
# Linux or easier to build an ISO from.

##########
# STEP 1 #
##########
#
# Check to make sure that we can get the code and can connect to the wider internet.
if ping -q -c 1 -W 1 github.com >/dev/null; then
  echo "Able to connect to GitHub, continuing."
else
  echo "Unable to connect to GitHub. Please connect the Pi unit to the internet using the Ethernet port or WiFi."

  exit
fi


##########
# STEP 2 #
##########
#
# Make sure we have the lastest version of the HUD code.

cd ~/StratuxHud
git fetch
git stash
git checkout master
git pull


##########
# STEP 3 #
##########
#
# Make sure we have the latest version of the OS

echo raspberry | sudo -S apt-get update --assume-yes
echo raspberry | sudo -S sudo apt-get upgrade --fix-missing --assume-yes
echo raspberry | sudo -S apt-get install libgtk2.0-dev  --assume-yes
echo raspberry | sudo -S cp ./media/hud_logo.png /usr/share/plymouth/themes/pix/splash.png
echo raspberry | sudo -S sudo python setup.py develop

##########
# STEP 4 #
##########
#
# Setup the Raspberry Pi change the memory split to have more RAM for the GPU

echo raspberry | sudo -S raspi-config nonint get_config_var gpu_mem_128 /boot/config.txt

##########
# STEP 5 #
##########
#
# Setup the Raspberry Pi to automatically boot into StratuxHud

echo raspberry | sudo -S raspi-config nonint do_boot_behaviour B2
echo raspberry | sudo -S -c printf  '@reboot sudo python /home/pi/StratuxHud/stratux_hud.py &' > /var/spool/cron/crontabs/pi

##########
# STEP 6 #
##########
#
# Setup the WiFi network to point to a Stratux

echo raspberry | sudo -S -c printf 'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\ncountry=US\nnetwork={\n\tssid="stratux"\n\tkey_mgmt=NONE\n}' > /media/jmarzulli/rootfs/etc/wpa_supplicant/wpa_supplicant.conf

##########
# STEP 7 #
##########
#
# All done - Time to reboot
echo "Would have rebooted, but this is a WIP script..."