===============================
Stupid, simple torrent client
===============================

.. image:: https://img.shields.io/pypi/v/sstc.svg
        :target: https://pypi.python.org/pypi/sstc


Stupid, simple torrent client built on top of libtorrent python binding.

Let you add torrents files and magnet and receive libtorrent alerts. That's all !

* Free software: WTFPL

Features
--------

* TODO

Full example
-------------
This example show how to add a magnet uri and how to create an alert handler.

Alert handler methods sould be named 'on\_ALERT', with ALERT the type of alert
to handle.

All methods will receive the session as first argument and the alert
as the second.

Please note that this example is not exhaustive.

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
            # torrent was added paused, we resume it
            handler.resume()

        def on_torrent_finished_alert(self, session, alert):
            logger.debug("on_torrent_finished_alert")
            # if you want to remove the torrent immediately :
            #session.remove_torrent(handler)

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
        # starts client with 100Mib/s download limit
        # and 10Mib/s uploadlimit
        client = TorrentClient(
            download_rate_limit=100 << 20,
            upload_rate_limit=10 << 20,
        )

        # start client alert dispatcher
        client.start()

        to_download=[
            # support local torrentfile
            "./big_buck_bunny.torrent"
            # also magnet url
            "magnet:?xt=urn:btih:0E876CE2A1A504F849CA72A5E2BC07347B3BC957&dn=big+buck+bunny+720p+psiclone&tr=udp%3A%2F%2Fopen.demonii.com%3A1337%2Fannounce",
            # also from http/https url
            "http://www.frostclick.com/torrents/video/animation/Big_Buck_Bunny_1080p_surround_frostclick.com_frostwire.com.torrent",
        ]

        try:
            for item in to_download:
                client.add(item, is_paused=True, alert_handler=AlertHandler())

            # Blocking loop
            client.loop()

        except (KeyboardInterrupt, Exception) as e:
            client.stop()

    if __name__ == "__main__":
        main()

