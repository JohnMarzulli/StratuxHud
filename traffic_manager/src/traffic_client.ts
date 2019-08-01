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

var trafficCache: Map<string, Map<string, any>> = new Map<
  string,
  Map<string, any>
>();
var lastWebsocketReportTime: number = 0;

var WebSocketClient: WebSocket = null;

/**
 * Get the number of seconds since the given time.
 *
 * @param {number} lastTime The time we want to get the time since.
 * @returns {number} The number of seconds between NOW and the given time.
 */
function getSecondsSince(lastTime: number): number {
  if (lastTime == null) {
    return 0.0;
  }

  return (Date.now() - lastTime) / 1000;
}

/**
 * Is the report "reliable" and this should be returned to be
 * shown in the HUD?
 *
 * @param {Map<string, any>} inReport The report that we want to test.
 * @returns {boolean} True if the traffic has a valid position.
 */
function isReliableTraffic(inReport: Map<string, any>): boolean {
  return (
    inReport != null &&
    inReport[secondsSinceLastReportKey] != null &&
    inReport[icaoAddressKey] != null &&
    inReport[trafficReliableKey] != null &&
    inReport[trafficReliableKey] &&
    inReport[latitudeKey] != null &&
    inReport[longitudeKey] != null &&
    inReport[onGroundKey] != null &&
    inReport[distanceKey] != null &&
    inReport[altitudeKey] != null &&
    inReport[bearingKey] != null
  );
}

/**
 * Get the name that should be displayed on the HUD
 * for this traffic.
 *
 * Uses the registration mark if available, then the
 * the callsign/tailnumber, then finally the IACO code.
 *
 * @param {Map<string, any>} trafficReport The traffic we want to get a display name for.
 * @returns {string} The display name for the traffic.
 */
