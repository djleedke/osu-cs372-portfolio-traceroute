# #################################################################################################################### #
# Imports                                                                                                              #
# #################################################################################################################### #
import os
from socket import *
import struct
import time
import select


# #################################################################################################################### #
# Class IcmpHelperLibrary                                                                                              #
# #################################################################################################################### #
class IcmpHelperLibrary:
    # ################################################################################################################ #
    # Class IcmpPacket                                                                                                 #
    #                                                                                                                  #
    # References:                                                                                                      #
    # https://www.iana.org/assignments/icmp-parameters/icmp-parameters.xhtml                                           #
    #                                                                                                                  #
    # ################################################################################################################ #
    class IcmpPacket:
        # ############################################################################################################ #
        # IcmpPacket Class Scope Variables                                                                             #
        # ############################################################################################################ #
        __icmpTarget = ""               # Remote Host
        __destinationIpAddress = ""     # Remote Host IP Address
        __header = b''                  # Header after byte packing
        __data = b''                    # Data after encoding
        __dataRaw = ""                  # Raw string data before encoding
        __icmpType = 0                  # Valid values are 0-255 (unsigned int, 8 bits)
        __icmpCode = 0                  # Valid values are 0-255 (unsigned int, 8 bits)
        __packetChecksum = 0            # Valid values are 0-65535 (unsigned short, 16 bits)
        __packetIdentifier = 0          # Valid values are 0-65535 (unsigned short, 16 bits)
        __packetSequenceNumber = 0      # Valid values are 0-65535 (unsigned short, 16 bits)
        __ipTimeout = 30
        __ttl = 255                     # Time to live

        __DEBUG_IcmpPacket = False      # Allows for debug output

        # ############################################################################################################ #
        # IcmpPacket Class Getters                                                                                     #
        # ############################################################################################################ #
        def getIcmpTarget(self):
            return self.__icmpTarget

        def getDataRaw(self):
            return self.__dataRaw

        def getIcmpType(self):
            return self.__icmpType

        def getIcmpCode(self):
            return self.__icmpCode

        def getPacketChecksum(self):
            return self.__packetChecksum

        def getPacketIdentifier(self):
            return self.__packetIdentifier

        def getPacketSequenceNumber(self):
            return self.__packetSequenceNumber

        def getTtl(self):
            return self.__ttl

        # ############################################################################################################ #
        # IcmpPacket Class Setters                                                                                     #
        # ############################################################################################################ #
        def setIcmpTarget(self, icmpTarget):
            self.__icmpTarget = icmpTarget

            # Only attempt to get destination address if it is not whitespace
            if len(self.__icmpTarget.strip()) > 0:
                self.__destinationIpAddress = gethostbyname(self.__icmpTarget.strip())

        def setIcmpType(self, icmpType):
            self.__icmpType = icmpType

        def setIcmpCode(self, icmpCode):
            self.__icmpCode = icmpCode

        def setPacketChecksum(self, packetChecksum):
            self.__packetChecksum = packetChecksum

        def setPacketIdentifier(self, packetIdentifier):
            self.__packetIdentifier = packetIdentifier

        def setPacketSequenceNumber(self, sequenceNumber):
            self.__packetSequenceNumber = sequenceNumber

        def setTtl(self, ttl):
            self.__ttl = ttl

        # ############################################################################################################ #
        # IcmpPacket Class Private Functions                                                                           #
        # ############################################################################################################ #
        def __recalculateChecksum(self):
            print("calculateChecksum Started...") if self.__DEBUG_IcmpPacket else 0
            packetAsByteData = b''.join([self.__header, self.__data])
            checksum = 0

            # This checksum function will work with pairs of values with two separate 16 bit segments. Any remaining
            # 16 bit segment will be handled on the upper end of the 32 bit segment.
            countTo = (len(packetAsByteData) // 2) * 2

            # Calculate checksum for all paired segments
            print(f'{"Count":10} {"Value":10} {"Sum":10}') if self.__DEBUG_IcmpPacket else 0
            count = 0
            while count < countTo:
                thisVal = packetAsByteData[count + 1] * 256 + packetAsByteData[count]
                checksum = checksum + thisVal
                checksum = checksum & 0xffffffff        # Capture 16 bit checksum as 32 bit value
                print(f'{count:10} {hex(thisVal):10} {hex(checksum):10}') if self.__DEBUG_IcmpPacket else 0
                count = count + 2

            # Calculate checksum for remaining segment (if there are any)
            if countTo < len(packetAsByteData):
                thisVal = packetAsByteData[len(packetAsByteData) - 1]
                checksum = checksum + thisVal
                checksum = checksum & 0xffffffff        # Capture as 32 bit value
                print(count, "\t", hex(thisVal), "\t", hex(checksum)) if self.__DEBUG_IcmpPacket else 0

            # Add 1's Complement Rotation to original checksum
            checksum = (checksum >> 16) + (checksum & 0xffff)   # Rotate and add to base 16 bits
            checksum = (checksum >> 16) + checksum              # Rotate and add

            answer = ~checksum                  # Invert bits
            answer = answer & 0xffff            # Trim to 16 bit value
            answer = answer >> 8 | (answer << 8 & 0xff00)
            print("Checksum: ", hex(answer)) if self.__DEBUG_IcmpPacket else 0

            self.setPacketChecksum(answer)

        def __packHeader(self):
            # The following header is based on http://www.networksorcery.com/enp/protocol/icmp/msg8.htm
            # Type = 8 bits
            # Code = 8 bits
            # ICMP Header Checksum = 16 bits
            # Identifier = 16 bits
            # Sequence Number = 16 bits
            self.__header = struct.pack("!BBHHH",
                                   self.getIcmpType(),              #  8 bits / 1 byte  / Format code B
                                   self.getIcmpCode(),              #  8 bits / 1 byte  / Format code B
                                   self.getPacketChecksum(),        # 16 bits / 2 bytes / Format code H
                                   self.getPacketIdentifier(),      # 16 bits / 2 bytes / Format code H
                                   self.getPacketSequenceNumber()   # 16 bits / 2 bytes / Format code H
                                   )

        def __encodeData(self):
            data_time = struct.pack("d", time.time())               # Used to track overall round trip time
                                                                    # time.time() creates a 64 bit value of 8 bytes
            dataRawEncoded = self.getDataRaw().encode("utf-8")

            self.__data = data_time + dataRawEncoded

        def __packAndRecalculateChecksum(self):
            # Checksum is calculated with the following sequence to confirm data in up to date
            self.__packHeader()                 # packHeader() and encodeData() transfer data to their respective bit
                                                # locations, otherwise, the bit sequences are empty or incorrect.
            self.__encodeData()
            self.__recalculateChecksum()        # Result will set new checksum value
            self.__packHeader()                 # Header is rebuilt to include new checksum value

        def __validateIcmpReplyPacketWithOriginalPingData(self, icmpReplyPacket):
            # Hint: Work through comparing each value and identify if this is a valid response.
            
            is_valid = True

            # Checking sequence number
            if icmpReplyPacket.getIcmpSequenceNumber() != self.getPacketSequenceNumber():
                is_valid = False
            else:
                icmpReplyPacket.setIsValidSequenceNum(True)

            # Checking packet identifier
            if icmpReplyPacket.getIcmpIdentifier() != self.getPacketIdentifier():
                is_valid = False
            else:
                icmpReplyPacket.setIsValidIcmpIdentifier(True)

            # Checking raw data
            if icmpReplyPacket.getIcmpData() != self.getDataRaw():
                is_valid = False
            else:
                icmpReplyPacket.setIsValidRawData(True)

            
            icmpReplyPacket.setIsValidResponse(is_valid)
            

        # ############################################################################################################ #
        # IcmpPacket Class Public Functions                                                                            #
        # ############################################################################################################ #
        def buildPacket_echoRequest(self, packetIdentifier, packetSequenceNumber):
            self.setIcmpType(8)
            self.setIcmpCode(0)
            self.setPacketIdentifier(packetIdentifier)
            self.setPacketSequenceNumber(packetSequenceNumber)
            self.__dataRaw = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            self.__packAndRecalculateChecksum()

        def sendEchoRequest(self):
            if len(self.__icmpTarget.strip()) <= 0 | len(self.__destinationIpAddress.strip()) <= 0:
                self.setIcmpTarget("127.0.0.1")

            ping_msg = "Pinging (" + self.__icmpTarget + ") " + self.__destinationIpAddress
            print(ping_msg, end=" ")

            mySocket = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)
            mySocket.settimeout(self.__ipTimeout)
            mySocket.bind(("", 0))

            mySocket.setsockopt(IPPROTO_IP, IP_TTL, struct.pack('I', self.getTtl()))  # Unsigned int - 4 bytes
            try:
                mySocket.sendto(b''.join([self.__header, self.__data]), (self.__destinationIpAddress, 0))
                IcmpHelperLibrary.sent_packets += 1

                timeLeft = 30
                pingStartTime = time.time()
                startedSelect = time.time()
                whatReady = select.select([mySocket], [], [], timeLeft)
                endSelect = time.time()
                howLongInSelect = (endSelect - startedSelect)
                if whatReady[0] == []:  # Timeout
                    print("  *        *        *        *        *      Request timed out.")
                recvPacket, addr = mySocket.recvfrom(1024)  # recvPacket - bytes object representing data received
                # addr  - address of socket sending data
                timeReceived = time.time()
                timeLeft = timeLeft - howLongInSelect
                if timeLeft <= 0:
                    print("  *        *        *        *        *      Request timed out (By no remaining time left).")

                else:
                    # Fetch the ICMP type and code from the received packet
                    icmpType, icmpCode = recvPacket[20:22]

                    if icmpType == 11:                          # Time Exceeded
                        print("  TTL=%d    RTT=%.0f ms    Type=%d    Code=%d    %s" %
                                (
                                    self.getTtl(),
                                    (timeReceived - pingStartTime) * 1000,
                                    icmpType,
                                    icmpCode,
                                    addr[0]
                                )
                              , end=" ")
                        print(f' {IcmpHelperLibrary.icmpCodes[icmpType][icmpCode]}')
                        IcmpHelperLibrary.recv_packets += 1

                    elif icmpType == 3:                         # Destination Unreachable
                        print("  TTL=%d    RTT=%.0f ms    Type=%d    Code=%d    %s" %
                                  (
                                      self.getTtl(),
                                      (timeReceived - pingStartTime) * 1000,
                                      icmpType,
                                      icmpCode,
                                      addr[0]
                                  )
                              , end=" '")

                        print(f' {IcmpHelperLibrary.icmpCodes[icmpType][icmpCode]}')
                        IcmpHelperLibrary.recv_packets += 1

                    elif icmpType == 0:                         # Echo Reply
                        icmpReplyPacket = IcmpHelperLibrary.IcmpPacket_EchoReply(recvPacket)
                        self.__validateIcmpReplyPacketWithOriginalPingData(icmpReplyPacket)
                        icmpReplyPacket.printResultToConsole(self, self.getTtl(), timeReceived, addr)
                        IcmpHelperLibrary.recv_packets += 1
                        return icmpType     # Echo reply is the end and therefore should return

                    else:
                        print("error")
            except timeout:
                print(" " * len(ping_msg), end=" ")
                print("  *        *        *        *        *      Request timed out (By Exception).")
            finally:
                mySocket.close()

        def printIcmpPacketHeader_hex(self):
            print("Header Size: ", len(self.__header))
            for i in range(len(self.__header)):
                print("i=", i, " --> ", self.__header[i:i+1].hex())

        def printIcmpPacketData_hex(self):
            print("Data Size: ", len(self.__data))
            for i in range(len(self.__data)):
                print("i=", i, " --> ", self.__data[i:i + 1].hex())

        def printIcmpPacket_hex(self):
            print("Printing packet in hex...")
            self.printIcmpPacketHeader_hex()
            self.printIcmpPacketData_hex()

    # ################################################################################################################ #
    # Class IcmpPacket_EchoReply                                                                                       #
    #                                                                                                                  #
    # References:                                                                                                      #
    # http://www.networksorcery.com/enp/protocol/icmp/msg0.htm                                                         #
    #                                                                                                                  #
    # ################################################################################################################ #
    class IcmpPacket_EchoReply:
        # ############################################################################################################ #
        # IcmpPacket_EchoReply Class Scope Variables                                                                   #
        # ############################################################################################################ #
        __recvPacket = b''


        # ############################################################################################################ #
        # IcmpPacket_EchoReply Constructors                                                                            #
        # ############################################################################################################ #
        def __init__(self, recvPacket):
            self.__recvPacket = recvPacket
            self.__isValidResponse = False
            self.__isValidSequenceNum = False
            self.__isValidIcmpIdentifier = False
            self.__isValidRawData = False

        # ############################################################################################################ #
        # IcmpPacket_EchoReply Getters                                                                                 #
        # ############################################################################################################ #
        def getIcmpType(self):
            # Method 1
            # bytes = struct.calcsize("B")        # Format code B is 1 byte
            # return struct.unpack("!B", self.__recvPacket[20:20 + bytes])[0]

            # Method 2
            return self.__unpackByFormatAndPosition("B", 20)

        def getIcmpCode(self):
            # Method 1
            # bytes = struct.calcsize("B")        # Format code B is 1 byte
            # return struct.unpack("!B", self.__recvPacket[21:21 + bytes])[0]

            # Method 2
            return self.__unpackByFormatAndPosition("B", 21)

        def getIcmpHeaderChecksum(self):
            # Method 1
            # bytes = struct.calcsize("H")        # Format code H is 2 bytes
            # return struct.unpack("!H", self.__recvPacket[22:22 + bytes])[0]

            # Method 2
            return self.__unpackByFormatAndPosition("H", 22)

        def getIcmpIdentifier(self):
            # Method 1
            # bytes = struct.calcsize("H")        # Format code H is 2 bytes
            # return struct.unpack("!H", self.__recvPacket[24:24 + bytes])[0]

            # Method 2
            return self.__unpackByFormatAndPosition("H", 24)

        def getIcmpSequenceNumber(self):
            # Method 1
            # bytes = struct.calcsize("H")        # Format code H is 2 bytes
            # return struct.unpack("!H", self.__recvPacket[26:26 + bytes])[0]

            # Method 2
            return self.__unpackByFormatAndPosition("H", 26)

        def getDateTimeSent(self):
            # This accounts for bytes 28 through 35 = 64 bits
            return self.__unpackByFormatAndPosition("d", 28)   # Used to track overall round trip time
                                                               # time.time() creates a 64 bit value of 8 bytes

        def getIcmpData(self):
            # This accounts for bytes 36 to the end of the packet.
            return self.__recvPacket[36:].decode('utf-8')

        def isValidResponse(self):
            return self.__isValidResponse

        def isValidSequenceNum(self):
            return self.__isValidSequenceNum

        def isValidIcmpIdentifier(self):
            return self.__isValidIcmpIdentifier

        def isValidRawData(self):
            return self.__isValidRawData

        # ############################################################################################################ #
        # IcmpPacket_EchoReply Setters                                                                                 #
        # ############################################################################################################ #
        def setIsValidResponse(self, booleanValue):
            self.__isValidResponse = booleanValue

        def setIsValidSequenceNum(self, booleanValue):
            self.__isValidSequenceNum = booleanValue

        def setIsValidIcmpIdentifier(self, booleanValue):
            self.__isValidIcmpIdentifier = booleanValue

        def setIsValidRawData(self, booleanValue):
            self.__isValidRawData = booleanValue

        # ############################################################################################################ #
        # IcmpPacket_EchoReply Private Functions                                                                       #
        # ############################################################################################################ #
        def __unpackByFormatAndPosition(self, formatCode, basePosition):
            numberOfbytes = struct.calcsize(formatCode)
            return struct.unpack("!" + formatCode, self.__recvPacket[basePosition:basePosition + numberOfbytes])[0]

        # ############################################################################################################ #
        # IcmpPacket_EchoReply Public Functions                                                                        #
        # ############################################################################################################ #
        def printResultToConsole(self, sentPack, ttl, timeReceived, addr):
            bytes = struct.calcsize("d")
            timeSent = struct.unpack("d", self.__recvPacket[28:28 + bytes])[0]
            rtt = (timeReceived - timeSent) * 1000
            IcmpHelperLibrary.roundTripTimes.append(rtt)    # Adding the round trip time to our list for tracking

            print("  TTL=%d    RTT=%.0f ms    Type=%d    Code=%d        Identifier=%d    Sequence Number=%d    %s" %
                  (
                      ttl,
                      rtt,
                      self.getIcmpType(),
                      self.getIcmpCode(),
                      self.getIcmpIdentifier(),
                      self.getIcmpSequenceNumber(),
                      addr[0]
                  )
                 )

            # Checking if valid, if not printing out the reasons why
            if not self.isValidResponse():

                if not self.isValidSequenceNum():
                    print(f'  [Invalid Sequence Number]: Received: {self.getIcmpSequenceNumber()} Expected: {sentPack.getPacketSequenceNumber()}')

                if not self.isValidIcmpIdentifier():
                    print(f'  [Invalid Packet Identifier]: Received: {self.getIcmpIdentifier()} Expected:{sentPack.getPacketIdentifier()}')

                if not self.isValidRawData():
                    print(f'  [Invalid Raw Data]: Received: {self.getIcmpData()} Expected: {sentPack.getDataRaw()}')

    # ################################################################################################################ #
    # Class IcmpHelperLibrary                                                                                          #
    # ################################################################################################################ #

    # ################################################################################################################ #
    # IcmpHelperLibrary Class Scope Variables                                                                          #
    # ################################################################################################################ #
    __DEBUG_IcmpHelperLibrary = False               # Allows for debug output
    roundTripTimes = []                             # List we are going to use to track the RTT to get min/max/avg
    sent_packets = 0                                # Used for packet loss tracking # of sent packets
    recv_packets = 0                                # Used for packet loss tracking # of received packets

    # Reference: https://www.iana.org/assignments/icmp-parameters/icmp-parameters.xhtml
    icmpCodes = {
        3 : {
            0 : 'Net Unreachable',
            1 : 'Host Unreachable',
            2 : 'Protocol Unreachable',
            3 : 'Port Unreachable',
            4 : 'Fragmentation Needed and Don\'t Fragment was Set',
            5 : 'Source Route Failed',
            6 : 'Destination Network Unknown',
            7 : 'Destination Host Unknown',
            8 : 'Source Host Isolated',
            9 : 'Communication with Destination Network is Administratively Prohibited',
            10 : 'Communication with Destination Host is Administratively Prohibited',
            11 : 'Destination Network Unreachable for Type of Service',
            12 : 'Destination Host Unreachable for Type of Service',
            13 : 'Communication Administratively Prohibited',
            14 : 'Host Precedence Violation',
            15 : 'Precedence cutoff in effect'
        },
        11 : {
            0 : 'Time to Live exceeded in Transit',
            1 : 'Fragment Reassembly Time Exceeded'
        }
    }

    # ################################################################################################################ #
    # IcmpHelperLibrary Private Functions                                                                              #
    # ################################################################################################################ #
    def __sendIcmpEchoRequest(self, host):
        print("sendIcmpEchoRequest Started...") if self.__DEBUG_IcmpHelperLibrary else 0

        for i in range(4):
            # Build packet
            icmpPacket = IcmpHelperLibrary.IcmpPacket()

            randomIdentifier = (os.getpid() & 0xffff)      # Get as 16 bit number - Limit based on ICMP header standards
                                                           # Some PIDs are larger than 16 bit

            packetIdentifier = randomIdentifier
            packetSequenceNumber = i

            icmpPacket.buildPacket_echoRequest(packetIdentifier, packetSequenceNumber)  # Build ICMP for IP payload
            icmpPacket.setIcmpTarget(host)
            icmpPacket.sendEchoRequest()                                                # Build IP

            icmpPacket.printIcmpPacketHeader_hex() if self.__DEBUG_IcmpHelperLibrary else 0
            icmpPacket.printIcmpPacket_hex() if self.__DEBUG_IcmpHelperLibrary else 0
            # we should be confirming values are correct, such as identifier and sequence number and data

        # Calculating and displaying RTT statistics
        min_rtt = round(min(IcmpHelperLibrary.roundTripTimes)) if IcmpHelperLibrary.roundTripTimes else 0
        max_rtt = round(max(IcmpHelperLibrary.roundTripTimes)) if IcmpHelperLibrary.roundTripTimes else 0
        # Reference: https://www.geeksforgeeks.org/find-average-list-python/
        avg_rtt = round(sum(IcmpHelperLibrary.roundTripTimes) / len(IcmpHelperLibrary.roundTripTimes)) if IcmpHelperLibrary.roundTripTimes else 0
        
        packet_loss = ((self.sent_packets - self.recv_packets) / self.sent_packets) * 100

        print(f'Ping Complete - Min RTT:{min_rtt} ms, Max RTT: {max_rtt} ms, Avg RTT: {avg_rtt} ms, Packet Loss: {packet_loss} %')

    def __sendIcmpTraceRoute(self, host):
        print("sendIcmpTraceRoute Started...") if self.__DEBUG_IcmpHelperLibrary else 0
        # Build code for trace route here

        trace_counter = 1
        icmpType = -1

        while icmpType != 0:

            icmpPacket = IcmpHelperLibrary.IcmpPacket()
            icmpPacket.setTtl(trace_counter)

            packetIdentifier = (os.getpid() & 0xffff)
            packetSequenceNumber = trace_counter

            icmpPacket.buildPacket_echoRequest(packetIdentifier, packetSequenceNumber)
            icmpPacket.setIcmpTarget(host)
            icmpType = icmpPacket.sendEchoRequest()

            icmpPacket.printIcmpPacketHeader_hex() if self.__DEBUG_IcmpHelperLibrary else 0
            icmpPacket.printIcmpPacket_hex() if self.__DEBUG_IcmpHelperLibrary else 0

            trace_counter += 1
            time.sleep(2)

    # ################################################################################################################ #
    # IcmpHelperLibrary Public Functions                                                                               #
    # ################################################################################################################ #
    def sendPing(self, targetHost):
        print("ping Started...") if self.__DEBUG_IcmpHelperLibrary else 0
        self.__sendIcmpEchoRequest(targetHost)

    def traceRoute(self, targetHost):
        print("traceRoute Started...") if self.__DEBUG_IcmpHelperLibrary else 0
        self.__sendIcmpTraceRoute(targetHost)


# #################################################################################################################### #
# main()                                                                                                               #
# #################################################################################################################### #
def main():
    icmpHelperPing = IcmpHelperLibrary()

    
    # Choose one of the following by uncommenting out the line
    # Google
    # icmpHelperPing.sendPing("www.google.com")
    # icmpHelperPing.traceRoute("www.google.com") 

    # UMass Amherst
    # icmpHelperPing.sendPing("gaia.cs.umass.edu")
    # icmpHelperPing.traceRoute("gaia.cs.umass.edu")        
    
    # This site was referenced to find and test international addresses: https://myip.ms/

    # Proton (Switzerland IP) 185.70.42.21
    #icmpHelperPing.sendPing("www.proton.ch")
    #icmpHelperPing.traceRoute("www.proton.ch")

    # Sakura Internet (Japan)
    icmpHelperPing.sendPing("www.sakura.ne.jp")
    #icmpHelperPing.traceRoute("www.sakura.ne.jp")
    

if __name__ == "__main__":
    main()
