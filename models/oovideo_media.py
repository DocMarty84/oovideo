# -*- coding: utf-8 -*-

import ast
import glob
import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from odoo import fields, models, _
from oovideo_transcoder import BR_LIST, RES_LIST

class VideoMedia(models.Model):
    _name = 'oovideo.media'
    _description = 'Video Media'
    _order = 'name'

    name = fields.Char('Title', required=True, index=True)
    duration = fields.Integer('Duration')
    height = fields.Integer('Heigth')
    width = fields.Integer('Width')
    bitrate = fields.Integer('Bitrate')
    audio_tracks = fields.Integer('# Audio Tracks')
    audio_tracks_lang = fields.Char('Audio Tracks Languages')
    path = fields.Char('Path', required=True, index=True)
    last_modification = fields.Integer('Last Modification')
    root_folder_id = fields.Many2one(
        'oovideo.folder', string='Root Folder', required=True, ondelete='cascade')
    folder_id = fields.Many2one(
        'oovideo.folder', string='Folder', required=True, ondelete='cascade')

    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )

    def oovideo_media_info(self):
        self.ensure_one()
        res_list = [_('Original')]
        res_list += [
            k for k, v in RES_LIST.items()
            if int(v.split('x')[0]) <= self.width or int(v.split('x')[1]) <= self.height
        ]
        br_list = [self.bitrate] + [b for b in BR_LIST if b <= self.bitrate]
        os.chdir(self.folder_id.path)
        return {
            'name': self.name,
            'height': self.height,
            'width': self.width,
            'audio_tracks_lang': ast.literal_eval(self.audio_tracks_lang),
            'br_list': br_list,
            'res_list': res_list,
            'sub_list': [
                os.path.basename(f) for f in glob.glob(os.path.splitext(self.path)[0] + '*.srt')
            ]
        }

    def oovideo_stream(self, **kwargs):
        self.ensure_one()
        bitrate = kwargs.get('br', '500')
        resolution = kwargs.get('res', '360p')
        if resolution not in RES_LIST.keys():
            resolution = str(self.width) + 'x' + str(self.height)
        else:
            resolution = RES_LIST[resolution]
        lang = kwargs.get('lang', 1)
        res = StringIO()
        res.write('#EXTM3U\n')
        res.write('#EXT-X-VERSION:1\n')
        res.write('#EXT-X-TARGETDURATION:10\n')
        total_duration = self.duration / 1000
        remaining_duration = total_duration
        while remaining_duration > 0:
            seek = total_duration - remaining_duration
            remaining_duration -= 10
            duration = 10 if remaining_duration >= 0 else remaining_duration + 10
            res.write('#EXTINF:%s,\n' % (duration))
            res.write(
                '/oovideo/trans/%s.ts?seek=%s&dur=%s&br=%s&res=%s&lang=%s\n'\
                % (self.id, seek, duration, bitrate, resolution, lang)
            )
        res.write('#EXT-X-ENDLIST')
        res.seek(0)
        return res
