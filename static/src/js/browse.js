odoo.define('oovideo.Browse', function (require) {
'use strict';

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;


var Browse = Widget.extend({
    events: {
        'click .oov_folder': 'openFolder',
        'click .oov_media': 'mediaPlayer',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.folder_id = action.context.folder_id || false;
        this.folder_data = action.context.folder_data || {}; // Used to cache requests
    },

    willStart: function () {
        return this.browse();
    },

    start: function() {
        // Render now, since events don't work when using the 'template' attribute.
        this.$el.html(QWeb.render('oovideo.Browse', {widget: this}));
        return this._super.apply(this, arguments);
    },

    browse: function () {
        var self = this;
        // Get folder data in the cache is available, otherwise request from the server
        if (this.folder_data[this.folder_id]) {
            return $.when();
        } else {
            return new Model('oovideo.folder').call('oovideo_browse', [self.folder_id]).then(function (data) {
                var tmp_data = {};
                tmp_data[self.folder_id] = JSON.parse(data);
                _.extend(self.folder_data, tmp_data);
            });
        }
    },

    openFolder: function (ev) {
        this.do_action({
            type: 'ir.actions.client',
            tag: 'oovideo_browse',
            name: _t('Browse Files'),
            context: {
                folder_id: $(ev.target).data('id'),
                folder_data: this.folder_data,
            },
        });
    },

    mediaPlayer: function (ev) {
        this.do_action({
            type: 'ir.actions.client',
            tag: 'oovideo_media_player',
            name: _t('Media Player'),
            context: {
                folder_id: this.folder_id,
                folder_data: this.folder_data,
                media_id: $(ev.target).data('id'),
            },
        });
    },
});

core.action_registry.add('oovideo_browse', Browse);
return {
    Browse: Browse,
};
});
