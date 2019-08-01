https://code.visualstudio.com/docs/typescript/typescript-compiling
https://jonathanmh.com/typescript-node-js-tutorial-backend-beginner/
https://mherman.org/blog/developing-a-restful-api-with-node-and-typescript/

``` bash

cd ~
curl -sL https://deb.nodesource.com/setup_12.x | sudo bash -
sudo apt install nodejs --assume-yes

sudo apt install node-typescript # Dev only

cd StratuxHud/traffic_manager
sudo npm install
```

```
tsc; node ./build/traffic_manager.js
```

```
curl http://localhost/Traffic/Reliable
```

@reboot node /home/pi/StratuxHud/traffic_manager/build/traffic_manager.js &