function getDisplayName(trafficReport: Map<string, any>): string {
  if (trafficReport == null) {
    return unknownDisplayName;
  }

  var outDisplayName: string = trafficReport[registrationNumberKey];

  if (outDisplayName == null) {
    outDisplayName = trafficReport[tailNumberKey].toString();
  }

  if (outDisplayName == null) {
    outDisplayName = trafficReport[icaoAddressKey].toString();
  }

  if (outDisplayName == null) {
    outDisplayName = unknownDisplayName;
  }

  return outDisplayName;
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
   * Take a traffic report and then merge in the latest data
   * that came from the WebSocket.
   *
   * Handles incremental updates to the traffic, merging new portions
   * of the report into the existing data.
   *
   * @private
   * @static
   * @param {Map<string, any>} report The incoming traffic report.
   * @returns {void}
   * @memberof TrafficClient
   */
  private static reportTraffic(report: Map<string, any>): void {
    try {
      if (report == null) {
        return;
      }

      var icaoAddress: string = report[icaoAddressKey].toString();

      // Create the entry if it is not already there.
      if (trafficCache[icaoAddress] == null) {
        trafficCache[icaoAddress] = report;
        // trafficCache[icaoAddress] = new Map<string, any>();
        console.log(Date.now().toLocaleString() + ": Adding " + icaoAddress);
      } else {
        // Now go an perform the painful merge
        Object.keys(report).forEach(key => {
          trafficCache[icaoAddress][key] = report[key];
        });
      }

      lastWebsocketReportTime = Date.now();
      trafficCache[icaoAddress][
        secondsSinceLastReportKey
      ] = lastWebsocketReportTime;
    } catch (e) {
      console.error("Issue merging report into cache:" + e);
    }
  }

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

    var newTrafficReport: Map<string, Map<string, any>> = new Map<
      string,
      Map<string, any>
    >();
    Object.keys(trafficCache).forEach(iacoCode => {
      var secondsSinceLastReport: number = getSecondsSince(
        trafficCache[iacoCode][secondsSinceLastReportKey]
      );

      if (secondsSinceLastReport > SecondsToPurgeReport) {
        ++purgedCount;
      } else {
        newTrafficReport[iacoCode] = trafficCache[iacoCode];
        ++keptCount;
      }
    });

    trafficCache = newTrafficReport;

    console.log("GC: Kept " + keptCount + ", purged " + purgedCount);
  }

  /**
   * Triggers the websocker to be torn down and then rebuilt.
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

    WebSocketClient = new WebSocket("ws://" + StratuxAddress + "/traffic");

    WebSocketClient.onopen = function () {
      console.log("Socket open");
    };

    WebSocketClient.onerror = function (error) {
      console.error("ERROR:" + error);
    };

    WebSocketClient.onmessage = function (message) {
      try {
        var json = JSON.parse(message.data.toString());
        TrafficClient.reportTraffic(json);
      } catch (e) {
        console.log(e + "Error handling traffic report: ", message.data);
      }
    };
  }

  /**
   * Checks on the WebSocket to see if it needs to be torn
   * down and rebuilt.
   *
   * Making sure the socket is always active is the highest
   * priortity of this module.
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
  public static getServiceStatusResponseBody(req: Request): any {
    return {
      socketStatus: WebSocketClient.readyState,
      socketTimeSinceLastTraffic: getSecondsSince(lastWebsocketReportTime),
      trackedTrafficCount: Object.keys(trafficCache).length
    };
  }

  /**
   * Get a dictionary to be turned into JSON
   * that gives an overview of the traffic.
   * This is a greatly reduced pacakge to save
   * on transfer time.
   *
   * @static
   * @param {Request} req
   * @returns {Map<string, Map<string, any>>}
   * @memberof TrafficClient
   */
  public static getTrafficOverviewResponseBody(
    req: Request
  ): Map<string, Map<string, any>> {
    {
      var response: Map<string, Map<string, any>> = new Map<
        string,
        Map<string, any>
      >();

      Object.keys(trafficCache).forEach(icaoAddress => {
        response[icaoAddress] = {
          secondsSinceLastReport: getSecondsSince(
            trafficCache[icaoAddress][secondsSinceLastReportKey]
          ),
          tailNumber: getDisplayName(trafficCache[icaoAddress])
        };
      });

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
   * @returns {Map<string, Map<string, any>>}
   * @memberof TrafficClient
   */
  public static getTrafficFullResponseBody(
    req: Request
  ): Map<string, Map<string, any>> {
    return trafficCache;
  }

  /**
   * Get a dictionary to be turned into JSON
   * of the traffice that is considered reliable
   * and CAN be shown in the HUD.
   *
   * Uses a slightly different format so as to normalize
   * the display names.
   *
   * @static
   * @param {Request} req
   * @returns {Map<string, Map<string, any>>}
   * @memberof TrafficClient
   */
  public static getTrafficReliableRepsonseBody(
    req: Request
  ): Map<string, Map<string, any>> {
    var outReliableTraffic: Map<string, Map<string, any>> = new Map<
      string,
      Map<string, any>
    >();

    Object.keys(trafficCache).forEach(iacoCode => {
      if (isReliableTraffic(trafficCache[iacoCode])) {
        var displayValue: string = getDisplayName(trafficCache[iacoCode]);

        outReliableTraffic[iacoCode] = new Map<string, Map<string, any>>();
        outReliableTraffic[iacoCode][displayNameKey] = displayValue;
        outReliableTraffic[iacoCode][secondsSinceLastReportKey] =
          trafficCache[iacoCode][secondsSinceLastReportKey];
        outReliableTraffic[iacoCode][latitudeKey] =
          trafficCache[iacoCode][latitudeKey];
        outReliableTraffic[iacoCode][longitudeKey] =
          trafficCache[iacoCode][longitudeKey];
        outReliableTraffic[iacoCode][onGroundKey] =
          trafficCache[iacoCode][onGroundKey];
        outReliableTraffic[iacoCode][distanceKey] =
          trafficCache[iacoCode][distanceKey];
        outReliableTraffic[iacoCode][altitudeKey] =
          trafficCache[iacoCode][altitudeKey];
        outReliableTraffic[iacoCode][bearingKey] =
          trafficCache[iacoCode][bearingKey];
      }
    });

    return outReliableTraffic;
  }

  /**
   * Get a dictionary to be turned into JSON that is just the RAW
   * data about the given traffic.
   *
   * Takes an IACO integer as the parameter.
   *
   * If a bad code is given, an empty set is returned.
   *
   * @static
   * @param {*} req The request that will containing the identifier of the traffic we want to get the details of.
   * @returns {*}
   * @memberof TrafficClient
   */
  public static getTrafficDetailsResponseBody(req: any): any {
    if (req == null || req.params == null || req.params.id == null) {
      return {};
    }

    try {
      var key: number = Number(req.params.id);

      return trafficCache[key];
    } catch {
      return Object.keys(trafficCache);
    }
  }
}

setInterval(
  TrafficClient.garbageCollectTraffic,
  SecondsToRunTrafficGarbageCollection * 1000
);
setInterval(TrafficClient.checkWebSocket, SecondsToCheckSocketClient * 1000);
