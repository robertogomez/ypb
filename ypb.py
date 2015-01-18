#!/usr/bin/env python2

import os
import sys
import time
import httplib2
from config import *
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

# Backs-up playlists using the provided request
def backup_playlists(youtube, playlists_request):
    path = time.strftime("%Y%m%d-%H%M%S")
    os.mkdir(path)

    # Fetch pages of playlists until end
    while playlists_request:
        playlists_response = playlists_request.execute()

        for playlist in playlists_response["items"]:
            # Assemble request for videos in each playlist
            playlist_items_request = youtube.playlistItems().list(
                part="id,snippet",
                fields="items(id,snippet/title),nextPageToken",
                playlistId=playlist["id"],
                maxResults=50
            )

            # Create new file for playlist
            with open(os.path.join(path, playlist["snippet"]["title"]), 'w') as f:

                # Fetch pages of videos until end
                while playlist_items_request:
                    playlist_items_response = playlist_items_request.execute()

                    # Print videos in each playlist
                    for video in playlist_items_response["items"]:
                        f.write(video["snippet"]["title"].encode("utf-8") + '\n')

                    # Request next page of videos
                    playlist_items_request = youtube.playlistItems().list_next(
                        playlist_items_request, playlist_items_response)

            f.close()

        # Request next page of playlists
        playlists_request = youtube.playlists().list_next(
            playlists_request, playlists_response)

# Creates request for retrieving all the user's playlists (including private
# ones). Script is authorized via OAuth 2.0 protocol.
def setup_auth_request(options):
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
        message=MISSING_CLIENT_SECRETS_MESSAGE,
        scope=YOUTUBE_READONLY_SCOPE)

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, options)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))

    playlists_request = youtube.playlists().list(
        part="id,snippet",
        fields="items(id,snippet/title),nextPageToken",
        mine="true",
        maxResults=50
    )

    backup_playlists(youtube, playlists_request);

# Creates request for retrieving the user's public playlists using channel ID.
# Script is authorized via developer key.
def setup_channelid_request(options):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        developerKey=DEVELOPER_KEY)

    playlists_request = youtube.playlists().list(
        part="id,snippet",
        fields="items(id,snippet/title),nextPageToken",
        channelId=options.channelid,
        maxResults=50
    )

    backup_playlists(youtube, playlists_request);

if __name__ == "__main__":
    argparser.add_argument("-c", "--channelid", help="Use channel ID instead of authenticated request")
    args = argparser.parse_args()

    try:
        if args.channelid:
            setup_channelid_request(args)
        else:
            setup_auth_request(args)
    except HttpError, e:
        print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

