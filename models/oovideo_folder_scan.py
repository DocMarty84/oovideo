# -*- coding: utf-8 -*-

import logging
import os
import threading
from datetime import datetime as dt

from odoo import _, api, fields, models

from .pymediainfo import MediaInfo

_logger = logging.getLogger(__name__)


class VideoFolderScan(models.TransientModel):
    _name = "oovideo.folder.scan"
    _description = "Video Folder Scan"

    ALLOWED_FILE_EXTENSIONS = {"avi", "m4v", "mkv", "mov", "mp4", "mpg", "webm"}

    def _lock_folder(self, folder_id):
        """
        Check if a folder is locked. If it is not locked, lock it. If it is locked, log an error.

        :param int folder_id: ID of the folder to scan
        :return bool: False if the folder was already locked, True if it was not
        """
        Folder = self.env["oovideo.folder"].browse([folder_id])
        if Folder.locked:
            _logger.error('"%s" is locked! It probably means that a scan is ongoing.', Folder.path)
            res = False
        else:
            Folder.write({"locked": True})
            res = True

        self.env.cr.commit()
        return res

    def _clean_directory(self, path, user_id):
        """
        Clean a directory. It removes folders and media which are not on the disk anymore. This
        can potentially deletes the folder linked to the given path if the path doesn't exist
        anymore.

        :param str path: path of the folder to clean
        :param int user_id: ID of the user to whom belongs the folder
        """
        _logger.debug('Cleaning folder "%s"...', path)

        # List existing directories and files
        filelist = set(" ")
        folderlist = set(" ")
        for rootdir, dirnames, filenames in os.walk(path):
            folderlist.add(rootdir)
            for fn in filenames:
                fn_ext = fn.split(".")[-1]
                if fn_ext and fn_ext.lower() in self.ALLOWED_FILE_EXTENSIONS:
                    filelist.add(os.path.join(rootdir, fn))

        track_data = [
            (("id", "path"), "oovideo_folder", folderlist),
            (("id", "path"), "oovideo_media", filelist),
        ]

        # Cleaning part:
        # - select existing paths in table
        # - compare with paths actually used
        # - deletes the ones which are not used anymore
        for td in track_data:
            field_list = ",".join([x for x in td[0]])
            query = "SELECT " + field_list + " FROM " + td[1] + " WHERE user_id = " + str(user_id)
            self.env.cr.execute(query)
            res = self.env.cr.fetchall()
            to_clean = {r[1] for r in res if path in r[1]} - td[2]

            if to_clean:
                to_clean = {r[1]: r[0] for r in res if r[1] in to_clean}.values()
                self.env[td[1].replace("_", ".")].browse(to_clean).sudo().unlink()

    def _build_cache(self, folder_id, user_id):
        """
        Builds the cache for a given folder. This avoids using the ORM cache which does not show
        the required performances for a large number of files. Only the necessary data is set in
        cache.

        :param int folder_id: ID of the folder to scan
        :param int user_id: ID of the user to whom belongs the folder
        :return dict: content of the cache
        """
        _logger.debug('Building cache for folder_id "%s"...', folder_id)
        cache = {}
        cache["user_id"] = user_id
        params = (user_id,)

        query = "SELECT path, id, last_modification FROM oovideo_folder WHERE user_id = %s;"
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall()
        cache["folder"] = {r[0]: (r[1], r[2] or 0) for r in res}

        params = (user_id, folder_id)
        query = """
            SELECT path, id, last_modification FROM oovideo_media
            WHERE user_id = %s AND root_folder_id = %s;
        """
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall()
        cache["media"] = {r[0]: (r[1], r[2]) for r in res}

        return cache

    def _manage_dir(self, rootdir, cache):
        """
        For a given directory, checks that it is already in the cache.
        - If not in the cache, create the associated folder
        - If in the cache, check the last modification date
        If the last modification date is older than the one recorded, the folder is skipped

        :param str rootdir: folder to check
        :param dict cache: reading cache
        :return dict, bool: tuple with content of the cache updated, and boolean which indicates if
            the folder can be skipped
        """
        skip = False
        folder = cache["folder"].get(rootdir)
        mtime = int(os.path.getmtime(rootdir))

        if not folder:
            cache = self._create_folder(rootdir, cache)
        elif folder[1] >= mtime:
            skip = True
        else:
            parent_dir = os.sep.join(rootdir.split(os.sep)[:-1])
            parent_dir = cache["folder"].get(parent_dir, [False])
            Folder = self.env["oovideo.folder"].browse(folder[0])
            Folder.write({"last_modification": mtime, "parent_id": parent_dir[0]})
        return cache, skip

    def _create_folder(self, rootdir, cache):
        """
        Create the directory rootdir, and updates the cache.

        :param str rootdir: path of the folder to create
        :param dict cache: reading cache
        :return dict: cache updated
        """
        parent_dir = os.sep.join(rootdir.split(os.sep)[:-1])
        parent_dir = cache["folder"].get(parent_dir)
        if parent_dir:
            mtime = int(os.path.getmtime(rootdir))
            vals = {
                "root": False,
                "path": rootdir,
                "parent_id": parent_dir[0],
                "last_modification": mtime,
                "user_id": cache["user_id"],
            }
            Folder = self.env["oovideo.folder"].create(vals)
            cache["folder"][rootdir] = (Folder.id, mtime)

        return cache

    def _get_media_info(self, file_path):
        """
        Get the infos of a media, thanks to MediaInfo.

        :param str file_path: path of the media to get the data from
        :return dict: media data
        """
        try:
            media_info = MediaInfo.parse(file_path)
            vals = {"audio_tracks": 0, "audio_tracks_lang": []}
            for track in media_info.tracks:
                if track.track_type == "General":
                    vals["duration"] = int(float(track.duration or 0.0))
                elif track.track_type == "Video":
                    vals["height"] = track.height
                    vals["width"] = track.width
                    vals["bitrate"] = int(
                        float(track.bit_rate or track.nominal_bit_rate or 0.0) / 1000.0
                    )
                elif track.track_type == "Audio":
                    vals["audio_tracks"] += 1
                    vals["audio_tracks_lang"] += [
                        str(vals["audio_tracks"]) + ": " + (track.language or _("Unknown"))
                    ]
        except:
            _logger.warning('Error while opening file "%s"', file_path, exc_info=1)
        return vals

    def _scan_folder(self, folder_id):
        """
        The folder scanning method. It walks in all sub-directories of the folder. If the
        modification date is more recent than the recorded date, the directory is scanned.

        A file is scanned if these conditions are met:
        - the extension matches the allowed file extensions;
        - the last modification date is more recent than the recorded date, in order to update data
          of an existing record.
        During the scan, any new album or artists will be created as well.

        There is an arbitrary commit every 100 medias, which should allow a regular update of the
        database.

        :param int folder_id: ID of the folder to scan
        """
        with api.Environment.manage(), self.pool.cursor() as cr:
            time_start = dt.now()
            # As this function is in a new thread, open a new cursor because the existing one may be
            # closed
            if not self.env.context.get("test_mode"):
                self = self.with_env(self.env(cr))

                # Lock the folder. A new cursor is necessary right after since it is closed
                # explicitly. If the folder is locked, do nothing
                if not self._lock_folder(folder_id):
                    return {}

            VideoFolder = self.env["oovideo.folder"]
            VideoMedia = self.env["oovideo.media"]

            folder = VideoFolder.browse([folder_id])

            # Clean-up the DB before actual scan
            self._clean_directory(folder.path, folder.user_id.id)
            if not folder.exists():
                if not self.env.context.get("test_mode"):
                    self.env.cr.commit()
                return {}

            # Build the cache
            # - cache is used for read/search, i.e. avoid reading/searching same info several times
            # - cache_write is used for writing tracks info on other models and avoid stored
            #   related/computed fields
            cache = self._build_cache(folder.id, folder.user_id.id)
            i = len(cache["media"].keys())

            # Start scanning
            for rootdir, dirnames, filenames in os.walk(folder.path):
                _logger.debug('Scanning folder "%s"...', rootdir)

                cache, skip = self._manage_dir(rootdir, cache)
                if skip:
                    continue

                for fn in filenames:
                    # Check file extension
                    fn_ext = fn.split(".")[-1]
                    if fn_ext and fn_ext.lower() not in self.ALLOWED_FILE_EXTENSIONS:
                        continue

                    # Skip file if already in DB
                    fn_path = os.path.join(rootdir, fn)
                    mtime = int(os.path.getmtime(fn_path))
                    if fn_path in cache["media"].keys() and cache["media"][fn_path][1] >= mtime:
                        continue

                    # Get media info
                    media_info = self._get_media_info(os.path.join(rootdir, fn))

                    # Aggregate info
                    vals = {
                        "name": fn,
                        "duration": media_info.get("duration", 0),
                        "height": media_info.get("height", 0),
                        "width": media_info.get("width", 0),
                        "bitrate": media_info.get("bitrate", 1000),
                        "audio_tracks": media_info.get("audio_tracks", 0),
                        "audio_tracks_lang": str(media_info.get("audio_tracks_lang", [])),
                        "path": fn_path,
                        "last_modification": mtime,
                        "root_folder_id": folder_id,
                        "folder_id": cache["folder"][rootdir][0],
                        "user_id": cache["user_id"],
                    }

                    # Create the track. No need to insert a new track in the cache, since we won't
                    # scan it during the process.
                    if fn_path in cache["media"].keys():
                        media = VideoMedia.browse(cache["media"][fn_path][0])
                        media.write(vals)
                    else:
                        media = VideoMedia.create(vals)

                    # Commit every 1000 tracks
                    i = i + 1
                    if i % 100 == 0:
                        # Commit and close the transaction
                        if not self.env.context.get("test_mode"):
                            self.env.cr.commit()

            # Final stuff to write and tags cleaning
            if folder.exists():
                folder.write(
                    {
                        "last_scan": fields.Datetime.now(),
                        "last_scan_duration": round((dt.now() - time_start).total_seconds()),
                        "locked": False,
                    }
                )
            if not self.env.context.get("test_mode"):
                self.env.cr.commit()
            _logger.debug('Scan of folder_id "%s" completed!', folder_id)
            return {}

    def scan_folder_th(self, folder_id):
        """
        This is the method used to scan a oovideo folder with a new thread. Only one folder should
        be scanned at a time, since different folders can share album, artist and genre data.

        To improve scanning speed, two parameters are set in the context:
        - `recompute`: prevents calculating non-stored calculated fields
        - `prefetch_fields`: deactivate prefetching

        :param int folder_id: ID of the folder to scan
        """
        threaded_scan = threading.Thread(
            target=self.sudo().with_context(recompute=False, prefetch_fields=False)._scan_folder,
            args=(folder_id,),
        )
        threaded_scan.start()
