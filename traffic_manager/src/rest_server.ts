// Shamelessly borrowed from https://mherman.org/blog/developing-a-restful-api-with-node-and-typescript/
// https://stackoverflow.com/questions/38802959/how-to-lock-on-object-which-shared-by-multiple-async-method-in-nodejs

import * as express from "express";
import * as logger from "morgan";
import * as bodyParser from "body-parser";
import * as WebSocket from "ws";
import { stringify } from "querystring";

const StratuxAddress: string = "192.168.10.1";
const SecondsToPurgeReport = 60 * 2;

const icaoAddressKey: string = "Icao_addr";

var trafficCache: Map<number, Map<string, any>> = new Map<
  number,
  Map<string, any>
>();

var lastTrafficReport: Map<number, Date> = new Map<number, Date>();

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

    var icaoAddress: number = parseInt(report[icaoAddressKey]);

    // Create the entry if it is not already there.
    if (trafficCache[icaoAddress] == null) {
      trafficCache[icaoAddress] = new Map<string, any>();
      console.log("Adding " + icaoAddress);
    }

    // Now go an perform the painful merge
    Object.keys(report).forEach(key => {
      trafficCache[icaoAddress][key] = report[key];
    });

    lastTrafficReport[icaoAddress] = Date.now();
  } catch (e) {
    console.error("Issue merging report into cache:" + e);
  }
}

function garbageCollectTraffic(): number {
  var numReportsRemoved: number = 0;

  var keysToRemove: number[] = [];

  Object.keys(lastTrafficReport).forEach(icaoAddress => {
    var secondsSinceLastReport: number =
      (Date.now() - lastTrafficReport[icaoAddress]) / 1000;

    if (secondsSinceLastReport > SecondsToPurgeReport) {
      keysToRemove.push(Number(icaoAddress));
    }
  });

  keysToRemove.forEach(trafficToRemove => {
    console.warn("Purging " + trafficToRemove);
    lastTrafficReport.delete(trafficToRemove);
    trafficCache.delete(trafficToRemove);
  });

  return numReportsRemoved;
}

const WebSocketClient = new WebSocket("ws://" + StratuxAddress + "/traffic");

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
  private getServiceInfoResponseBody(req: any): any {
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
  private getServiceStatusResponseBody(req: any): any {
    // $TODO - Actually get the status of the socket
    return {
      socketStatus: null,
      socketTimeSinceLastTraffic: null,
      trackedTrafficCount: null
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
  private getServiceResetResponseBody(req: any): any {
    // $TODO - Actually perform the reset
    return {
      resetTime: new Date().toUTCString()
    };
  }

  private getTrafficOverviewResponseBody(
    req: any
  ): Map<number, Map<string, any>> {
    // $TODO - Return basic information about ALL
    //         of the known traffic.
    {
      var response: Map<number, Map<string, any>> = new Map<
        number,
        Map<string, any>
      >();

      Object.keys(lastTrafficReport).forEach(icaoAddress => {
        var secondsSinceLastReport: number =
          (Date.now() - lastTrafficReport[icaoAddress]) / 1000;

        response[icaoAddress] = {
          secondsSinceLastReport: secondsSinceLastReport,
          tailNumber: trafficCache[icaoAddress]["Reg"]
        };
      });

      return response;
    }
  }

  private getTrafficFullResponseBody(req: any): any {
    garbageCollectTraffic();

    return trafficCache;
  }

  /**
   *
   * @param request The request that will containing the identifier of the traffic we want to get the details of.
   */
  private getTrafficDetailsResponseBody(req: any): any {
    if (req && req.params && req.params.id) {
      try {
        var key: number = Number(req.params.id);

        return trafficCache[key];
      } catch {
        return Object.keys(trafficCache);
      }
    }

    return null;
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
      "/Traffic/All": this.getTrafficOverviewResponseBody,
      "/Traffic/Full": this.getTrafficFullResponseBody,
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
