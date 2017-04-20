# -*- coding: utf-8 -*-
{
    'name': 'OOVideo',
    'author': 'Nicolas Martinelli',
    'category': 'Uncategorized',
    'summary': 'Video streaming module',
    'website': 'https://koozic.net/',
    'version': '0.1',
    'description': """
Video Collection
================

        """,
    'depends': [
        'base',
        'web',
        'web_tour',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/oovideo_security.xml',

        'views/oovideo_menu_views.xml',
        'views/oovideo_folder_views.xml',
        'views/oovideo_media_views.xml',
        'views/oovideo_transcoder_views.xml',
        'views/oovideo.xml',
        'views/tour_views.xml',

        'data/oovideo_folder_data.xml',
        'data/oovideo_format_data.xml',
        'data/oovideo_transcoder_data.xml',
    ],
    'demo': [
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': True,
    'license': 'Other OSI approved licence',
}
