"""Usage:
    parserArgs.py [options] <btt-input-file> [<blkparse-input-file>]

Options:
    -r --reads                                  only look at read requests; requires blkparse output
    -w --writes                                 only look at write requests; requires blkparse output
    -m --merge-requests                         consider a group of merged requests to be one
    -M --unmerge-hardware-requests              consider a group of multiple requests to be
                                                multiple requests in the hardware queue
    --print-hardware-queue-length               print the calculated hardware queue length
    -q=EVENT --queue-spot=EVENT                 when in a request to graph the queue
                                                length (Q,M,G,I,D,C) [default: Q]
    -Q=QUEUE --queue-selection=QUEUE            which queue to graph the length of (software,
                                                hardware, both) [default: both]
    -t=TIME --start-time=TIME                   when to start measuring a request's
                                                response time (Q,M,G,I,D,C) [default: Q]
    -T=TIME --end-time=TIME                     when to finish measuring a request's
                                                response time (Q,M,G,I,D,C) [default: C]
    -x=RANGE --x-range=RANGE                    limit the x-axis to a certain range (eg [0, 100])
    -y=RANGE --y-range=RANGE                    limit the y-axis to a certain range (eg [0, 100])
    -h --hardware-queue                         plot the hardware queue vs time
    -s --software-queue                         plot the software queue vs time
    -a=RANGE --hardware-queue-x-range=RANGE    limit the x-axis of the hardware queue graph
                                                to a certain range (eg [0, 100])
    -b=RANGE --hardware-queue-y-range=RANGE    limit the y-axis of the hardware queue graph
                                                to a certain range (eg [0, 100])
    -c=RANGE --software-queue-x-range=RANGE    limit the x-axis of the software queue graph
                                                to a certain range (eg [0, 100])
    -d=RANGE --software-queue-y-range=RANGE    limit the y-axis of the software queue graph
                                                to a certain range (eg [0, 100])

"""

from docopt import docopt
from copy import deepcopy
import matplotlib.pyplot as plt
import ast
import re

args = docopt(__doc__, help=True)


# print(args)

blkparseEntries = {}

class Entry:
    def __init__(self, inputLine, id, lineNum):
        if lineNum == 0:
            raise Exception("wrong line number")
        data = inputLine[12:].strip().replace('+', ' ').replace('  ', ' ').split(' ')
        self.id = id
        self.line = lineNum
        self.time = float(data[0])
        self.operation = data[1]
        self.block = data[2]
        self.length = data[3]

    def __str__(self):
        return str(self.id) + ": " + str(
            self.time) + ", " + self.operation + ", " + self.block + ", " + self.length + ", " + str(self.line)


class BlkparseEntry:
    def __init__(self, time, operation, block, length):
        self.time = time
        self.operation = operation
        self.block = block
        self.length = length

    def new(inputLine):
        try:
            data = re.sub(' +', ' ', inputLine.replace('+', '')).split(' ')
            int(data[7])
            int(data[8])
            return BlkparseEntry(float(data[3]), data[5], data[7], data[8]), data[6]
        except Exception:
            return None, None
    def get(entry):
        blk = BlkparseEntry(entry.time, entry.operation, entry.block, entry.length)
        if blk in blkparseEntries:
            return blkparseEntries[blk]
        else:
            return ''

    def __str__(self):
        return str(self.time) +", "+ self.operation +", "+ self.block +", "+ self.length

    def __hash__(self):
        return hash((self.time, self.operation, self.block, self.length))

    def __eq__(self, other):
        return self.time == other.time and self.operation == other.operation and self.block == other.block and self.length == other.length



