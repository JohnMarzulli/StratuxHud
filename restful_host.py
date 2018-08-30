"""
Module to run a RESTful server to set and get the configuration.
"""


import sys
import datetime
import socket
import json
import shutil
import urllib
import os
import re
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import lib.utilities as utilities
import configuration
import lib.local_debug as local_debug

RESTFUL_HOST_PORT = 8080
CONFIGURATION = None
COMMAND_PROCESSOR = None

# Based on https://gist.github.com/tliron/8e9757180506f25e46d9

# EXAMPLES
# Invoke-WebRequest -Uri "http://localhost:8080/settings" -Method GET -ContentType "application/json"
# Invoke-WebRequest -Uri "http://localhost:8080/settings" -Method PUT -ContentType "application/json" -Body '{"declination": 0}'

ERROR_JSON = '{success: false}'


def get_views_list(handler):
    return json.dumps(configuration.CONFIGURATION.get_views_list(), indent=4, sort_keys=False)


def get_elements_list(handler):
    return json.dumps(configuration.CONFIGURATION.get_elements_list(), indent=4, sort_keys=False)


def get_settings(handler):
    """
    Handles a get-the-settings request.
    """
    if configuration.CONFIGURATION is not None:
        print("settings/GET")
        return configuration.CONFIGURATION.get_json_from_config()
    else:
        return ERROR_JSON


def set_settings(handler):
    """
    Handles a set-the-settings request.
    """

    if configuration.CONFIGURATION is not None:
        payload = handler.get_payload()
        print("settings/PUT:")
        print(payload)
        configuration.CONFIGURATION.update_configuration(payload)
        return configuration.CONFIGURATION.get_json_from_config()
    else:
        return ERROR_JSON


def set_views(handler):
    payload = handler.get_payload()
    view_config_text = json.dumps(payload, indent=4, sort_keys=True)
    print("views/PUT:\n{}".format(view_config_text))

    configuration.CONFIGURATION.write_views_list(view_config_text)

    return configuration.CONFIGURATION.get_views_list()


def get_json_success_response(text):
    """
    Returns a generic JSON response of success with
    text included in the payload.
    """

    return '{success: true, response:"' + text + '"}'


class RestfulHost(BaseHTTPRequestHandler):
    """
    Handles the HTTP response for status.
    """

    HERE = os.path.dirname(os.path.realpath(__file__))
    ROUTES = {
        r'^/settings': {'GET': get_settings, 'PUT': set_settings, 'media_type': 'application/json'},
        r'^/view_elements': {'GET': get_elements_list, 'media_type': 'application/json'},
        r'^/views': {'GET': get_views_list, 'PUT': set_views, 'media_type': 'application/json'},
    }

    def do_HEAD(self):
        self.handle_method('HEAD')

    def do_GET(self):
        self.handle_method('GET')

    def do_POST(self):
        self.handle_method('POST')

    def do_PUT(self):
        self.handle_method('PUT')

    def do_DELETE(self):
        self.handle_method('DELETE')

    def get_payload(self):
        try:
            payload_len = int(self.headers.getheader('content-length', 0))
            payload = self.rfile.read(payload_len)
            payload = json.loads(payload)
            return payload
        except:
            return {}

    def __handle_invalid_route__(self):
        """
        Handles the response to a bad route.
        """
        self.send_response(404)
        self.end_headers()
        self.wfile.write('Route not found\n')

    def __handle_file_request__(self, route, method):
        if method == 'GET':
            try:
                f = open(os.path.join(
                    RestfulHost.HERE, route['file']))
                try:
                    self.send_response(200)
                    if 'media_type' in route:
                        self.send_header(
                            'Content-type', route['media_type'])
                    self.end_headers()
                    shutil.copyfileobj(f, self.wfile)
                finally:
                    f.close()
            except:
                self.send_response(404)
                self.end_headers()
                self.wfile.write('File not found\n')
        else:
            self.send_response(405)
            self.end_headers()
            self.wfile.write('Only GET is supported\n')

    def __finish_get_put_delete_request__(self, route, method):
        if method in route:
            content = route[method](self)
            if content is not None:
                self.send_response(200)
                if 'media_type' in route:
                    self.send_header(
                        'Content-type', route['media_type'])
                self.end_headers()
                if method != 'DELETE':
                    self.wfile.write(json.dumps(content))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write('Not found\n')
        else:
            self.send_response(405)
            self.end_headers()
            self.wfile.write(method + ' is not supported\n')

    def __handle_request__(self, route, method):
        if method == 'HEAD':
            self.send_response(200)
            if 'media_type' in route:
                self.send_header('Content-type', route['media_type'])
            self.end_headers()
        else:
            if 'file' in route:
                self.__handle_file_request__(route, method)
            else:
                self.__finish_get_put_delete_request__(route, method)

    def handle_method(self, method):
        route = self.get_route()
        if route is None:
            self.__handle_invalid_route__()
        else:
            self.__handle_request__(route, method)

    def get_route(self):
        for path, route in RestfulHost.ROUTES.iteritems():
            if re.match(path, self.path):
                return route
        return None


class HudServer(object):
    """
    Class to handle running a REST endpoint to handle configuration.
    """

    def get_server_ip(self):
        """
        Returns the IP address of this REST server.

        Returns:
            string -- The IP address of this server.
        """

        return ''

    def run(self):
        """
        Starts the server.
        """

        print("localhost = {}:{}".format(self.__local_ip__, self.__port__))

        self.__httpd__.serve_forever()

    def __init__(self):
        self.__port__ = RESTFUL_HOST_PORT
        self.__local_ip__ = self.get_server_ip()
        server_address = (self.__local_ip__, self.__port__)
        self.__httpd__ = HTTPServer(server_address, RestfulHost)


if __name__ == '__main__':
    host = HudServer()
    host.run()
