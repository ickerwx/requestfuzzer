#!/usr/bin/env python

import argparse
import threading
import sys
from queue import Queue

from lib.requestgenerator import RequestGenerator
from lib.requestsender import RequestSender
from lib.requestrecorder import RequestRecorder


def parse_args():
    parser = argparse.ArgumentParser(description='HTTP Request Fuzzer')

    parser.add_argument('-t', '--template', dest='template', help='path to the template file', required=True)
    parser.add_argument('-r', '--rules', dest='rules', help='path to the rules file', required=True)
    parser.add_argument('-o', '--host', dest='host', help='target IP or host name', required=True)
    parser.add_argument('-d', '--db', dest='db', help='path to the DB file', required=True)
    parser.add_argument('-p', '--port', dest='port', type=int, default=80, help='target port')
    # parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
    #                     help='More verbose output of status information')
    parser.add_argument('-s', '--tls', dest='use_tls', action='store_true', default=False,
                        help='use TLS to connect to the target')
    parser.add_argument('-c', '--certificate', dest='cert', default=None, help='client certificate in PEM format')
    parser.add_argument('-k', '--key', dest='key', default=None, help='client key in PEM format')
    parser.add_argument('-n', '--threads', dest='threads', type=int, default=10, help='number of sender threads')

    return parser.parse_args()


def generate_requests(generator):
    while True:
        generator.generate()


def send_requests(sender):
    while True:
        sender.send()


def main():
    args = parse_args()

    tlsConfig = {}
    tlsConfig['use_tls'] = args.use_tls
    tlsConfig['cert'] = args.cert
    tlsConfig['key'] = args.key

    requestqueue = Queue()
    responsequeue = Queue()

    generator = RequestGenerator(args.template, args.rules, requestqueue, args.host, args.port)
    generatorthread = threading.Thread(target=generate_requests, args=(generator,))
    generatorthread.start()

    for i in range(args.threads):
        senderthread = threading.Thread(target=send_requests, args=(RequestSender(requestqueue, responsequeue, tlsConfig),))
        senderthread.start()

    try:
        recorder = RequestRecorder(responsequeue, args.db)
        while True:
            recorder.processResponse()
            # TODO: implement clean program termination
    except KeyboardInterrupt:
        print('\nCtrl+C detected, exiting...')
        sys.exit(0)


if __name__ == "__main__":
    main()
