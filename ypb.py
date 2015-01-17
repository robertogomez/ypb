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

def backup_all_playlists(options):
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
        message=MISSING_CLIENT_SECRETS_MESSAGE,
        scope=YOUTUBE_READONLY_SCOPE)
    
    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()
    
    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))

    path = time.strftime("%Y%m%d-%H%M%S")
    os.mkdir(path)

    # Assemble request for all of user's playlists
    playlists_request = youtube.playlists().list(
        part="id,snippet",
        fields="items(id,snippet/title),nextPageToken",
        mine="true",
        maxResults=50
    )

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

def backup_public_playlists(options):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        developerKey=DEVELOPER_KEY)

    path = time.strftime("%Y%m%d-%H%M%S")
    os.mkdir(path)

    # Assemble request for user's publicly available playlists
    playlists_request = youtube.playlists().list(
        part="id,snippet",
        fields="items(id,snippet/title),nextPageToken",
        channelId=options.channelid,
        maxResults=50
    )

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

if __name__ == "__main__":
    argparser.add_argument("-c", "--channelid", help="Use channel ID instead of authenticated request")
    args = argparser.parse_args()

    try:
        if args.channelid:
            backup_public_playlists(args)
        else:
            backup_all_playlists(args)
    except HttpError, e:
        print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

