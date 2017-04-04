# Python bittorrent ut_metadata extension
Simple bittorrent protocol implementation for handle "ut_metadata" extension messages.

## Demo
Replace `info_hash` to your own value & enjoy
```python
def print_metadata(metadata):
    print metadata


factory = BitTorrentFactory(info_hash=unhexlify('E4DFB9BC728B5554F81CBF97637F7EA5151BF565'),
                            peer_id=unhexlify('cd2e6673b9f2a21cad1e605fe5fb745b9f7a214d'),
                            on_metadata_loaded=print_metadata)

reactor.connectTCP("127.0.0.1", 16762, factory)
reactor.run()
```