class Request:
    def __init__(self, id):
        self.id = id
        self.startTime = 0
        self.queueLength = None
        self.endTime = 0

    def setStartTime(self, id, time):
        if self.id != id:
            print(self.id)
            print(id)
            raise Exception('wrong id!')
        self.startTime = time

    def setEndTime(self, id, time):
        if self.id != id:
            raise Exception('wrong id!')
        self.endTime = time

    def setQueueLength(self, id, length):
        if self.id != id:
            raise Exception('wrong id!')
        self.queueLength = length

    def getElapsedTime(self):
        return self.endTime - self.startTime

    def getQueueLength(self):
        return self.queueLength


# validate args:
queueSpot = args["--queue-spot"].upper()
startTime = args["--start-time"].upper()
endTime = args["--end-time"].upper()

reads = args['--reads']
writes = args['--writes']
blkparse = args['<blkparse-input-file>']

allEvents = "QMGIDC"
if queueSpot not in allEvents:
    raise Exception("invalid queue spot")
if startTime not in allEvents:
    raise Exception("invalid start time")
if endTime not in allEvents:
    raise Exception("invlaid end time")
if allEvents.index(startTime) >= allEvents.index(endTime):
    raise Exception("start event should be BEFORE end event")
if reads and (not blkparse):
    raise Exception("tracking reads only requires blkparse file")
if writes and (not blkparse):
    raise Exception("tracking writes only requires blkparse file")

# read the blkparse file
if reads or writes:
    with open(blkparse) as inputFile:
        for inputLine in inputFile.readlines():
            entry, readwrite = BlkparseEntry.new(inputLine)
            if entry is not None:
                blkparseEntries[entry] = readwrite

# read the input file
entries = []

with open(args['<btt-input-file>']) as inputFile:
    # to be able to actually track a request
    currentID = 0
    currentLine = 0

    # to copy implicit G and I to other requests
    extraIDs = []
    lineGstr = ""
    lineGNum = 0
    lineIstr = ""
    lineINum = 0

    for inputLine in inputFile.readlines():
        # print(inputLine)
        currentLine += 1
        if '-' in inputLine:
            for id in extraIDs:
                entries.append(Entry(lineGstr, id, lineGNum))
                if lineINum != 0:
                    entries.append(Entry(lineGstr, id, lineINum))

            extraIDs = []
            lineGstr = ""
            lineGNum = 0
            lineIstr = ""
            lineINum = 0
        else:
            if len(inputLine) > 12:
                if 'G' in inputLine:
                    lineGstr = inputLine
                    lineGNum = currentLine
                    # kinda hackish thing to make up for lack of M
                    m = deepcopy(entries[-1])
                    m.operation = 'M'
                    entries.append(m)
                    mp = deepcopy(m)
                    mp.operation = 'Mp'
                    entries.append(mp)
                elif 'I' in inputLine:
                    lineIstr = inputLine
                    lineINum = currentLine
                else:
                    entries.append(Entry(inputLine, currentID, currentLine))
            else:
                extraIDs.append(currentID)
                currentID += 1
inputFile.close()

# entries.sort(key=lambda x: (x.time, x.id))
#
# for entry in entries:
#     print(entry)

# sort entries by time

if reads and writes:
    entries = [e for e in entries if 'R' in BlkparseEntry.get(e) or 'W' in BlkparseEntry.get(e)]
elif reads:
    entries = [e for e in entries if 'R' in BlkparseEntry.get(e)]
elif writes:
    entries = [e for e in entries if 'W' in BlkparseEntry.get(e)]


entries.sort(key=lambda x: x.time)

# read through entries and track
mergeReqs = args['--merge-requests']
unmergeHardware = args['--unmerge-hardware-requests']

sQueueLength = 0
hQueueLength = 0

requests = [Request(x) for x in range(currentID)]

lastDTime = 0
lastDBlock = 0
lastDlength = 0
lastCTime = 0
lastCBlock = 0
lastClength = 0

stimes = []  # could check if these are actually needed
htimes = []
hlengths = []
slengths = []

