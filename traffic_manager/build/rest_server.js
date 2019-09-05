"use strict";
// Shamelessly borrowed from https://mherman.org/blog/developing-a-restful-api-with-node-and-typescript/
// https://stackoverflow.com/questions/38802959/how-to-lock-on-object-which-shared-by-multiple-async-method-in-nodejs
Object.defineProperty(exports, "__esModule", { value: true });
var express = require("express");
var logger = require("morgan");
var bodyParser = require("body-parser");
var traffic_client_1 = require("./traffic_client");
/**
 * Service class that exposes the Traffic Client to the
 * rest of the world as a RESTful API.
 *
 * @class RestServer
 */
var RestServer = /** @class */ (function () {
    /**
     * Creates an instance of RestServer to serve up
     * the data collected from the WebSocket as a RESTful service.
     * @memberof RestServer
     */
    function RestServer() {
        this.express = express();
        this.middleware();
        this.routes();
    }
    /**
     * Returns the information about the service.
     * Intended to be used for compatibility checks
     * and the diagnostics view.
     *
     * @private
     * @returns {*}
     * @memberof RestServer
     */
    RestServer.prototype.getServiceInfoResponseBody = function (req) {
        return {
            server: {
                name: "StratuxHud",
                version: "1.6.0"
            }
        };
    };
    /**
     * Performs a reset of the WebSocket + reconnect
     * and then returns a response body to indicate the success
     *
     * @private
     * @returns {*}
     * @memberof RestServer
     */
    RestServer.prototype.getServiceResetResponseBody = function (req) {
        traffic_client_1.TrafficClient.resetWebSocketClient();
        return {
            resetTime: new Date().toUTCString()
        };
    };
    // Configure Express middleware.
    RestServer.prototype.middleware = function () {
        this.express.use(logger("dev"));
        this.express.use(bodyParser.json());
        this.express.use(bodyParser.urlencoded({ extended: false }));
    };
    /**
     * Create all of the routing from API endpoint to deletegates
     *
     * @private
     * @memberof RestServer
     */
    RestServer.prototype.routes = function () {
        var _this = this;
        var router = express.Router();
        var mapping = {
            "/": this.getServiceInfoResponseBody,
            "/Service/Info": this.getServiceInfoResponseBody,
            "/Service/Status": traffic_client_1.TrafficClient.getServiceStatusResponseBody,
            "/Service/Reset": this.getServiceResetResponseBody,
            "/Traffic/Summary": traffic_client_1.TrafficClient.getTrafficOverviewResponseBody,
            "/Traffic/Full": traffic_client_1.TrafficClient.getTrafficFullResponseBody,
            "/Traffic/Reliable": traffic_client_1.TrafficClient.getTrafficReliableRepsonseBody,
            "/Traffic/:id": traffic_client_1.TrafficClient.getTrafficDetailsResponseBody
        };
        Object.keys(mapping).forEach(function (key) {
            router.get(key, function (req, res, next) {
                res.json(mapping[key](req));
            });
        });
        // NOTE:
        // The "use root" appears to be required
        // for the Express routing to actually work.
        Object.keys(mapping).forEach(function (route) {
            _this.express.use(route, router);
        });
    };
    return RestServer;
}());
exports.default = new RestServer().express;
