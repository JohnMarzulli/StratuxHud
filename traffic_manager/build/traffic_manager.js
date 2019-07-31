"use strict";
// Shamelessly borrowed from:
// https://mherman.org/blog/developing-a-restful-api-with-node-and-typescript/
// https://flaviocopes.com/node-websockets/
// https://medium.com/@martin.sikora/node-js-websocket-simple-chat-tutorial-2def3a841b61
Object.defineProperty(exports, "__esModule", { value: true });
var http = require("http");
var debug = require("debug");
var rest_server_1 = require("./rest_server");
debug("ts-express:server");
var DefaultPort = 3000;
var port = normalizePort(process.env.PORT || DefaultPort);
rest_server_1.default.set("port", port);
var server = http.createServer(rest_server_1.default);
server.listen(port);
server.on("error", onError);
server.on("listening", onListening);
/**
 * Extracts the actual value of the port from what is given.
 *
 * @param {(string | number)} originalValue The value from the environment or number from config.
 * @returns {number} The extracted value of the port number
 */
function getPortValue(originalValue) {
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
function normalizePort(val) {
    var port = getPortValue(val);
    return isNaN(port) || port < 0 ? DefaultPort : port;
}
function onError(error) {
    if (error.syscall !== "listen") {
        throw error;
    }
    var bind = "Port " + port;
    switch (error.code) {
        case "EACCES":
            console.error(bind + " requires elevated privileges");
            process.exit(1);
            break;
        case "EADDRINUSE":
            console.error(bind + " is already in use");
            process.exit(1);
            break;
        default:
            throw error;
    }
}
function onListening() {
    var addr = server.address();
    var bind = typeof addr === "string" ? "pipe " + addr : "port " + addr.port;
    debug("Listening on " + bind);
}
