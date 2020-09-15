#!/usr/bin/env python

import argparse
import sys
import threading
import time

from lib.common import ABORT_MSG, PLS_FINISH_MSG
from lib.requestgenerator import HTTPRequestGenerator
from lib.requestrecorder import HTTPRequestRecorder
from lib.requestsender import TCPRequestSender
from queue import Queue


def parse_args():
    parser = argparse.ArgumentParser(description='HTTP Request Fuzzer')

    parser.add_argument('-t', '--template', dest='template', help='path to the template file', required=True)
    parser.add_argument('-r', '--rules', dest='rules', help='path to the rules file', required=True)
    parser.add_argument('-o', '--host', dest='host', help='target IP or host name', required=True)
    parser.add_argument('-d', '--db', dest='db', help='path to the DB file', required=True)
    parser.add_argument('-p', '--port', dest='port', type=int, default=80, help='target port')
    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                        help='More verbose output of status information')
    parser.add_argument('-s', '--tls', dest='use_tls', action='store_true', default=False,
                        help='use TLS to connect to the target')
    parser.add_argument('-c', '--certificate', dest='cert', default=None, help='client certificate in PEM format')
    parser.add_argument('-k', '--key', dest='key', default=None, help='client key in PEM format')
    parser.add_argument('-n', '--threads', dest='threads', type=int, default=10, help='number of sender threads')
    parser.add_argument('-x', '--count', dest='count', type=int, default=1000, help='number of requests to send')

    return parser.parse_args()


def leave(message, threads, commandqueue, verbose):
    if verbose:
        print('\nSending signal to sender threads.')
    for i in range(len(threads) - 2):
        # all except two threads are senders
        commandqueue.put(('sender', message))
    for t in threads:
        if t.name.startswith('Sender'):
            if verbose:
                print(f'Waiting for thread {t.name}\t', end="", flush=True)
            t.join()
            if verbose:
                print('🗸', flush=True)
    if verbose:
        print('Sender threads finished.')
        print('Terminating remaining threads.')
    commandqueue.put(('recorder', message))
    commandqueue.put(('generator', message))
    for t in threads:
        if not t.name.startswith('Sender'):
            if verbose:
                print(f'Waiting for thread {t.name}\t', end="", flush=True)
            t.join()
            if verbose:
                print('🗸', flush=True)
    sys.exit(0)


def main():
    args = parse_args()

    tlsConfig = {}
    tlsConfig['use_tls'] = args.use_tls
    tlsConfig['cert'] = args.cert
    tlsConfig['key'] = args.key

    requestqueue = Queue()
    responsequeue = Queue()
    commandqueue = Queue()

    threads = []
    if args.verbose:
        print("Creating and starting threads:", flush=True)
        print("Generator:\t", end="", flush=True)
    generator = HTTPRequestGenerator(args.template, args.rules, requestqueue, commandqueue, args.host, args.port, args.count)
    generatorthread = threading.Thread(target=generator.generate, name="Generator")
    generatorthread.start()
    threads.append(generatorthread)
    if args.verbose:
        print("started", flush=True)

    # wait a few seconds to enable the generator to put a few requests into the queue
    if args.verbose:
        print('Prepopulating request queue...', end='', flush=True)
    time.sleep(5)
    if args.verbose:
        print('done.', flush=True)
    if args.verbose:
        print("Senders:\t", end="", flush=True)
    for i in range(args.threads):
        sender = TCPRequestSender(requestqueue, responsequeue, commandqueue, tlsConfig)
        senderthread = threading.Thread(target=sender.send, name=f"Sender-{i}")
        senderthread.start()
        threads.append(senderthread)
    if args.verbose:
        print("started", flush=True)
    if args.verbose:
        print("Recorder:\t", end="", flush=True)
    recorder = HTTPRequestRecorder(responsequeue, commandqueue, args.db)
    recorderthread = threading.Thread(target=recorder.processResponse, name="Recorder")
    recorderthread.start()
    threads.append(recorderthread)
    if args.verbose:
        print("started", flush=True)

    try:
        timestamp = time.time()
        while True:
            time.sleep(1)
            if time.time() - timestamp >= 10:
                # print stats every 10 seconds
                print(f"Request queue: {requestqueue.qsize()} Response queue: {responsequeue.qsize()}    ", end='\r')
                timestamp = time.time()
            if responsequeue.qsize() == 0 and requestqueue.qsize() == 0:
                if args.verbose:
                    print("\nLooks like all queues are empty, exiting.")
                leave(PLS_FINISH_MSG, threads, commandqueue, args.verbose)
            if generator.done:
                if args.verbose:
                    print(f"\nGenerator is done creating {args.count} messages, exiting.")
                leave(PLS_FINISH_MSG, threads, commandqueue, args.verbose)
    except KeyboardInterrupt:
        print('\nCtrl+C detected, exiting...')
        leave(ABORT_MSG, threads, commandqueue, args.verbose)


if __name__ == "__main__":
    main()
