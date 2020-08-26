import random
import string
import secrets
import shlex
import subprocess
import re
import time
import queue
from lib.common import Request
from abc import ABC, abstractmethod
from lib.common import ABORT_MSG, PLS_FINISH_MSG


# will loop over a wordlist
class WordlistAction:
    def __init__(self, wordlistpath):
        with open(wordlistpath, "r") as f:
            words = [word.strip() for word in f.readlines()]
        self.wordlist = words
        self.next = 0

    def exec(self):
        if self.next >= len(self.wordlist):
            self.next = 0
        word = self.wordlist[self.next]
        self.next += 1
        return word


class RandomAction:
    def __init__(self, type, length=20):
        if type not in ['randstr', 'randint', 'randbytes']:
            raise ValueError('type must be randstr, randint or randbytes')
        self.len = int(length)

        if type == 'randstr':
            self.exec = self.randomstr
        elif type == 'randint':
            self.exec = self.randomint
        else:
            self.exec = self.randombytes

    # generates a random alphanum string
    def randomstr(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=int(self.randomint())))

    def randomint(self):
        return str(random.randrange(self.len))

    def randombytes(self):
        return str(secrets.token_bytes(int(self.randomint())))


class CommandAction:
    def __init__(self, command):
        self.cmd = shlex.split(command)

    def exec(self):
        out = subprocess.run(self.cmd, stdout=subprocess.PIPE)
        return out.stdout.decode('utf-8').rstrip()


class GeneratorBase(ABC):
    @abstractmethod
    def generate(self):
        pass


class HTTPRequestGenerator(GeneratorBase):

    def __init__(self, templatefile, rulesfile, requestqueue, cmdqueue, host, port, count):
        with open(templatefile, "r") as f:
            template = f.read()

        self.template = template
        self.requestqueue = requestqueue
        self.cmdqueue = cmdqueue
        self.counter = 0
        self.maxcount = count
        self.done = False
        placeholders = set(re.findall(r"§(\w+)§", self.template))
        self.rules = {}
        self.destination = (host, int(port))

        with open(rulesfile, "r") as f:
            rules = [line.strip().split(":") for line in f.readlines()]

        for rule in rules:
            placeholder = rule[0]
            action = rule[1]
            param = rule[2]
            if action.lower() == 'wordlist':
                self.rules[placeholder] = WordlistAction(param)
            elif action.lower().startswith('rand'):
                self.rules[placeholder] = RandomAction(action, param)
            elif action.lower() == 'command':
                self.rules[placeholder] = CommandAction(param)

        for p in placeholders:
            if p not in self.rules.keys():
                raise ValueError("No action found for placeholder " + p)

    def generate(self):
        while True:
            # the method will exit if self.maxcount requests have been created or if the abort command has been given
            text = self.template
            for placeholder in self.rules.keys():
                text = text.replace(f"§{placeholder}§", self.rules[placeholder].exec())

            # detect line endings: \n or \r\n?
            lines = text.split('\n')
            end = '\r\n' if lines[0].endswith('\r') else '\n'

            # split text at 2*end to get request headers and body
            # then replace the content-length header with the correct value, if that header exists
            headers, body = text.split(2*end, 1)
            headers = re.sub(r"(content-length:)\s*\d+", r"\1 "+str(len(body)), headers, flags=re.IGNORECASE)
            text = headers + 2*end + body
            r = Request(bytes(text, "utf-8"), self.counter, self.destination)
            self.counter += 1
            self.requestqueue.put(r)  # write request into the queue, a sender thread will pull it
            if self.counter == self.maxcount:
                self.done = True
                return
            try:
                recipient, message = self.cmdqueue.get_nowait()
                if recipient == 'generator':
                    if message in [ABORT_MSG, PLS_FINISH_MSG]:
                        return
                else:
                    self.cmdqueue.put((recipient, message))
            except queue.Empty:
                # if the command queue is empty, just continue
                pass
            if self.requestqueue.qsize() > 100:
                time.sleep(1)

    def set_host(self, hostname):
        self.destination[0] = hostname

    def set_port(self, port):
        self.destination[1] = int(port)
