#!/usr/bin/env python

import os
import sys
import time
import argparse
import httplib2
from config import *
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

# Creates the resource object for interacting with the YouTube API
# Sets up OAuth 2.0 for authorized requests if necessary
def create_resource_obj():
    global youtube

    if (ident or uname):
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
            developerKey=DEVELOPER_KEY)
    else:
        flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
            message=MISSING_CLIENT_SECRETS_MESSAGE,
            scope=YOUTUBE_READONLY_SCOPE)

        storage = Storage("%s-oauth2.json" % sys.argv[0])
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, args)

        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
            http=credentials.authorize(httplib2.Http()))

# Creates a request for the user's playlists using their channel ID
def setup_id_request():
   request = youtube.playlists().list(
       part="id,snippet",
       fields="items(id,snippet/title),nextPageToken",
       channelId=ident,
       maxResults=50
   )

   return request

# Creates a request for the user's playlists using their username
# First uses a channel request to obtain channel ID from username
def setup_username_request():
   channel_request = youtube.channels().list(
       part="id",
       forUsername=uname,
       maxResults=50
   )

   channel_response = channel_request.execute()

   try:
       request = youtube.playlists().list(
           part="id,snippet",
           fields="items(id,snippet/title),nextPageToken",
           channelId=channel_response["items"][0]["id"],
           maxResults=50
       )
   except IndexError:
       sys.exit("No channel found for {}".format(uname))

   return request

# Creates an authenticated request for accessing the user's private playlists
def setup_private_request():
    request = youtube.playlists().list(
        part="id,snippet",
        fields="items(id,snippet/title),nextPageToken",
        mine="true",
        maxResults=50
    )

    return request

# Backs-up playlists using the provided request
def backup_playlists(playlists_request):
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

            # Fetch pages of videos until end
            while playlist_items_request:
                playlist_items_response = playlist_items_request.execute()

                print "{}".format(playlist["snippet"]["title"])

                # Print videos in each playlist
                for i, video in enumerate(playlist_items_response["items"], start=1):
                    print "{}. {}".format((i), video["snippet"]["title"].encode("utf-8"))

                print

                # Request next page of videos
                playlist_items_request = youtube.playlistItems().list_next(
                    playlist_items_request, playlist_items_response)

        # Request next page of playlists
        playlists_request = youtube.playlists().list_next(
            playlists_request, playlists_response)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Playlist Backup script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[argparser])
    retrieval_method = parser.add_mutually_exclusive_group()
    retrieval_method.add_argument("-i", "--id", help="Retrieve playlists using channel ID")
    retrieval_method.add_argument("-u", "--username", help="Retrieve playlists using legacy YouTube username")
    args = parser.parse_args()

    # Process user options
    # Check the commandline arguments first, then the config vars if specified
    try:
        ident = args.id if (args.id) else CHANNELID
    except NameError:
        ident = None

    try:
        uname = args.username if (args.username) else USERNAME
    except NameError:
        uname = None

    youtube = None

    try:
        create_resource_obj()

        if (ident):
            req = setup_id_request()
        elif (uname):
            req = setup_username_request()
        else:
            req = setup_private_request()

        backup_playlists(req)
    except HttpError as e:
        print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

