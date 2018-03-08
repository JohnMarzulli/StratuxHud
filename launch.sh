#!/bin/sh

# Allow the network to come up
sleep 15
./update.sh
python hangar_buddy.py
