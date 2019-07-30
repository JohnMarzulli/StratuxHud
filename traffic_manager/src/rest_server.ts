// Shamelessly borrowed from https://mherman.org/blog/developing-a-restful-api-with-node-and-typescript/
// https://stackoverflow.com/questions/38802959/how-to-lock-on-object-which-shared-by-multiple-async-method-in-nodejs

import * as express from "express";
import * as logger from "morgan";
import * as bodyParser from "body-parser";
import * as WebSocket from "ws";
import { stringify } from "querystring";

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

/**
 * Take a traffic report and then merge in the latest data
 * that came from the WebSocket
 *
 * @param {Map<string, any>} report
 * @returns {void}
 */
function reportTraffic(report: Map<string, any>): void {
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

function garbageCollectTraffic(): void {
  console.log("Starting GC");

  var newTrafficReport: Map<string, Map<string, any>> = new Map<
    string,
    Map<string, any>
  >();
  Object.keys(trafficCache).forEach(iacoCode => {
    var secondsSinceLastReport: number = getSecondsSince(
      trafficCache[iacoCode][secondsSinceLastReportKey]
    );

    if (secondsSinceLastReport > SecondsToPurgeReport) {
      console.log("Purging " + iacoCode);
    } else {
      newTrafficReport[iacoCode] = trafficCache[iacoCode];
      console.log("Keeping " + iacoCode + " as " + trafficCache[iacoCode]);
    }
  });

  trafficCache = newTrafficReport;
}

var WebSocketClient: WebSocket = null;

function createWebSocketClient(): WebSocket {
  if (WebSocketClient != null) {
    WebSocketClient.close();
  }

  WebSocketClient = new WebSocket("ws://" + StratuxAddress + "/traffic");

  WebSocketClient.onopen = function() {
    console.log("Socket open");
  };

  WebSocketClient.onerror = function(error) {
    console.error("ERROR:" + error);
  };

  WebSocketClient.onmessage = function(message) {
    try {
      var json = JSON.parse(message.data.toString());
      reportTraffic(json);
    } catch (e) {
      console.log(e + "Error handling traffic report: ", message.data);
      return;
    }
  };

  return WebSocketClient;
}

function checkWebSocket(): void {
  if (
    WebSocketClient == null ||
    getSecondsSince(lastWebsocketReportTime) > WebSocketTimeoutSeconds
  ) {
    createWebSocketClient();
  }
}

setInterval(garbageCollectTraffic, SecondsToRunTrafficGarbageCollection * 1000);
setInterval(checkWebSocket, SecondsToCheckSocketClient * 1000);

function getSecondsSince(lastTime: number): number {
  if (lastTime == null) {
    return 0.0;
  }

  return (Date.now() - lastTime) / 1000;
}

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

// Creates and configures an ExpressJS web server.
class RestServer {
  // ref to Express instance
  public express: express.Application;

  /**
   * Returns the information about the service.
   * Intended to be used for compatibility checks
   * and the diagnostics view.
   *
   * @private
   * @returns {*}
   * @memberof RestServer
   */
  private getServiceInfoResponseBody(req: Request): any {
    return {
      server: {
        name: "StratuxHud",
        version: "1.6.0"
      }
    };
  }

  /**
   * Returns the status of the service and the web socket
   *
   * @private
   * @returns {*}
   * @memberof RestServer
   */
  private getServiceStatusResponseBody(req: Request): any {
    return {
      socketStatus: WebSocketClient.readyState,
      socketTimeSinceLastTraffic: getSecondsSince(lastWebsocketReportTime),
      trackedTrafficCount: Object.keys(trafficCache).length
    };
  }

  /**
   * Performs a reset of the WebSocket + reconnect
   * and then returns a response body to indicate the success
   *
   * @private
   * @returns {*}
   * @memberof RestServer
   */
  private getServiceResetResponseBody(req: Request): any {
    createWebSocketClient();
    return {
      resetTime: new Date().toUTCString()
    };
  }

  private getTrafficOverviewResponseBody(
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

  private getTrafficFullResponseBody(
    req: Request
  ): Map<string, Map<string, any>> {
    return trafficCache;
  }

  private getTrafficReliableRepsonseBody(
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
   *
   * @param request The request that will containing the identifier of the traffic we want to get the details of.
   */
  private getTrafficDetailsResponseBody(req: any): any {
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

  //Run configuration methods on the Express instance.
  constructor() {
    this.express = express();
    this.middleware();
    this.routes();
  }

  // Configure Express middleware.
  private middleware(): void {
    this.express.use(logger("dev"));
    this.express.use(bodyParser.json());
    this.express.use(bodyParser.urlencoded({ extended: false }));
  }

  // Configure API endpoints.
  private routes(): void {
    let router = express.Router();

    var mapping = {
      "/": this.getServiceInfoResponseBody,
      "/Service/Info": this.getServiceInfoResponseBody,
      "/Service/Status": this.getServiceStatusResponseBody,
      "/Service/Reset": this.getServiceResetResponseBody,
      "/Traffic/Summary": this.getTrafficOverviewResponseBody,
      "/Traffic/Full": this.getTrafficFullResponseBody,
      "/Traffic/Reliable": this.getTrafficReliableRepsonseBody,
      "/Traffic/:id": this.getTrafficDetailsResponseBody
    };

    Object.keys(mapping).forEach(key => {
      router.get(key, (req, res, next) => {
        res.json(mapping[key](req));
      });
    });

    // NOTE:
    // The "use root" appears to be required
    // for the Express routing to actually work.
    Object.keys(mapping).forEach(route => {
      this.express.use(route, router);
    });
  }
}

export default new RestServer().express;
