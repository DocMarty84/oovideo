# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.release import version


class VideoConfigSettings(models.TransientModel):
    _name = 'oovideo.config.settings'
    _inherit = 'res.config.settings'

    cron = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Scheduled Actions', help='Activate automatic folder scan and image cache mechanism')
    folder_sharing = fields.Selection([
        ('inactive', 'Inactive (user specific)'),
        ('active', 'Active (shared amongst all users)'),
    ], string='Folder Sharing')
    version = fields.Char('Version', readonly=True)

    @api.model
    def get_values(self):
        res = super(VideoConfigSettings, self).get_values()
        cron = (
            self.env.ref('oovideo.oovideo_scan_folder')
        ).mapped('active')
        folder_sharing = (
            self.env.ref('oovideo.oovideo_folder') +
            self.env.ref('oovideo.oovideo_media')
        ).mapped('perm_read')
        res['cron'] = 'active' if all([c for c in cron]) else 'inactive'
        res['folder_sharing'] = 'inactive' if all([c for c in folder_sharing]) else 'active'
        res['version'] = version
        return res

    def set_values(self):
        super(VideoConfigSettings, self).set_values()
        # Activate/deactive ir.cron
        (
            self.env.ref('oovideo.oovideo_scan_folder')
        ).write({'active': bool(self.cron == 'active')})
        # Set folder sharing
        (
            self.env.ref('oovideo.oovideo_folder') +
            self.env.ref('oovideo.oovideo_media')
        ).write({'perm_read': bool(self.folder_sharing == 'inactive')})
