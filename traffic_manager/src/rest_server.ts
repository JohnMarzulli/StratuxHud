// Shamelessly borrowed from https://mherman.org/blog/developing-a-restful-api-with-node-and-typescript/

import * as express from "express";
import * as logger from "morgan";
import * as bodyParser from "body-parser";

// Creates and configures an ExpressJS web server.
class RestServer {
  // ref to Express instance
  public express: express.Application;

  private GetServiceInfoPath: string = "/Service/Info";
  private GetServiceResetPath: string = "/Service/Reset";
  private GetServiceStatusPath: string = "/Service/Status";
  private GetTrafficOverviewPath: string = "/Traffic/All";
  private GetTrafficDetailsPath: string = "/Traffic/:id";

  /**
   * Returns the information about the service.
   * Intended to be used for compatibility checks
   * and the diagnostics view.
   *
   * @private
   * @returns {*}
   * @memberof RestServer
   */
  private getServiceInfoResponseBody(): any {
    return {
      server: {
        name: "StratuxHud",
        version: "1.6.0"
      }
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
  private getServiceResetResponseBody(): any {
    // $TODO - Actually perform the reset
    return {
      resetTime: new Date().toUTCString(),
      status: this.getServiceStatusResponseBody()
    };
  }

  /**
   * Returns the status of the service and the web socket
   *
   * @private
   * @returns {*}
   * @memberof RestServer
   */
  private getServiceStatusResponseBody(): any {
    // $TODO - Actually get the status of the socket
    return {
      socketStatus: null,
      socketTimeSinceLastTraffic: null,
      trackedTrafficCount: null
    };
  }

  private getTrafficOverviewResponseBody(): any {
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
  private getTrafficDetailsResponseBody(request: Request): any {
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

    // The main handler will return the basic information
    // on the Traffic Manager server
    router.get(this.GetServiceInfoPath, (req, res, next) => {
      res.json(this.getServiceInfoResponseBody());
    });

    // Handler that forces a re-connect of the web-socket
    router.get(this.GetServiceResetPath, (req, res, next) => {
      res.json(this.getServiceResetResponseBody());
    });

    // Handler that gets teh current status of the service
    router.get(this.GetServiceStatusPath, (req, res, next) => {
      res.json(this.getServiceStatusResponseBody());
    });

    // Handler that returns basic details about ALL known traffic
    router.get(this.GetTrafficOverviewPath, (req, res, next) => {
      res.json(this.getTrafficOverviewResponseBody());
    });

    // Handler that returns the full details about a single piece of traffic
    router.get(this.GetTrafficDetailsPath, (req, res, next) => {
      res.json(this.getTrafficDetailsResponseBody());
    });

    this.express.use(this.GetServiceInfoPath, router);
    this.express.use(this.GetServiceResetPath, router);
    this.express.use(this.GetServiceStatusPath, router);
    this.express.use(this.GetTrafficOverviewPath, router);
    this.express.use(this.GetTrafficDetailsPath, router);
  }
}

export default new RestServer().express;
