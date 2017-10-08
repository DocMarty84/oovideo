# -*- coding: utf-8 -*-

from collections import OrderedDict
import datetime
import os
import subprocess

from odoo import fields, models

BR_LIST = [200, 300, 400, 500, 700, 1200, 1500, 1700, 2000, 2500, 3000, 4000, 5000, 6000]
RES_LIST = OrderedDict([
    ('144p', '256x144'),
    ('240p', '426x240'),
    ('360p', '640x360'),
    ('480p', '854x480'),
    ('720p', '1280x720'),
    ('1080p', '1920x1080'),
])


class VideoTranscoder(models.Model):
    _name = 'oovideo.transcoder'
    _description = 'Video Transcoder'
    _order = 'sequence'

    name = fields.Char('Transcoder Name', required=True)
    sequence = fields.Integer(
        default=10,
        help='Sequence used to order the transcoders. The lower the value, the higher the priority')
    command = fields.Char(
        'Command line', required=True,
        help='''Command to execute for transcoding. Specific keywords are automatically replaced:
        - "%i": input file
        - "%s": start from this seek time
        - "%d": duration
        - "%b": birate for output file
        - "%r": resolution for output file
        - "%l": language track
        '''
    )
    bitrate = fields.Integer(
        'Bitrate', required=True,
        help='Default bitrate. Can be changed if necessary when the transcoding function is called'
    )
    input_formats = fields.Many2many(
        'oovideo.format', string='Input Formats', required=True, index=True,
    )
    output_format = fields.Many2one('oovideo.format', string='Output Format', required=True)
    buffer_size = fields.Integer(
        'Buffer Size (KB)', required=True, default=1000,
        help='''Size of the buffer used while streaming. A larger value can reduce the potential
        file download errors when playing.'''
    )

    def transcode(self, media_id, **kwargs):
        '''
        Method used to transcode a track. It takes in charge the replacement of the specific
        keywords of the command, and returns the subprocess executed. The subprocess output is
        redirected to stdout, so it is possible to stream the transcoding result while it is still
        ongoing.
        Extra parameters should be specified:
        - 'seek': start time of the transcoding
        - 'dur': duration to transcode
        - 'br': bitrate for video track of the output file
        - 'res': resolution for video track of the output file
        - 'lang': language track to select

        :param media_id: ID of the media to transcode
        :returns: subprocess redirected to stdout.
        :rtype: subprocess.Popen
        '''
        self.ensure_one()
        seek = int(kwargs.get('seek', 0))
        duration = kwargs.get('dur', '10')
        bitrate = kwargs.get('br', self.bitrate)
        resolution = kwargs.get('res', '640x360')
        lang = kwargs.get('lang', '1')

        media = self.env['oovideo.media'].browse([media_id])
        cmd = self.command\
            .replace('%s', '%s' % (str(datetime.timedelta(seconds=seek))))\
            .replace('%d', '%s' % (duration))\
            .replace('%r', '%s' % (resolution))\
            .replace('%b', '%s' % (bitrate))\
            .replace('%l', '%s' % (lang))
        cmd = cmd.split(' ')
        cmd[cmd.index('%i')] = media.path

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=open(os.devnull, 'w'))
        return proc
