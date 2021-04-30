# HTTP Request Fuzzer

I wrote this program to fuzz REST API calls. It will read a request template from a file and apply changes to that template defined in a rules file. These changes can be:
 
 - replace placeholder with word from a wordlist
 - replace placeholder with result from an executable
 - replace placeholder with random value (string, number or binary data)

It will generate requests, send them to the target and record the response. Response data will be written into an sqlite db.

## Usage

First prepare two files, a request template and a rules file (see next section for details). A typical call will look like this:

```
./requestfuzzer.py -t ./template -r ./rules --host target.example.net -p 443 --tls -c ./clientcert.pem -k ./key.pem -d ./record.db
```

You must use at least `-t/--template`, `-r/--rules`, `-o/--host` and `-d/--db`. This is the help text:

```
./requestfuzzer.py -h
usage: requestfuzzer.py [-h] -t TEMPLATE -r RULES -o HOST -d DB [-p PORT] [-v] [-s] [-c CERT] [-k KEY] [-n THREADS] [-x COUNT]

HTTP Request Fuzzer

optional arguments:
  -h, --help            show this help message and exit
  -t TEMPLATE, --template TEMPLATE
                        path to the template file
  -r RULES, --rules RULES
                        path to the rules file
  -o HOST, --host HOST  target IP or host name
  -d DB, --db DB        path to the DB file
  -p PORT, --port PORT  target port
  -v, --verbose         More verbose output of status information
  -s, --tls             use TLS to connect to the target
  -c CERT, --certificate CERT
                        client certificate in PEM format
  -k KEY, --key KEY     client key in PEM format
  -n THREADS, --threads THREADS
                        number of sender threads
  -x COUNT, --count COUNT
                        number of requests to send
```

The program can connect to a service that requires a TLS client certificate by using `-c/--certificate` and `-k/--key`.

## Structure

The program runs with three threads:
 - request generator: takes the template, applies the modifications, sends it into a request queue
 - request sender: reads the generated request from a queue, sends it and writes the response into another queue
 - response recorder: takes the response, parses some metadata out of it, then writes request, response and metadata to sqlite db

 ## Request Generator Rules

 The Request Generator will take two parameters, the template file and the rules file. The template file is a file that contains a single HTTP request that should be fuzzed.

 ```
POST /v1/foo/§endpoint§ HTTP/1.1
Host: foo.example.net
Accept: application/json
Content-Type: application/json
Content-Length: 10

{
    "foo": "§bar§",
    §lines§
}
 ```

 This template has three placeholders, `§endpoint§`, `§bar§` and `§lines§`. They can be named whatever you like and must start and end with `§` (yes, I stole that from burpsuite :P). Note that the `Content-Length` will be modified to be correct once the placeholders have been replaced.

 Now that we have the template, we need the actual rules. The rules file is a file that has one replacement rule per line, like this:

 ```
 endpoint:wordlist:/path/to/wordlist
 bar:randint:100
 lines:command:/path/to/script_or_executable --switchsupport=true
 ```

 The general format is `placeholdername:action:parameter`. The first field is the placeholder name, it's the same name used in the template sans the `§`. The second field is the action: what should be done to generate a value for this field. As of now these are the supported actions:

  - wordlist
  - randstr
  - randint
  - randbytes
  - randhex
  - randb64
  - command

### wordlist

Loop over a wordlist, one word at a time. If at the end, start again at the beginning. The only parameter for this is the path to the wordlist.

### rand(str|int|bytes|hex|b64)

Generate a random string, a random positive integer or a sequence of random bytes. The parameter is always a single positive number:
 - randstr/randbytes: the number is the maximum length of the string or the byte sequence
 - randint: the number is the upper bound, the generated number will be between 0 and the bound
 - randhex: the number is the exact length of the generated random hex string
 - randb64: take a random number, between 0 and *<number>*, random bytes and base64-encode them

### command

Run a command and read stdout. The placeholder will be replaced with the command's output. The output can be a multi-line string. Note that trailing whitespace will not be stripped.

## Response Recorder

The Recorder will take the responses and write them into a sqlite database. It will store the following data:

 - request number (num)
 - target host (host)
 - target port (port)
 - request timestamp (timestamp)
 - request string (request)
 - response timestamp
 - response string
 - HTTP response code
 - content length

## Tips and Notes

Although this program is used to fuzz HTTP requests, it is not at all aware of HTTP and its particular requirements and quirks. The code opens a socket and sends whatever you tell it to, then reads the response. At present, several things like `Content-Length` correction and reading response status codes are hardcoded, but you can easily write a seperate generator or recorder for pretty much any protocol, knock yourself out.

### HTTP Auth

Like I said, no part of this code is actually HTTP aware. If you need to test something behind HTTP authentication, either hardcode the header in your request template or write some code that does what needs to be done and then outputs a valid header. In your template you set a placeholder and let that placeholder be replaced by your code's output.
