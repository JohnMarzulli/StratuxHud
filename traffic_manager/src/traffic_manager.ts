// Shamelessly borrowed from:
// https://mherman.org/blog/developing-a-restful-api-with-node-and-typescript/
// https://flaviocopes.com/node-websockets/
// https://medium.com/@martin.sikora/node-js-websocket-simple-chat-tutorial-2def3a841b61

import * as http from "http";
import * as debug from "debug";
import * as WebSocket from "ws";

import RestServer from "./rest_server";

debug("ts-express:server");

const DefaultPort: number = 3000;
const StratuxAddress: string = "192.168.10.1";
const port: number = normalizePort(process.env.PORT || DefaultPort);
RestServer.set("port", port);

const server = http.createServer(RestServer);
const WebSocketClient = new WebSocket("ws://" + StratuxAddress + "/traffic");

WebSocketClient.onopen = function() {
  console.log("Socket open");
};

WebSocketClient.onerror = function(error) {
  console.error("ERROR:" + error);
};

WebSocketClient.onmessage = function(message) {
  console.log(message.data);

  // try to decode json (I assume that each message
  // from server is json)
  try {
    var json = JSON.parse(message.data.toString());
  } catch (e) {
    console.log("This doesn't look like a valid JSON: ", message.data);
    return;
  }
  // handle incoming message
};

server.listen(port);
server.on("error", onError);
server.on("listening", onListening);

/**
 * Extracts the actual value of the port from what is given.
 *
 * @param {(string | number)} originalValue The value from the environment or number from config.
 * @returns {number} The extracted value of the port number
 */
function getPortValue(originalValue: string | number): number {
  return typeof originalValue === "string"
    ? parseInt(originalValue, 10)
    : originalValue;
}

/**
 * Gets the port to open the REST server on.
 *
 * @param {(number | string)} val The port from the config or environment
 * @returns {number} The port to open the server on.
 */
function normalizePort(val: number | string): number {
  let port: number = getPortValue(val);

  return isNaN(port) || port < 0 ? DefaultPort : port;
}

function onError(error: NodeJS.ErrnoException): void {
  if (error.syscall !== "listen") {
    throw error;
  }

  let bind = "Port " + port;

  switch (error.code) {
    case "EACCES":
      console.error(`${bind} requires elevated privileges`);
      process.exit(1);
      break;

    case "EADDRINUSE":
      console.error(`${bind} is already in use`);
      process.exit(1);
      break;

    default:
      throw error;
  }
}

function onListening(): void {
  let addr = server.address();
  let bind = typeof addr === "string" ? `pipe ${addr}` : `port ${addr.port}`;
  debug(`Listening on ${bind}`);
}
