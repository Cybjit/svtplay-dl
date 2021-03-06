# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import copy
import xml.etree.ElementTree as ET

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, is_py2_old
from svtplay_dl.utils.urllib import unquote_plus
from svtplay_dl.log import log
from svtplay_dl.fetcher.rtmp import RTMP

class Qbrick(Service, OpenGraphThumbMixin):
    supported_domains = ['di.se', 'sydsvenskan.se']

    def get(self, options):
        if re.findall(r"sydsvenskan.se", self.url):
            data = self.get_urldata()
            match = re.search(r"data-qbrick-mcid=\"([0-9A-F]+)\"", data)
            if not match:
                log.error("Can't find video file")
                sys.exit(2)
            mcid = match.group(1)
            host = "http://vms.api.qbrick.com/rest/v3/getsingleplayer/%s" % mcid
        elif re.findall(r"di.se", self.url):
            data = self.get_urldata()
            match = re.search("src=\"(http://qstream.*)\"></iframe", data)
            if not match:
                log.error("Can't find video info")
                sys.exit(2)
            data = get_http_data(match.group(1))
            match = re.search(r"data-qbrick-ccid=\"([0-9A-Z]+)\"", data)
            if not match:
                log.error("Can't find video file")
                sys.exit(2)
            host = "http://vms.api.qbrick.com/rest/v3/getplayer/%s" % match.group(1)
        elif re.findall(r"svd.se", self.url):
            match = re.search(r'video url-([^"]*)\"', self.get_urldata())
            if not match:
                log.error("Can't find video file")
                sys.exit(2)
            path = unquote_plus(match.group(1))
            data = get_http_data("http://www.svd.se%s" % path)
            match = re.search(r"mcid=([A-F0-9]+)\&width=", data)
            if not match:
                log.error("Can't find video file")
                sys.exit(2)
            host = "http://vms.api.qbrick.com/rest/v3/getsingleplayer/%s" % match.group(1)
        else:
            log.error("Can't find site")
            sys.exit(2)

        data = get_http_data(host)
        xml = ET.XML(data)
        try:
            url = xml.find("media").find("item").find("playlist").find("stream").find("format").find("substream").text
        except AttributeError:
            log.error("Can't find video file")
            sys.exit(2)
        live = xml.find("media").find("item").find("playlist").find("stream").attrib["isLive"]
        if live == "true":
            options.live = True
        data = get_http_data(url)
        xml = ET.XML(data)
        server = xml.find("head").find("meta").attrib["base"]
        streams = xml.find("body").find("switch")
        if is_py2_old:
            sa = list(streams.getiterator("video"))
        else:
            sa = list(streams.iter("video"))

        for i in sa:
            options.other = "-y '%s'" % i.attrib["src"]
            yield RTMP(copy.copy(options), server, i.attrib["system-bitrate"])
