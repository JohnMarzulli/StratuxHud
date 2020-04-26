from http.server import HTTPServer

from configuration import configuration_host

CONFIGURATION_HOST_PORT = 8080


class HudServer(object):
    """
    Class to handle running a REST endpoint to handle configuration.
    """

    def get_server_ip(
        self
    ):
        """
        Returns the IP address of this REST server.

        Returns:
            string -- The IP address of this server.
        """

        return ''

    def run(
        self
    ):
        """
        Starts the server.
        """

        print("localhost = {}:{}".format(self.__local_ip__, self.__port__))

        self.__httpd__.serve_forever()

    def stop(
        self
    ):
        if self.__httpd__ is not None:
            self.__httpd__.shutdown()
            self.__httpd__.server_close()

    def __init__(
        self
    ):
        self.__port__ = CONFIGURATION_HOST_PORT
        self.__local_ip__ = self.get_server_ip()
        server_address = (self.__local_ip__, self.__port__)
        self.__httpd__ = HTTPServer(
            server_address, configuration_host.ConfigurationHost)


if __name__ == '__main__':
    host = HudServer()
    host.run()
