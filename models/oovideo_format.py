# -*- coding: utf-8 -*-

from odoo import fields, models


class VideoFormat(models.Model):
    _name = 'oovideo.format'
    _description = 'Video Format'
    _order = 'name'

    name = fields.Char('Format', required=True, index=True)
    mimetype = fields.Char('Mimetype', required=True)
    browser_support = fields.Boolean('Supported by browser', default=False)

    _sql_constraints = [
        ('oovideo_format_name_uniq', 'unique(name)', 'Format name must be unique!'),
    ]
