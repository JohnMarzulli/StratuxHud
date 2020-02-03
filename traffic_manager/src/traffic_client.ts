import * as WebSocket from "ws";

const StratuxAddress: string = "192.168.10.1";
const SecondsToRunTrafficGarbageCollection: number = 5;
const SecondsToPurgeReport: number = 15;
const SecondsToCheckSocketClient: number = 1;
const WebSocketTimeoutSeconds: number = 10;

const icaoAddressKey: string = "Icao_addr";
const registrationNumberKey: string = "Reg";
const tailNumberKey: string = "Tail";
const trafficReliableKey: string = "Position_valid";
const latitudeKey: string = "Lat";
const longitudeKey: string = "Lng";
const onGroundKey: string = "OnGround";
const transponderCodeKey: string = "Squawk";
const distanceKey: string = "Distance";
const altitudeKey: string = "Alt";
const bearingKey: string = "Bearing";

const secondsSinceLastReportKey: string = "secondsSinceLastReport";
const displayNameKey: string = "displayName";

const unknownDisplayName = "UNKNOWN";

class JsonPackage extends Map<string, any>{ }
class TrafficResponsePackage extends Map<string, JsonPackage>{ }

var trafficCache: TrafficResponsePackage = new Map<string, JsonPackage>();
var lastWebsocketReportTime: number = 0;

var WebSocketClient: WebSocket;

/**
 * Get the number of seconds since the given time.
 *
 * @param {number} lastTime The time we want to get the time since.
 * @returns {number} The number of seconds between NOW and the given time.
 */
function getSecondsSince(
  lastTime: number
): number {
  if (lastTime == null) {
    return 0.0;
  }

  return (Date.now() - lastTime) / 1000;
}

function hasGpsKeys(
  inReport: JsonPackage
): boolean {
  return inReport != null
    && inReport[latitudeKey] != null
    && inReport[longitudeKey] != null;
}

function isReliableReport(
  inReport: JsonPackage
): boolean {
  return inReport != null
    && inReport[trafficReliableKey] != null
    && inReport[trafficReliableKey];
}

function containsKeyAndValueIsNonNull(
  inReport: JsonPackage,
  requiredKeyName: string
): boolean {
  return (requiredKeyName in inReport) && (inReport[requiredKeyName] != null);
}

