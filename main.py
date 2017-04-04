from struct import pack, unpack
from binascii import unhexlify
from bencode import bencode, bdecode, decode_dict
from time import sleep
from twisted.internet import protocol, reactor, defer


class BitTorrentClient(protocol.Protocol):
    def __init__(self, info_hash, peer_id, on_metadata_loaded):
        self._info_hash = info_hash
        self._peer_id = peer_id

        self._read_handshake = True
        self._metadata = {}

        self._deferred = defer.Deferred()
        self._deferred.addCallback(on_metadata_loaded)

    @staticmethod
    def parseMessage(message):
        # Return message code and message data
        return (unpack("B", message[:1])[0], message[1:])

    def sendExtendedMessage(self, message_id, message_data):
        buf = pack("BB", 20, message_id) + bencode(message_data)

        self.transport.write(pack("!I", len(buf)) + buf)

    def handleMessage(self, msg_code, msg_data):
        if msg_code == 20:
            # Extended handshake
            if ord(msg_data[0]) == 0:
                hs_data = bdecode(msg_data[1:])

                assert "metadata_size" in hs_data and "m" in hs_data and "ut_metadata" in hs_data["m"]

                metadata_size = hs_data["metadata_size"]
                ut_metadata_id = hs_data['m']['ut_metadata']

                hs_response = {'e': 0,
                               'metadata_size': hs_data["metadata_size"],
                               'v': '\xce\xbcTorrent 3.4.9',
                               'm': {'ut_metadata': 1},
                               'reqq': 255}

                # Response extended handshake
                self.sendExtendedMessage(0, hs_response)

                sleep(0.5)

                # Request metadata
                for i in range(0, 1 + metadata_size / (16 * 1024)):
                    self.sendExtendedMessage(ut_metadata_id, {"msg_type": 0, "piece": i})
                    sleep(0.05)

            elif ord(msg_data[0]) == 1:
                r, l = decode_dict(msg_data[1:], 0)

                if r['msg_type'] == 1:
                    self._metadata[r['piece']] = msg_data[l + 1:]

                    if sum(map(len, self._metadata.values())) == r['total_size']:
                        reactor.callLater(0, self._deferred.callback, self._metadata)
                        self.transport.loseConnection()

    def connectionMade(self):
        # Send handshake
        bp = list('BitTorrent protocol')
        self.transport.write(pack('B19c', 19, *bp))
        self.transport.write(unhexlify('0000000000100005'))
        self.transport.write(self._info_hash)
        self.transport.write(self._peer_id)

    def dataReceived(self, data):
        buf = buffer(data)

        if self._read_handshake:
            self._read_handshake = False

            # Skip handshake response
            buf = buf[68:]

        # Read regular message
        while buf:
            msg_len = unpack("!I", buf[:4])[0]

            self.handleMessage(*self.parseMessage(buf[4: msg_len + 4]))

            buf = buf[msg_len + 4:]


class BitTorrentFactory(protocol.ClientFactory):
    protocol = BitTorrentClient

    def __init__(self, info_hash, peer_id, on_metadata_loaded):
        self._info_hash = info_hash
        self._peer_id = peer_id
        self._on_metadata_loaded = on_metadata_loaded

    def buildProtocol(self, addr):
        p = self.protocol(self._info_hash, self._peer_id, self._on_metadata_loaded)
        p.factory = self
        return p

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        reactor.stop()


def print_metadata(metadata):
    print metadata


factory = BitTorrentFactory(unhexlify('E4DFB9BC728B5554F81CBF97637F7EA5151BF565'),
                            unhexlify('cd2e6673b9f2a21cad1e605fe5fb745b9f7a214d'),
                            print_metadata)
reactor.connectTCP("127.0.0.1", 16762, factory)
reactor.run()
