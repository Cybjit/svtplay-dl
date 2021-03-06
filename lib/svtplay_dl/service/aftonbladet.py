# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import json
import copy

from svtplay_dl.service import Service
from svtplay_dl.utils import get_http_data
from svtplay_dl.log import log
from svtplay_dl.fetcher.hls import HLS, hlsparse

class Aftonbladet(Service):
    supported_domains = ['tv.aftonbladet.se']

    def get(self, options):
        data = self.get_urldata()
        match = re.search('data-aptomaId="([-0-9a-z]+)"', data)
        if not match:
            log.error("Can't find video info")
            sys.exit(2)
        videoId = match.group(1)
        match = re.search(r'data-isLive="(\w+)"', data)
        if not match:
            log.error("Can't find live info")
            sys.exit(2)
        if match.group(1) == "true":
            options.live = True
        if not options.live:
            dataurl = "http://aftonbladet-play-metadata.cdn.drvideo.aptoma.no/video/%s.json" % videoId
            data = get_http_data(dataurl)
            data = json.loads(data)
            videoId = data["videoId"]

        streamsurl = "http://aftonbladet-play-static-ext.cdn.drvideo.aptoma.no/actions/video/?id=%s&formats&callback=" % videoId
        streams = json.loads(get_http_data(streamsurl))
        hlsstreams = streams["formats"]["hls"]
        playlist = False
        if "level3" in hlsstreams.keys():
            hls = hlsstreams["level3"]
        else:
            hls = hlsstreams["akamai"]
        if "csmil" in hls.keys():
            hls = hls["csmil"][0]
        else:
            hls = hls["m3u8"][0]
            playlist = True
        address = hls["address"]
        path = hls["path"]

        for i in hls["files"]:
            if "filename" in i.keys():
                plist = "http://%s/%s/%s/master.m3u8" % (address, path, i["filename"])
            else:
                plist = "http://%s/%s/%s" % (address, path, hls["filename"])
            if playlist:
                streams = hlsparse(plist)
                log.info("streams %r", streams)
                for n in list(streams.keys()):
                    yield HLS(copy.copy(options), streams[n], n)
            else:
                yield HLS(copy.copy(options), plist, i["bitrate"])
