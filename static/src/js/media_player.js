odoo.define('oovideo.MediaPlayer', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var QWeb = core.qweb;
var _t = core._t;


var MediaPlayer = AbstractAction.extend({
    events: {
        'click .oov_folder': '_onClickFolder',
        'click .oov_reload': '_onClickReload',
        'change .oov_raw': '_onChangeRaw',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.folder_id = action.context.folder_id || false;
        this.folder_data = action.context.folder_data || {};
        this.media_id = action.context.media_id || false;
    },

    willStart: function () {
        var self = this;
        return this._rpc({
                model: 'oovideo.media',
                method: 'oovideo_media_info',
                args: [self.media_id],
            })
            .then(function (data) {
                self.media_info = data;
            });
    },

    start: function () {
        // Render now, since events don't work when using the 'template' attribute.
        this.$el.html(QWeb.render('oovideo.MediaPlayer', {widget: this}));
        this._initPlaybackData();
        this._initClappr();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _initPlaybackData: function () {
        this.bitrate = _.contains(this.media_info.br_list, 500) ? 500 : this.media_info.br_list[0];
        this.$('.oov_br').val(String(this.bitrate))
        this.resolution = _.contains(this.media_info.res_list, '360p') ? '360p' : 'orig';
        this.$('.oov_res').val(this.resolution !== 'orig' ? this.resolution : this.media_info.res_list[0])
        this.lang = this.media_info.audio_tracks_lang && this.media_info.audio_tracks_lang[0] || '0';
        this.$('.oov_lang').val(this.lang);
    },

    _initClappr: function () {
        this.playerElement = this.$('#player-wrapper');
        this.player = new Clappr.Player({
            source: this._makeSourceURL(),
            autoPlay: true,
            chromeless: this.media_info.sub_list.length > 0 ? true : false,
            playback: {
                preload: 'auto',
                controls: this.media_info.sub_list.length > 0 ? true : false,
                playInline: true,
                recycleVideo: Clappr.Browser.isMobile,
                externalTracks: this.media_info.sub_list,
              }

        });
        this.player.attachTo(this.playerElement[0]);
    },

    _makeSourceURL: function () {
        return '/oovideo/stream/' + String(this.media_id) + (this.raw ? '.mp4' : '.m3u8')
            + '?br=' + String(this.bitrate)
            + '&res=' + this.resolution
            + '&lang=' + this.lang.split(':')[0];
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickFolder: function (ev) {
        this.do_action({
            type: 'ir.actions.client',
            tag: 'oovideo_browse',
            name: _t('Browse Files'),
            context: {
                folder_id: this.folder_id,
                folder_data: this.folder_data,
            },
        });
    },

    _onClickReload: function (ev) {
        this.bitrate = this.$('.oov_br').val();
        this.resolution = this.$('.oov_res').val()
        this.resolution = this.resolution !== this.media_info.res_list[0] ? this.resolution : 'orig';
        this.lang = this.$('.oov_lang').val();
        this.raw = this.$('.oov_raw').is(':checked');
        this.player.destroy();
        this._initClappr();
    },

    _onChangeRaw: function (ev) {
        if (this.$('.oov_raw').is(':checked')) {
            this.$('.oov_br,.oov_res,.oov_lang').attr('disabled', true);
        } else {
            this.$('.oov_br,.oov_res,.oov_lang').removeAttr('disabled');
        }
    },

});

core.action_registry.add('oovideo_media_player', MediaPlayer);
return {
    MediaPlayer: MediaPlayer,
};
});