for entry in entries:
    if entry.operation == 'Q':
        sQueueLength += 1
        slengths.append(sQueueLength)
        stimes.append(entry.time)

    if mergeReqs:
        if entry.operation == 'M':
            sQueueLength -= 1
            slengths.append(sQueueLength)
            stimes.append(entry.time)
        if entry.operation == 'Mp':
            sQueueLength += 1
            slengths.append(sQueueLength)
            stimes.append(entry.time)

    if entry.operation == 'D':
        uniqueD = False
        if lastDTime != entry.time or lastDBlock != entry.block or lastDlength != entry.length:
            uniqueD = True
            lastDTime = entry.time
            lastDBlock = entry.block
            lastDlength = entry.length

        if mergeReqs:
            if uniqueD:
                sQueueLength -= 1
                slengths.append(sQueueLength)
                stimes.append(entry.time)
        else:
            sQueueLength -= 1
            slengths.append(sQueueLength)
            stimes.append(entry.time)

        if unmergeHardware:
            hQueueLength += 1
            hlengths.append(hQueueLength)
            htimes.append(entry.time)

        else:
            if uniqueD:
                hQueueLength += 1
                hlengths.append(hQueueLength)
                htimes.append(entry.time)

    if entry.operation == 'C':
        uniqueC = False
        if lastCTime != entry.time or lastCBlock != entry.block or lastClength != entry.length:
            uniqueC = True
            lastCTime = entry.time
            lastCBlock = entry.block
            lastClength = entry.length

        if unmergeHardware:
            hQueueLength -= 1
            hlengths.append(hQueueLength)
            htimes.append(entry.time)

        else:
            if uniqueC:
                hQueueLength -= 1
                hlengths.append(hQueueLength)
                htimes.append(entry.time)

    if entry.operation == args['--start-time']:
        requests[entry.id].setStartTime(entry.id, entry.time)

    if entry.operation == args['--end-time']:
        requests[entry.id].setEndTime(entry.id, entry.time)

    if entry.operation == args['--queue-spot']:
        length = 0
        if args['--queue-selection'] == 'software' or args['--queue-selection'] == 'both':
            length += sQueueLength
        if args['--queue-selection'] == 'hardware' or args['--queue-selection'] == 'both':
            length += hQueueLength
        requests[entry.id].setQueueLength(entry.id, length)

if args['--print-hardware-queue-length']:
    print(max(hlengths))

dispSoftware = args['--software-queue'] or args['--software-queue-x-range'] or args['--software-queue-y-range']
dispHardware = args['--hardware-queue'] or args['--hardware-queue-x-range'] or args['--hardware-queue-y-range']

lengths = [r.queueLength for r in requests if r.queueLength is not None]
times = [r.getElapsedTime() for r in requests if r.queueLength is not None]
plt.scatter(lengths, times, [1] * len(lengths))
plt.xlabel('Queue length')
plt.ylabel('Response time')
if args['--x-range']:
    plt.xlim(ast.literal_eval(args['--x-range']))
if args['--y-range']:
    plt.ylim(ast.literal_eval(args['--y-range']))
if dispSoftware or dispHardware:
    plt.figure()
else:
    plt.show()

if dispSoftware:
    plt.scatter(slengths, stimes)
    plt.xlabel('Software queue length')
    plt.ylabel('Time')
    if args['--software-queue-x-range']:
        plt.xlim(ast.literal_eval(args['--software-queue-x-range']))
    if args['--software-queue-y-range']:
        plt.ylim(ast.literal_eval(args['--software-queue-y-range']))
    if dispHardware:
        plt.figure()
    else:
        plt.show()
if dispHardware:
    plt.scatter(hlengths, htimes)
    plt.xlabel('Hardware queue length')
    plt.ylabel('Time')
    if args['--hardware-queue-x-range']:
        plt.xlim(ast.literal_eval(args['--hardware-queue-x-range']))
    if args['--hardware-queue-y-range']:
        plt.ylim(ast.literal_eval(args['--hardware-queue-y-range']))
    plt.show()
