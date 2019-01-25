# -*- coding: utf-8 -*-

import logging
import os
from tempfile import NamedTemporaryFile

from werkzeug.exceptions import NotFound
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

from odoo import http
from odoo.http import request

try:
    from webvtt import webvtt
except ImportError:
    webvtt = None


_logger = logging.getLogger(__name__)


class VideoController(http.Controller):
    @http.route(['/oovideo/stream/<int:media_id>.<string:vformat>'], type='http', auth='user')
    def stream(self, media_id, vformat, **kwargs):
        media = request.env['oovideo.media'].browse([media_id])
        if vformat == 'mp4':
            return http.send_file(media.path, as_attachment=True)
        generator = media.oovideo_stream(**kwargs)
        data = wrap_file(request.httprequest.environ, generator)
        return Response(data, mimetype='application/x-mpegurl', direct_passthrough=True)

    @http.route(['/oovideo/trans/<int:media_id>.ts'], type='http', auth='user')
    def trans(self, media_id, **kwargs):
        transcoder = request.env['oovideo.transcoder'].env.ref('oovideo.oovideo_transcoder_0')
        generator = transcoder.transcode(media_id, **kwargs).stdout
        mimetype = transcoder.output_format.mimetype

        data = wrap_file(request.httprequest.environ, generator)
        return Response(data, mimetype=mimetype, direct_passthrough=True)

    @http.route(['/oovideo/sub/<int:media_id>'], type='http', auth='user')
    def sub(self, media_id, **kwargs):
        media = request.env['oovideo.media'].browse([media_id])
        sub = os.path.join(media.folder_id.path, kwargs.get('sub', '').split(os.sep)[-1])
        if os.path.isfile(sub):
            with NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as sub_tmp:
                sub_send = sub_tmp.name
                sub_ext = os.path.splitext(sub)[1]
                if sub_ext == '.srt' and webvtt:
                    webvtt.WebVTT().from_srt(sub).write(sub_tmp)
                elif sub_ext == '.sbv' and webvtt:
                    webvtt.WebVTT().from_sbv(sub).write(sub_tmp)
                elif sub_ext == '.vtt':
                    sub_send = sub
                else:
                    raise NotFound()
                return http.send_file(sub_send, mimetype='text/vtt')
        raise NotFound()
