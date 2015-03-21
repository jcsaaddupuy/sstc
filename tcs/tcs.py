# -*- coding: utf-8 -*-

import os
import threading

import libtorrent as lt

import socket

import logging
logger = logging.getLogger(__name__)


class TcError(Exception):
    pass


class TcDeadProxyError(TcError):
    pass



class TorrentClient(object):

    def __init__(self,
                 download_path='./',
                 port_in=6881,
                 port_out=6891,

                 proxy_type=None,
                 proxy_host=None,
                 proxy_port=None,

                 anonymous_mode=False
                 ):

        self.download_path = download_path
        self.session = lt.session()
        self.session.listen_on(port_in, port_out)
        self.session.set_alert_mask(
                lt.alert.category_t.storage_notification +
                lt.alert.category_t.status_notification +
                lt.alert.category_t.progress_notification
        )

        self.proxy_type = proxy_type
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

        # if self.is_proxy_alive(proxy_host, proxy_port):
        self.check_proxy()
        self.configure_proxy()
        self.configure(anonymous_mode)

        self.alert_handlers = {}

        self._loop_thread = threading.Thread(target=self._loop)
        self.e_stop = threading.Event()

    def configure(self, anonymous_mode):
        settings = lt.session_settings()
        settings.anonymous_mode = anonymous_mode
        self.session.set_settings(settings)

    def configure_proxy(self, proxy_type=None, proxy_host=None, proxy_port=None):
        proxy_type = proxy_type or self.proxy_type
        proxy_host = proxy_host or self.proxy_host
        proxy_port = proxy_port or self.proxy_port

        if proxy_port and proxy_host:

            proxy_settings = lt.proxy_settings()
            proxy_settings.type = proxy_type
            proxy_settings.hostname = proxy_host
            proxy_settings.port = proxy_port

            self.session.set_proxy(proxy_settings)
            self.session.set_dht_proxy(proxy_settings)
            self.session.set_peer_proxy(proxy_settings)
            self.session.set_tracker_proxy(proxy_settings)
            self.session.set_web_seed_proxy(proxy_settings)

    def is_proxy_alive(self, proxy_host=None, proxy_port=None):
        proxy_host = proxy_host or self.proxy_host
        proxy_port = proxy_port or self.proxy_port

        if proxy_port is not None and proxy_host is not None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((proxy_host, proxy_port))
            sock.close()
            return result == 0
        # no proxy : direct connection -> True
        return True

    def check_proxy(self, proxy_host=None, proxy_port=None):
        proxy_host = proxy_host or self.proxy_host
        proxy_port = proxy_port or self.proxy_port
        if not self.is_proxy_alive(proxy_host, proxy_port):
            raise TcDeadProxyError("Could not connect to proxy")

    def _add_torrent(self, torrent_path, download_path=None):
        e = lt.bdecode(open(torrent_path, 'rb').read())

        info = lt.torrent_info(e)

        params = {
            'save_path': download_path or self.download_path,
            'storage_mode': lt.storage_mode_t.storage_mode_sparse,
            'ti': info
        }

        return self.session.add_torrent(params)

    def _add_magnet(self, magnet, download_path=None):
        params = {
            'save_path': download_path or self.download_path,
            'storage_mode': lt.storage_mode_t.storage_mode_sparse,
        }
        return lt.add_magnet_uri(self.session, magnet, params)

    def add_torrent(self, torrent_path, download_path=None, alert_handler=None):
        torrent_path = os.path.abspath(torrent_path)
        handler = self._add_torrent(torrent_path, download_path)

        self.alert_handlers[handler.name()] = alert_handler

    def add_magnet(self, magnet, download_path=None, alert_handler=None):
        handler = self._add_magnet(magnet, download_path)
        self.alert_handlers[handler.name()] = alert_handler

    def add(self, what, download_path=None, alert_handler=None):
        if what.startswith("magnet:"):
            return self.add_magnet(what, download_path, alert_handler)
        elif os.path.isfile(what):
            return self.add_torrent(what, download_path, alert_handler)
        else:
            raise ValueError("%s not usable", what)

    def stop(self):
        self.e_stop.set()
        if self._loop_thread.start != threading.currentThread():
            self._loop_thread.join()

    def _loop(self):
        while not self.e_stop.isSet():
            self.session.wait_for_alert(500)
            alert = self.session.pop_alert()
            if not alert:
                continue

            handle = getattr(alert, "handle", None)
            if not handle:
                logger.debug("No handle for %s", alert.__class__.__name__)
                continue
            alert_handler = self.alert_handlers.get(alert.handle.name(), None)
            if not alert_handler:
                continue
            m_name = "on_%s" % (alert.__class__.__name__)
            method = getattr(alert_handler, m_name, None)
            if not method:
                #logger.debug("No method for %s", m_name)
                continue
            try:
                method(self.session, alert)
            except Exception:
                logger.exception("Error calling handler")

    def loop(self):
        self._loop_thread.start()

    def __len__(self):
        return len(self.session.get_torrents())
