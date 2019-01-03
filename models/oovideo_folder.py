# -*- coding: utf-8 -*-

import json
import logging
import os

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class VideoFolder(models.Model):
    _name = 'oovideo.folder'
    _description = 'Video Folder'
    _order = 'path'

    name = fields.Char('Name')
    root = fields.Boolean('Top Level Folder', default=True)
    path = fields.Char('Folder Path', required=True, index=True)
    exclude_autoscan = fields.Boolean(
        'No auto-scan', default=False,
        help='Exclude this folder from the automatized scheduled scan. Useful if the folder is not '
        'always accessible, e.g. linked to an external drive.'
    )
    last_scan = fields.Datetime('Last Scanned')
    last_scan_duration = fields.Integer('Scan Duration (s)')
    parent_id = fields.Many2one('oovideo.folder', string='Parent Folder', ondelete='cascade')
    child_ids = fields.One2many('oovideo.folder', 'parent_id', string='Child Folders')
    media_ids = fields.One2many('oovideo.media', 'folder_id', string='Media')
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )
    last_modification = fields.Integer('Last Modification')
    locked = fields.Boolean(
        'Locked', default=False,
        help='When a folder is being scanned, it is flagged as "locked". It might be necessary to '
        'unlock it manually if scanning has failed or has been interrupted.')
    root_preview = fields.Text('Preview Folder Content', compute='_compute_root_preview')
    path_name = fields.Char('Folder Name', compute='_compute_path_name')

    _sql_constraints = [
        ('oovideo_folder_path_uniq', 'unique(path, user_id)', 'Folder path must be unique!'),
    ]

    @api.depends('path')
    def _compute_root_preview(self):
        ALLOWED_FILE_EXTENSIONS = self.env['oovideo.folder.scan'].ALLOWED_FILE_EXTENSIONS
        for folder in self.filtered(lambda f: f.root and f.path):
            i = 0
            fn_paths = ''
            for rootdir, dirnames, filenames in os.walk(folder.path):
                ii = 0
                for fn in filenames:
                    print(fn)
                    # Check file extension
                    fn_ext = fn.split('.')[-1]
                    if fn_ext and fn_ext.lower() not in ALLOWED_FILE_EXTENSIONS:
                        continue

                    fn_paths += '{}\n'.format(os.path.join(rootdir.replace(folder.path, ''), fn))
                    i += 1
                    ii += 1
                    if ii > 3:
                        fn_paths += '...\n'
                        break
                if i > 30:
                    break
            if not fn_paths:
                fn_paths = _('No track found')
            folder.root_preview = fn_paths

    @api.depends('path')
    def _compute_path_name(self):
        for folder in self:
            if folder.root:
                folder.path_name = folder.path
            else:
                folder.path_name = folder.path.split(os.sep)[-1]

    @api.model
    def create(self, vals):
        if 'path' in vals and vals.get('root', True):
            vals['path'] = os.path.normpath(vals['path'])
        return super(VideoFolder, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'path' in vals:
            vals['path'] = os.path.normpath(vals['path'])
            folders = self | self.search([('id', 'child_of', self.ids)])
            folders.write({'last_modification': 0})
            tracks = folders.mapped('media_ids')
            tracks.write({'last_modification': 0})
        return super(VideoFolder, self).write(vals)

    @api.multi
    def action_scan_folder(self):
        '''
        This is the main method used to scan a oovideo folder. It creates a thread with the scanning
        process.
        '''
        folder_id = self.id
        if folder_id:
            self.env['oovideo.folder.scan'].scan_folder_th(folder_id)

    @api.multi
    def action_scan_folder_full(self):
        '''
        This is a method used to force a full scan of a folder.
        '''
        folder_id = self.id
        if folder_id:
            # Set the last modification date to zero so we force scanning all folders and files
            folders = self.env['oovideo.folder'].search([('id', 'child_of', folder_id)]) | self
            folders.sudo().write({'last_modification': 0})
            media = self.env['oovideo.media'].search([('root_folder_id', '=', folder_id)])
            media.sudo().write({'last_modification': 0})
            self.env.cr.commit()
            self.env['oovideo.folder.scan'].scan_folder_th(folder_id)

    @api.model
    def cron_scan_folder(self):
        for folder in self.search([('root', '=', True), ('exclude_autoscan', '=', False)]):
            try:
                self.env['oovideo.folder.scan']._scan_folder(folder.id)
            except:
                _logger.info('Error while scanning folder ID %s', folder.id)
                continue

    @api.multi
    def oovideo_browse(self):
        res = {}
        if self.root or self.parent_id:
            res['parent_id'] =\
                {'id': self.parent_id.id, 'name': self.path_name or ''}
        if self:
            res['current_id'] = {'id': self.id, 'name': self.path}
            res['child_ids'] = [
                {'id': c.id, 'name': c.path_name} for c in self.child_ids
            ]
        else:
            res['child_ids'] = [
                {'id': c.id, 'name': c.path_name} for c in self.search([('root', '=', True)])
            ]
        res['media_ids'] = [
            {'id': t.id, 'name': t.path.split(os.sep)[-1]}
            for t in self.media_ids.sorted(key='path')
        ]

        return json.dumps(res)
