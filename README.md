# HTTP Request Fuzzer

This programm will read a request template from a file and apply changes to that template defined in a rules file. These changes can be:
 
 - replace placeholder with word from a wordlist
 - replace placeholder with result from an executable
 - replace placeholder with random value (string, number or binary data)

It will generate requests, send them to the target and record the response. Response data will be written into an sqlite db.

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
  - command

### wordlist

Loop over a wordlist, one word at a time. If at the end, start again at the beginning. The only parameter for this is the path to the wordlist.

### rand(str|int|bytes)

Generate a random string, a random positive integer or a sequence of random bytes. The parameter is always a single positive number:
 - randstr/randbytes: the number is the maximum length of the string or the byte sequence
 - randint: the number is the upper bound, the generated number will be between 0 and the bound

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
