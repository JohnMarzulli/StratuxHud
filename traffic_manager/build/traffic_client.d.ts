declare class JsonPackage extends Map<string, any> {
}
declare class TrafficResponsePackage extends Map<string, JsonPackage> {
}
/**
 * Static class to package up the traffic client, websocket
 * helpers, and all of the other fun stuff to get the code
 * running nicely.
 *
 * @export
 * @class TrafficClient
 */
export declare class TrafficClient {
    /**
     * Looks at all of the existing traffic reports and then
     * prunes out anything that is old and should not be shown.
     *
     * @static
     * @memberof TrafficClient
     */
    static garbageCollectTraffic(): void;
    /**
     * Triggers the websocket to be torn down and then rebuilt.
     *
     * @static
     * @memberof TrafficClient
     */
    static resetWebSocketClient(): void;
    /**
     * Creates a new websocket. Sets up all of the callbacks
     * so traffic reports and error handling are performed.
     *
     * @static
     * @returns {WebSocket}
     * @memberof TrafficClient
     */
    static createWebSocketClient(): void;
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
    static checkWebSocket(): void;
    /**
     * Returns a dictionary that will become the JSON status of the service and the web socket.
     *
     * @private
     * @returns {*}
     * @memberof RestServer
     */
    static getServiceStatusResponseBody(req: Request): any;
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
    static getTrafficOverviewResponseBody(req: Request): TrafficResponsePackage;
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
    static getTrafficFullResponseBody(req: Request): TrafficResponsePackage;
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
    static getTrafficReliableResponseBody(req: Request): TrafficResponsePackage;
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
    static getTrafficDetailsResponseBody(req: any): any;
}
export {};
