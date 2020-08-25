import sqlite3
import re


class RequestRecorder:
    def __init__(self, responsequeue, dbpath):
        self.queue = responsequeue
        self.connection = sqlite3.connect(dbpath)
        self.cursor = self.connection.cursor()
        if not self.check_table_exists():
            self.create_table()

    def check_table_exists(self):
        query = "SELECT count(name) FROM sqlite_master WHERE type='table' AND name='fuzzdata'"
        self.cursor.execute(query)
        return self.cursor.fetchone()[0] == 1

    def create_table(self):
        query = """CREATE TABLE fuzzdata (
            num INTEGER,
            host TEXT,
            port INTEGER,
            req_timestamp REAL,
            request TEXT,
            resp_timestamp REAL,
            response TEXT,
            code TEXT,
            length INTEGER)"""
        self.cursor.execute(query)

    def processResponse(self):
        query = "insert into fuzzdata values (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        response = self.queue.get()
        try:
            code = re.findall(r"HTTP/1.[01] (.*?)\r*\n", response.response.decode("utf-8"))[0]
        except Exception:
            code = "Unknown"
        try:
            length = re.findall(r"Content-Length:\s*(\d+)", response.response.decode("utf-8"))[0]
        except Exception:
            # detect line endings: \n or \r\n?
            lines = response.response.decode('utf-8').split('\n')
            end = '\r\n' if lines[0].endswith('\r') else '\n'

            # split text at 2*end to get request headers and body
            # then replace the content-length header with the correct value, if that header exists
            _, body = response.response.decode('utf-8').split(2*end, 1)
            length = len(body)
        request = response.request
        values = (request.num,)
        values += request.destination
        values += (request.time, request.request, response.time, response.response, code, length)
        self.cursor.execute(query, values)
        self.connection.commit()

    def __del__(self):
        self.cursor.close()
