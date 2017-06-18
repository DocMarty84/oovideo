# -*- coding: utf-8 -*-

import logging
import os

from werkzeug.exceptions import NotFound
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

from odoo import http
from odoo.http import request

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

    @http.route(['/oovideo/sub/<int:media_id>.srt'], type='http', auth='user')
    def sub(self, media_id, **kwargs):
        media = request.env['oovideo.media'].browse([media_id])
        sub = media.folder_id.path + os.sep + kwargs.get('sub', '')
        if os.path.isfile(sub):
            return http.send_file(sub, mimetype='application/x-subrip')
        raise NotFound()
