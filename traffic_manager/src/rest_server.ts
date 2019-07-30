// Shamelessly borrowed from https://mherman.org/blog/developing-a-restful-api-with-node-and-typescript/

import * as express from "express";
import * as logger from "morgan";
import * as bodyParser from "body-parser";

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

  private getTrafficOverviewResponseBody(req: any): any {
    // $TODO - Return basic information about ALL
    //         of the known traffic.
    return {
      traffic: []
    };
  }

  /**
   *
   * @param request The request that will containing the identifier of the traffic we want to get the details of.
   */
  private getTrafficDetailsResponseBody(req: any): any {
    // $TODO - Return detailed information about a specific
    //         piece of traffic
    return {
      icao: null,
      identifier: null,
      altitude: null,
      latitude: null,
      longitude: null,
      reportAge: null,
      heading: null,
      bearing: null,
      speed: null
    };
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