function containsRequiredKeysToBeReliable(
  inReport: JsonPackage
): boolean {
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
  requiredKeys.forEach(requiredKeyName => {
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
function isReliableTraffic(
  inReport: JsonPackage
): boolean {
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
function getDisplayName(
  trafficReport: JsonPackage
): string {
  if (trafficReport == null) {
    return unknownDisplayName;
  }

  return trafficReport[registrationNumberKey]
    ?? trafficReport[tailNumberKey].toString()
    ?? trafficReport[icaoAddressKey].toString()
    ?? unknownDisplayName;
}

function isRequestInvalid(
  req: any
): boolean {
  return (req == null || req.params == null || req.params.id == null);
}

function getTrafficResponseSubPackage(
  icaoAddress: string
): any {
  return {
    secondsSinceLastReport: getSecondsSince(
      trafficCache[icaoAddress][secondsSinceLastReportKey]
    ),
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
function reportTraffic(
  report: JsonPackage
): void {
  try {
    if (report == null) {
      return;
    }

    var icaoAddress: string = report[icaoAddressKey].toString();

    // Create the entry if it is not already there.
    if (trafficCache[icaoAddress] == null) {
      trafficCache[icaoAddress] = report;
      console.log(`${Date.now().toLocaleString()}: Adding ${icaoAddress}`);
    } else {
      // Now go an perform the painful merge
      Object.keys(report).forEach(key => {
        trafficCache[icaoAddress][key] = report[key];
      });
    }

    lastWebsocketReportTime = Date.now();
    trafficCache[icaoAddress][secondsSinceLastReportKey] = lastWebsocketReportTime;
  } catch (e) {
    console.error(`Issue merging report into cache:${e}`);
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
export class TrafficClient {
  /**
   * Looks at all of the existing traffic reports and then
   * prunes out anything that is old and should not be shown.
   *
   * @static
   * @memberof TrafficClient
   */
  public static garbageCollectTraffic(): void {
    var keptCount: number = 0;
    var purgedCount: number = 0;

    var newTrafficReport: TrafficResponsePackage = new Map<string, JsonPackage>();
    Object.keys(trafficCache).forEach(icaoCode => {
      var secondsSinceLastReport: number = getSecondsSince(
        trafficCache[icaoCode][secondsSinceLastReportKey]
      );

      if (secondsSinceLastReport > SecondsToPurgeReport) {
        ++purgedCount;
      } else {
        newTrafficReport[icaoCode] = trafficCache[icaoCode];
        ++keptCount;
      }
    });

    trafficCache = newTrafficReport;

    console.log(`GC: Kept ${keptCount}, purged ${purgedCount}`);
  }

  /**
   * Triggers the websocket to be torn down and then rebuilt.
   *
   * @static
   * @memberof TrafficClient
   */
  public static resetWebSocketClient(): void {
    this.createWebSocketClient();
  }

  /**
   * Creates a new websocket. Sets up all of the callbacks
   * so traffic reports and error handling are performed.
   *
   * @static
   * @returns {WebSocket}
   * @memberof TrafficClient
   */
  public static createWebSocketClient(): void {
    if (WebSocketClient != null) {
      WebSocketClient.close();
    }

    WebSocketClient = new WebSocket(`ws://${StratuxAddress}/traffic`);

    WebSocketClient.onopen = function () {
      console.log("Socket open");
      lastWebsocketReportTime = Date.now();
    };

    WebSocketClient.onerror = function (error) {
      console.error(`ERROR:${error.message}`);
    };

    WebSocketClient.onmessage = function (message) {
      try {
        var json = JSON.parse(message.data.toString());
        reportTraffic(json);
      } catch (e) {
        console.log(`${e}: Error handling traffic report:`, message.data);
      }
    };
  }

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
  public static checkWebSocket(): void {
    if (
      WebSocketClient == null ||
      getSecondsSince(lastWebsocketReportTime) > WebSocketTimeoutSeconds
    ) {
      TrafficClient.createWebSocketClient();
    }
  }

  /**
   * Returns a dictionary that will become the JSON status of the service and the web socket.
   *
   * @private
   * @returns {*}
   * @memberof RestServer
   */
  public static getServiceStatusResponseBody(
    req: Request
  ): any {
    return {
      socketStatus: WebSocketClient.readyState,
      socketTimeSinceLastTraffic: getSecondsSince(lastWebsocketReportTime),
      trackedTrafficCount: Object.keys(trafficCache).length
    };
  }

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
  public static getTrafficOverviewResponseBody(
    req: Request
  ): TrafficResponsePackage {
    {
      var response: TrafficResponsePackage = new Map<string, JsonPackage>();

      for (const icaoAddress in Object.keys(trafficCache)) {
        response[icaoAddress] = getTrafficResponseSubPackage(icaoAddress);
      }

      return response;
    }
  }

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
  public static getTrafficFullResponseBody(
    req: Request
  ): TrafficResponsePackage {
    return trafficCache;
  }

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
  public static getTrafficReliableResponseBody(
    req: Request
  ): TrafficResponsePackage {
    var outReliableTraffic: TrafficResponsePackage = new Map<string, JsonPackage>();

    Object.keys(trafficCache).forEach(icaoCode => {
      if (isReliableTraffic(trafficCache[icaoCode])) {
        var displayValue: string = getDisplayName(trafficCache[icaoCode]);

        outReliableTraffic[icaoCode] = new Map<string, JsonPackage>();
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
  }

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
  public static getTrafficDetailsResponseBody(
    req: any
  ): any {
    return isRequestInvalid(req)
      ? {}
      : getCachedItemFromValidRequest(req);
  }
}

/**
 * Given a request, attempt to retrieve it from the cache.
 *
 * @param {{ params: { id: string; }; }} req The request that needs the cached item
 * @returns Any item found in the cache, otherwise a list of items in the cache.
 */
function getCachedItemFromValidRequest(
  req: { params: { id: string; }; }
) {
  var cachedItem = null;
  try {
    var key: number = Number(req?.params?.id);

    cachedItem = trafficCache[key];
  } catch {
    cachedItem = Object.keys(trafficCache);
  }

  return cachedItem;
}

setInterval(
  TrafficClient.garbageCollectTraffic,
  SecondsToRunTrafficGarbageCollection * 1000
);
setInterval(TrafficClient.checkWebSocket, SecondsToCheckSocketClient * 1000);
