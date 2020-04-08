"use strict";
var __extends = (this && this.__extends) || (function () {
    var extendStatics = function (d, b) {
        extendStatics = Object.setPrototypeOf ||
            ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
            function (d, b) { for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p]; };
        return extendStatics(d, b);
    };
    return function (d, b) {
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
var WebSocket = require("ws");
var StratuxAddress = "192.168.10.1";
var SecondsToRunTrafficGarbageCollection = 5;
var SecondsToPurgeReport = 15;
var SecondsToCheckSocketClient = 1;
var WebSocketTimeoutSeconds = 10;
var icaoAddressKey = "Icao_addr";
var registrationNumberKey = "Reg";
var tailNumberKey = "Tail";
var trafficReliableKey = "Position_valid";
var latitudeKey = "Lat";
var longitudeKey = "Lng";
var onGroundKey = "OnGround";
var transponderCodeKey = "Squawk";
var distanceKey = "Distance";
var altitudeKey = "Alt";
var bearingKey = "Bearing";
var secondsSinceLastReportKey = "secondsSinceLastReport";
var displayNameKey = "displayName";
var unknownDisplayName = "UNKNOWN";
var JsonPackage = /** @class */ (function (_super) {
    __extends(JsonPackage, _super);
    function JsonPackage() {
        return _super !== null && _super.apply(this, arguments) || this;
    }
    return JsonPackage;
}(Map));
var TrafficResponsePackage = /** @class */ (function (_super) {
    __extends(TrafficResponsePackage, _super);
    function TrafficResponsePackage() {
        return _super !== null && _super.apply(this, arguments) || this;
    }
    return TrafficResponsePackage;
}(Map));
var trafficCache = new Map();
var lastWebsocketReportTime = 0;
var WebSocketClient;
/**
 * Get the number of seconds since the given time.
 *
 * @param {number} lastTime The time we want to get the time since.
 * @returns {number} The number of seconds between NOW and the given time.
 */
function getSecondsSince(lastTime) {
    if (lastTime == null) {
        return 0.0;
    }
    return (Date.now() - lastTime) / 1000;
}
function hasGpsKeys(inReport) {
    return inReport != null
        && inReport[latitudeKey] != null
        && inReport[longitudeKey] != null;
}
function isReliableReport(inReport) {
    return inReport != null
        && inReport[trafficReliableKey] != null
        && inReport[trafficReliableKey];
}
function containsKeyAndValueIsNonNull(inReport, requiredKeyName) {
    return (requiredKeyName in inReport) && (inReport[requiredKeyName] != null);
}
function containsRequiredKeysToBeReliable(inReport) {
    var requiredKeys = [
        latitudeKey,
        longitudeKey,
        trafficReliableKey,
        secondsSinceLastReportKey,
        icaoAddressKey,
        onGroundKey,
        distanceKey,
        altitudeKey,
        bearingKey
    ];
    var requiredKeysAreNonNull = true;
    requiredKeys.forEach(function (requiredKeyName) {
        requiredKeysAreNonNull = requiredKeysAreNonNull && containsKeyAndValueIsNonNull(inReport, requiredKeyName);
    });
    return requiredKeysAreNonNull;
}
/**
 * Is the report "reliable" and this should be returned to be
 * shown in the HUD?
 *
 * @param {JsonPackage} inReport The report that we want to test.
 * @returns {boolean} True if the traffic has a valid position.
 */
function isReliableTraffic(inReport) {
    return containsRequiredKeysToBeReliable(inReport)
        && hasGpsKeys(inReport)
        && isReliableReport(inReport);
}
/**
 * Get the name that should be displayed on the HUD
 * for this traffic.
 *
 * Uses the registration mark if available, then the
 * the call sign/tail number, then finally the ICAO code.
 *
 * @param {JsonPackage} trafficReport The traffic we want to get a display name for.
 * @returns {string} The display name for the traffic.
 */
function getDisplayName(trafficReport) {
    var _a, _b, _c;
    if (trafficReport == null) {
        return unknownDisplayName;
    }
    return _c = (_b = (_a = trafficReport[tailNumberKey], (_a !== null && _a !== void 0 ? _a : trafficReport[registrationNumberKey].toString())), (_b !== null && _b !== void 0 ? _b : trafficReport[icaoAddressKey].toString())), (_c !== null && _c !== void 0 ? _c : unknownDisplayName);
}
function isRequestInvalid(req) {
    return (req == null || req.params == null || req.params.id == null);
}
function getTrafficResponseSubPackage(icaoAddress) {
    return {
        secondsSinceLastReport: getSecondsSince(trafficCache[icaoAddress][secondsSinceLastReportKey]),
        tailNumber: getDisplayName(trafficCache[icaoAddress])
    };
}
/**
 * Take a traffic report and then merge in the latest data
 * that came from the WebSocket.
 *
 * Handles incremental updates to the traffic, merging new portions
 * of the report into the existing data.
 *
 * @private
 * @static
 * @param {JsonPackage} report The incoming traffic report.
 * @returns {void}
 * @memberof TrafficClient
 */
function reportTraffic(report) {
    try {
        if (report == null) {
            return;
        }
        var icaoAddress = report[icaoAddressKey].toString();
        // Create the entry if it is not already there.
        if (trafficCache[icaoAddress] == null) {
            trafficCache[icaoAddress] = report;
            console.log(Date.now().toLocaleString() + ": Adding " + icaoAddress);
        }
        else {
            // Now go an perform the painful merge
            Object.keys(report).forEach(function (key) {
                trafficCache[icaoAddress][key] = report[key];
            });
        }
        lastWebsocketReportTime = Date.now();
        trafficCache[icaoAddress][secondsSinceLastReportKey] = lastWebsocketReportTime;
    }
    catch (e) {
        console.error("Issue merging report into cache:" + e);
    }
}
/**
 * Static class to package up the traffic client, websocket
 * helpers, and all of the other fun stuff to get the code
 * running nicely.
 *
 * @export
 * @class TrafficClient
 */
var TrafficClient = /** @class */ (function () {
    function TrafficClient() {
    }
    /**
     * Looks at all of the existing traffic reports and then
     * prunes out anything that is old and should not be shown.
     *
     * @static
     * @memberof TrafficClient
     */
    TrafficClient.garbageCollectTraffic = function () {
        var keptCount = 0;
        var purgedCount = 0;
        var newTrafficReport = new Map();
        Object.keys(trafficCache).forEach(function (icaoCode) {
            var secondsSinceLastReport = getSecondsSince(trafficCache[icaoCode][secondsSinceLastReportKey]);
            if (secondsSinceLastReport > SecondsToPurgeReport) {
                ++purgedCount;
            }
            else {
                newTrafficReport[icaoCode] = trafficCache[icaoCode];
                ++keptCount;
            }
        });
        trafficCache = newTrafficReport;
        console.log("GC: Kept " + keptCount + ", purged " + purgedCount);
    };
    /**
     * Triggers the websocket to be torn down and then rebuilt.
     *
     * @static
     * @memberof TrafficClient
     */
    TrafficClient.resetWebSocketClient = function () {
        this.createWebSocketClient();
    };
    /**
     * Creates a new websocket. Sets up all of the callbacks
     * so traffic reports and error handling are performed.
     *
     * @static
     * @returns {WebSocket}
     * @memberof TrafficClient
     */
    TrafficClient.createWebSocketClient = function () {
        if (WebSocketClient != null) {
            WebSocketClient.close();
        }
        WebSocketClient = new WebSocket("ws://" + StratuxAddress + "/traffic");
        WebSocketClient.onopen = function () {
            console.log("Socket open");
            lastWebsocketReportTime = Date.now();
        };
        WebSocketClient.onerror = function (error) {
            console.error("ERROR:" + error.message);
        };
        WebSocketClient.onmessage = function (message) {
            try {
                var json = JSON.parse(message.data.toString());
                reportTraffic(json);
            }
            catch (e) {
                console.log(e + ": Error handling traffic report:", message.data);
            }
        };
    };
    /**
     * Checks on the WebSocket to see if it needs to be torn
     * down and rebuilt.
     *
     * Making sure the socket is always active is the highest
     * priority of this module.
     *
     * @static
     * @memberof TrafficClient
     */
    TrafficClient.checkWebSocket = function () {
        if (WebSocketClient == null ||
            getSecondsSince(lastWebsocketReportTime) > WebSocketTimeoutSeconds) {
            TrafficClient.createWebSocketClient();
        }
    };
    /**
     * Returns a dictionary that will become the JSON status of the service and the web socket.
     *
     * @private
     * @returns {*}
     * @memberof RestServer
     */
    TrafficClient.getServiceStatusResponseBody = function (req) {
        return {
            socketStatus: WebSocketClient.readyState,
            socketTimeSinceLastTraffic: getSecondsSince(lastWebsocketReportTime),
            trackedTrafficCount: Object.keys(trafficCache).length
        };
    };
    /**
     * Get a dictionary to be turned into JSON
     * that gives an overview of the traffic.
     * This is a greatly reduced package to save
     * on transfer time.
     *
     * @static
     * @param {Request} req
     * @returns {Map<string, JsonPackage>}
     * @memberof TrafficClient
     */
    TrafficClient.getTrafficOverviewResponseBody = function (req) {
        {
            var response = new Map();
            for (var icaoAddress in Object.keys(trafficCache)) {
                response[icaoAddress] = getTrafficResponseSubPackage(icaoAddress);
            }
            return response;
        }
    };
    /**
     * Get a dictionary to be turned into JSON
     * that is the complete, RAW data known about
     * the current traffic situation.
     *
     * This can be large to transfer.
     *
     * @static
     * @param {Request} req
     * @returns {TrafficResponsePackage}
     * @memberof TrafficClient
     */
    TrafficClient.getTrafficFullResponseBody = function (req) {
        return trafficCache;
    };
    /**
     * Get a dictionary to be turned into JSON
     * of the traffic that is considered reliable
     * and CAN be shown in the HUD.
     *
     * Uses a slightly different format so as to normalize
     * the display names.
     *
     * @static
     * @param {Request} req
     * @returns {TrafficResponsePackage}
     * @memberof TrafficClient
     */
    TrafficClient.getTrafficReliableResponseBody = function (req) {
        var outReliableTraffic = new Map();
        Object.keys(trafficCache).forEach(function (icaoCode) {
            if (isReliableTraffic(trafficCache[icaoCode])) {
                var displayValue = getDisplayName(trafficCache[icaoCode]);
                outReliableTraffic[icaoCode] = new Map();
                outReliableTraffic[icaoCode][displayNameKey] = displayValue;
                outReliableTraffic[icaoCode][secondsSinceLastReportKey] = trafficCache[icaoCode][secondsSinceLastReportKey];
                outReliableTraffic[icaoCode][latitudeKey] = trafficCache[icaoCode][latitudeKey];
                outReliableTraffic[icaoCode][longitudeKey] = trafficCache[icaoCode][longitudeKey];
                outReliableTraffic[icaoCode][onGroundKey] = trafficCache[icaoCode][onGroundKey];
                outReliableTraffic[icaoCode][distanceKey] = trafficCache[icaoCode][distanceKey];
                outReliableTraffic[icaoCode][altitudeKey] = trafficCache[icaoCode][altitudeKey];
                outReliableTraffic[icaoCode][bearingKey] = trafficCache[icaoCode][bearingKey];
            }
        });
        return outReliableTraffic;
    };
    /**
     * Get a dictionary to be turned into JSON that is just the RAW
     * data about the given traffic.
     *
     * Takes an ICAO integer as the parameter.
     *
     * If a bad code is given, an empty set is returned.
     *
     * @static
     * @param {*} req The request that will containing the identifier of the traffic we want to get the details of.
     * @returns {*}
     * @memberof TrafficClient
     */
    TrafficClient.getTrafficDetailsResponseBody = function (req) {
        return isRequestInvalid(req)
            ? {}
            : getCachedItemFromValidRequest(req);
    };
    return TrafficClient;
}());
exports.TrafficClient = TrafficClient;
/**
 * Given a request, attempt to retrieve it from the cache.
 *
 * @param {{ params: { id: string; }; }} req The request that needs the cached item
 * @returns Any item found in the cache, otherwise a list of items in the cache.
 */
function getCachedItemFromValidRequest(req) {
    var _a, _b;
    var cachedItem = null;
    try {
        var key = Number((_b = (_a = req) === null || _a === void 0 ? void 0 : _a.params) === null || _b === void 0 ? void 0 : _b.id);
        cachedItem = trafficCache[key];
    }
    catch (_c) {
        cachedItem = Object.keys(trafficCache);
    }
    return cachedItem;
}
setInterval(TrafficClient.garbageCollectTraffic, SecondsToRunTrafficGarbageCollection * 1000);
setInterval(TrafficClient.checkWebSocket, SecondsToCheckSocketClient * 1000);
//# sourceMappingURL=traffic_client.js.map