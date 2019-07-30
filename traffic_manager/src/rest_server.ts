// Shamelessly borrowed from https://mherman.org/blog/developing-a-restful-api-with-node-and-typescript/
// https://stackoverflow.com/questions/38802959/how-to-lock-on-object-which-shared-by-multiple-async-method-in-nodejs

import * as express from "express";
import * as logger from "morgan";
import * as bodyParser from "body-parser";
import { TrafficClient } from "./traffic_client";

/**
 * Service class that exposes the Traffic Client to the
 * rest of the world as a RESTful API.
 *
 * @class RestServer
 */
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
   * Performs a reset of the WebSocket + reconnect
   * and then returns a response body to indicate the success
   *
   * @private
   * @returns {*}
   * @memberof RestServer
   */
  private getServiceResetResponseBody(req: Request): any {
    TrafficClient.resetWebSocketClient();
    return {
      resetTime: new Date().toUTCString()
    };
  }

  /**
   * Creates an instance of RestServer to serve up
   * the data collected from the WebSocket as a RESTful service.
   * @memberof RestServer
   */
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

  /**
   * Create all of the routing from API endpoint to deletegates
   *
   * @private
   * @memberof RestServer
   */
  private routes(): void {
    let router = express.Router();

    var mapping = {
      "/": this.getServiceInfoResponseBody,
      "/Service/Info": this.getServiceInfoResponseBody,
      "/Service/Status": TrafficClient.getServiceStatusResponseBody,
      "/Service/Reset": this.getServiceResetResponseBody,
      "/Traffic/Summary": TrafficClient.getTrafficOverviewResponseBody,
      "/Traffic/Full": TrafficClient.getTrafficFullResponseBody,
      "/Traffic/Reliable": TrafficClient.getTrafficReliableRepsonseBody,
      "/Traffic/:id": TrafficClient.getTrafficDetailsResponseBody
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
