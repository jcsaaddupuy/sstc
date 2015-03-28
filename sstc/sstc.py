# -*- coding: utf-8 -*-

import os
import time
import threading

import socket

import libtorrent as lt
import requests

import logging
logger = logging.getLogger(__name__)

logger_alerts = logging.getLogger("%s.alert" % __name__)

ALERT_MASK_STORAGE = lt.alert.category_t.storage_notification
ALERT_MASK_STATUS = lt.alert.category_t.status_notification
ALERT_MASK_PROGRESS = lt.alert.category_t.progress_notification
ALERT_MASK_ERROR = lt.alert.category_t.error_notification
ALERT_MASK_STATS = lt.alert.category_t.stats_notification
ALERT_MASK_ALL = lt.alert.category_t.all_categories


class TcError(Exception):
    pass


class TcDeadProxyError(TcError):
    pass


class TorrentClient(object):

    def __init__(self,
                 download_path='./',

                 port_start=6881,
                 port_ends=6891,
                 interface=None,

                 proxy_type=None,
                 proxy_host=None,
                 proxy_port=None,

                 anonymous_mode=False,
                 # session limits
                 download_rate_limit=-1,
                 upload_rate_limit=-1,
                 # per torrents
                 download_limit=-1,
                 upload_limit=-1,
                 user_agent = None,

                 alert_mask = ALERT_MASK_STORAGE | ALERT_MASK_STATUS | ALERT_MASK_STATS | ALERT_MASK_ERROR,
                 ):

        self.download_path = download_path
        self.session = lt.session()
        self.session.listen_on(port_start, port_ends, interface)
        # set session limits
        self.session.set_download_rate_limit(download_rate_limit)
        self.session.set_upload_rate_limit(upload_rate_limit)
        # store per torrent settings
        self.download_limit = download_limit
        self.upload_limit = upload_limit

        self.user_agent = user_agent
        if alert_mask is not None:
            self.session.set_alert_mask(alert_mask)

        self.proxy_type = proxy_type
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

        # if self.is_proxy_alive(proxy_host, proxy_port):
        self.check_proxy()
        self.configure_proxy()
        self.configure(anonymous_mode, user_agent)

        self.alert_handlers = {}

        self._loop_thread = threading.Thread(target=self._loop)
        self.e_stop = threading.Event()

    def configure(self, anonymous_mode, user_agent=None):
        settings = lt.session_settings()
        settings.anonymous_mode = anonymous_mode
        if user_agent:
            settings.user_agent = user_agent
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

    def _add_torrent_content(self, bdecoded, is_paused=False, download_path=None, download_limit=0, upload_limit=0):

        info = lt.torrent_info(bdecoded)

        params = {
            'save_path': download_path or self.download_path,
            'storage_mode': lt.storage_mode_t.storage_mode_sparse,
            'ti': info
        }

        handler = self.session.add_torrent(params)
        handler.set_download_limit(download_limit or self.download_limit)
        handler.set_upload_limit(upload_limit or self.upload_limit)

        if is_paused:
            handler.pause()
        return handler

    def _add_magnet(self, magnet, is_paused=False, download_path=None, download_limit=0, upload_limit=0):
        params = {
            'save_path': download_path or self.download_path,
            'storage_mode': lt.storage_mode_t.storage_mode_sparse,
        }
        handler = lt.add_magnet_uri(self.session, magnet, params)

        handler.set_download_limit(download_limit or self.download_limit)
        handler.set_upload_limit(upload_limit or self.upload_limit)

        if is_paused:
            handler.pause()
        return handler

    def add_torrent(self, torrent_path, alert_handler=None, *args, **kwargs):
        torrent_path = os.path.abspath(torrent_path)
        bdecoded = lt.bdecode(open(torrent_path, 'rb').read())
        handler = self._add_torrent_content(bdecoded, *args, **kwargs)
        self.alert_handlers[handler.name()] = alert_handler
        logger.info("Added %s", handler.name())

    def add_magnet(self, magnet, alert_handler=None, *args, **kwargs):
        handler = self._add_magnet(magnet, *args, **kwargs)
        self.alert_handlers[handler.name()] = alert_handler
        logger.info("Added %s", handler.name())

    def add_url(self, url, alert_handler, *args, **kwargs):
        if self.user_agent:
            headers = {
                'User-Agent': self.user_agent,
            }
            resp = requests.get(url, headers=headers)
        else:
            resp = requests.get(url)

        bdecoded = lt.bdecode(resp.content)
        handler = self._add_torrent_content(bdecoded, *args, **kwargs)
        self.alert_handlers[handler.name()] = alert_handler
        logger.info("Added %s", handler.name())

    def add(self, what, alert_handler=None, *args, **kwargs):
        if what.startswith("magnet:"):
            return self.add_magnet(
                what,
                alert_handler=alert_handler,
                *args,
                **kwargs
            )
        elif os.path.isfile(what):
            return self.add_torrent(
                what,
                alert_handler=alert_handler,
                *args,
                **kwargs
            )
        elif what.startswith("http://") or what.startswith("https://"):
            return self.add_url(
                what,
                alert_handler=alert_handler,
                *args,
                **kwargs
            )
        else:
            raise ValueError("%s not usable", what)

    def stop(self):
        logger.info("Stopping")
        self.e_stop.set()
        for handler in self.session.get_torrents():
            try:
                self.session.remove_torrent(handler, option=1)
            except Exception as e:
                logger.error("Could not remove torrent : %s", getattr(e, 'message', 'Unkown error'))

        if self._loop_thread.start != threading.currentThread():
            self._loop_thread.join()

    def _loop(self):
        while not self.e_stop.isSet():
            self.session.wait_for_alert(500)
            alert = self.session.pop_alert()
            if not alert:
                continue

            if type(alert) is lt.alert:
                logger.debug(alert.what())
                continue

            handle = getattr(alert, "handle", None)
            if not handle:
                logger_alerts.debug("No handle for %s", alert.__class__.__name__)
                continue
            alert_handler = self.alert_handlers.get(alert.handle.name(), None)
            if not alert_handler:
                continue
            m_name = "on_%s" % (alert.__class__.__name__)
            method = getattr(alert_handler, m_name, None)
            if not method:
                logger_alerts.debug("%s : No method for %s", handle.name(), m_name)
                continue
            try:
                method(self.session, alert)
            except Exception:
                logger_alerts.exception("Error calling handler")
            finally:
                if type(alert) == lt.torrent_removed_alert:
                    try:
                        del self.alert_handlers[alert.handle.name()]
                        logger.debug("Handler for %s removed", alert.handle.name())
                    except KeyError:
                        pass

    def start(self):
        logger.info("Starting")
        self._loop_thread.start()

    def loop(self):
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, Exception):
            self.stop()

    def __len__(self):
        return len(self.session.get_torrents())
