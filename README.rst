===============================
Stupid, simple torrent client
===============================

.. image:: https://img.shields.io/travis/jcsaaddupuy/sstc.svg
        :target: https://travis-ci.org/jcsaaddupuy/sstc

.. image:: https://img.shields.io/pypi/v/sstc.svg
        :target: https://pypi.python.org/pypi/sstc


Stupid, simple torrent client built on top of libtorrent python binding.

Let you add torrents files and magnet and receive libtorrent alerts. That's all !

Full example :

.. code-block:: python

    # coding: utf-8
    import sys
    import os
    import time
    import logging

    from sstc.sstc import TorrentClient

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)


    class AlertHandler(object):
        def on_torrent_added_alert(self, session, alert):
            logger.debug("on_torrent_added_alert")

        def on_state_changed_alert(self, session, alert):
            logger.debug("on_state_changed_alert")
            logger.debug(alert.message())

        def on_torrent_resumed_alert(self, session, alert):
            logger.debug("on_torrent_resumed_alert")

        def on_torrent_checked_alert(self, session, alert):
            logger.debug("on_torrent_checked_alert")
            handler = alert.handle
            info = handler.get_torrent_info()
            files = info.files()
            # Do something with torrent infos, like filter files to download
            handler.resume()

        def on_torrent_finished_alert(self, session, alert):
            logger.debug("on_torrent_finished_alert")
            session.remove_torrent(handler)

        def on_piece_finished_alert(self, session, alert):
            logger.debug("on_torrent_finished_alert")
            handler = alert.handle

        def on_block_finished_alert(self, session, alert):
            logger.debug("on_block_finished_alert")
            handler = alert.handle

        def on_file_completed_alert(self, session, alert):
            logger.debug("on_file_completed_alert")
            handler = alert.handle
            info = handler.get_torrent_info()
            f = info.file_at(alert.index)
            logger.debug("%s : completed", f.path)

    def main():
        client = TorrentClient()
        client.loop()
        # use big buck bunny magnet
        magnet ="magnet:?xt=urn:btih:0E876CE2A1A504F849CA72A5E2BC07347B3BC957&dn=big+buck+bunny+720p+psiclone&tr=udp%3A%2F%2Fopen.demonii.com%3A1337%2Fannounce"

        try:
            client.add(magnet, is_paused=True, alert_handler=AlertHandler(imdb))
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, Exception) as e:
            client.stop()

    if __name__ == "__main__":
        main()
```

* Free software: BSD license
* Documentation: https://sstc.readthedocs.org.

Features
--------

* TODO
