import sys
import matplotlib.pyplot as plt

class Entry:
    def __init__(self, data, id):
        self.id = id
        self.time = float(data[0])
        self.operation = data[1]
        self.block = data[2]
        self.length = data[3]

    def __str__(self):
        return str(currentID) + ": " + str(self.time) + ", " + self.operation + ", " + self.block + ", " + self.length


class Request:
    def __init__(self, id, time, queueLength):
        self.startTime = time
        self.id = id
        self.startQueue = queueLength
        self.endQueue = None
        self.endTime = None

    def completed(self, id, time, queueLength):
        if self.id != id:
            raise Exception('wrong id!')
        self.endTime = time
        self.endQueue = queueLength

    def getElapsedTime(self):
        return self.endTime - self.startTime


# read the input file
entries = []

inputFileName = sys.argv[1]
with open(inputFileName) as inputFile:
    currentID = 0
    for inputLine in inputFile.readlines():
        if '-' not in inputLine:
            if len(inputLine) > 12:
                entries.append(Entry(inputLine[12:].strip().replace('+', ' ').replace('  ', ' ').split(' '), currentID))
                # print(inputLine[12:])
                #print(entries[-1])
                # print()
            else:
                currentID += 1
inputFile.close()

# sort entries by time
entries.sort(key=lambda x: x.time)

#read through entries and track queue length
requests = [None] * currentID

queueLength = 0
for entry in entries:
    if entry.operation == 'Q':
        requests[entry.id] = Request(entry.id, entry.time, queueLength)
        queueLength += 1
    if entry.operation == 'C':
        requests[entry.id].completed(entry.id, entry.time, queueLength)
        queueLength -= 1
if queueLength != 0:
    raise Exception("Unfinished requests")

#sort requests by starting queue length
#requests.sort(key=lambda x : x.startQueue)
#for r in requests:
#    print(str(r.startQueue)+","+str(r.getElapsedTime()))

#plot results
lengths = [r.startQueue for r in requests]
times = [r.getElapsedTime() for r in requests]
plt.scatter(lengths, times, [1]*len(lengths))
plt.xlabel('Queue length')
plt.ylabel('Response time')
plt.ylim([0, 0.05])
plt.xlim([600, 700])
plt.show()
