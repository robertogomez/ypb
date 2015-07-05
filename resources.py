#!/usr/bin/env python

import os
import sys
import argparse
import httplib2
from config import *
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the Developers Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

class Options():
    def __init__(self):
        self.id_config = False
        self.username_config = False
        self.id = None
        self.username = None
        self.related = None

    def process_options(self, arguments):
        # Check for mutual exclusion of config options
        try:
            if (CHANNELID and USERNAME):
                sys.exit("May only specify either CHANNELID or USERNAME")
        except NameError:
            pass

        # Process config options
        try:
            if CHANNELID:
                self.id_config = True
        except NameError:
            self.id_config = False

        try:
            if USERNAME:
                self.username_config = True
        except NameError:
            self.username_config = False

        # Process commandline arguments
        # Check args first, then config options if specified
        try:
            self.id = arguments.id if (arguments.id) else CHANNELID
        except NameError:
            self.id = None

        try:
            self.username = arguments.username if (arguments.username) else USERNAME
        except NameError:
            self.username = None

        try:
            self.related = arguments.related if (arguments.related) else RELATED
        except NameError:
            self.related = None

def process_arguments():
    parser = argparse.ArgumentParser(description="YouTube Playlist Backup script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[argparser])

    retrieval_method = parser.add_mutually_exclusive_group()
    retrieval_method.add_argument("-i", "--id", help="Retrieve playlists using channel ID")
    retrieval_method.add_argument("-u", "--username", help="Retrieve playlists using legacy YouTube username")
    parser.add_argument("-r", "--related", help="Also retrieve related playlists (likes, history, etc.)",
                        action="store_true")

    return parser.parse_args()

# Creates the resource object for interacting with the YouTube API
# Sets up OAuth 2.0 for authorized requests if necessary
def create_resource_object(id, username, arguments):
    global youtube

    if (id or username):
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
            developerKey=DEVELOPER_KEY)
    else:
        flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
            message=MISSING_CLIENT_SECRETS_MESSAGE,
            scope=YOUTUBE_READONLY_SCOPE)

        storage = Storage("%s-oauth2.json" % sys.argv[0])
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, arguments)

        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
            http=credentials.authorize(httplib2.Http()))

# Creates a request for the user's playlists using their channel ID
def create_id_request(id):
    return youtube.playlists().list(
        part="id,snippet",
        fields="items(id,snippet/title),nextPageToken",
        channelId=id,
        maxResults=MAX_RESULTS
    )

# Creates a request for the user's playlists using their username
# First uses a channel request to obtain channel ID from username
def create_username_request(username):
    channel_request = youtube.channels().list(
        part="id",
        forUsername=username,
        maxResults=MAX_RESULTS
    )

    channel_response = channel_request.execute()

    try:
        return youtube.playlists().list(
            part="id,snippet",
            fields="items(id,snippet/title),nextPageToken",
            channelId=channel_response["items"][0]["id"],
            maxResults=MAX_RESULTS
        )
    except IndexError:
        sys.exit("No channel found for {}".format(username))

# Creates an authenticated request for accessing the user's private playlists
def create_private_request():
    return youtube.playlists().list(
        part="id,snippet",
        fields="items(id,snippet/title),nextPageToken",
        mine="true",
        maxResults=MAX_RESULTS
    )

# Creates a channel request necessary for obtaining the channel's
# related playlists, via channel ID
def create_id_channel_request(id):
    return youtube.channels().list(
        part="contentDetails",
        fields="items(contentDetails/relatedPlaylists)",
        id=id
    )

# Creates a channel request necessary for obtaining the channel's
# related playlists, via username
def create_username_channel_request(username):
    return youtube.channels().list(
        part="contentDetails",
        fields="items(contentDetails/relatedPlaylists)",
        forUsername=username
    )

# Creates a channel request necessary for obtaining the channel's
# related playlists, via authentication
def create_private_channel_request():
    return youtube.channels().list(
        part="contentDetails",
        fields="items(contentDetails/relatedPlaylists)",
        mine="true"
    )

# Create request for obtaining the user's related playlists
def create_related_request(channel_request):
    playlist_id_list = []

    channel_response = channel_request.execute()

    # Traverse channel_response to create list of related playlist IDs
    for channel in channel_response["items"]:
        for playlist, playlist_id in channel["contentDetails"]["relatedPlaylists"].items():
            playlist_id_list.append(playlist_id)

    return youtube.playlists().list(
        part="id,snippet",
        fields="items(id,snippet/title),nextPageToken",
        id=",".join(playlist_id_list),
        maxResults=MAX_RESULTS
    )

# Backs-up playlists using the provided request
def backup_playlists(playlists_request):
    # Fetch pages of playlists until end
    while playlists_request:
        playlists_response = playlists_request.execute()

        for playlist in playlists_response["items"]:
            video_count = 0

            # Assemble request for videos in each playlist
            playlist_items_request = youtube.playlistItems().list(
                part="id,snippet",
                fields="items(id,snippet/title),nextPageToken",
                playlistId=playlist["id"],
                maxResults=MAX_RESULTS
            )

            print "{}".format(playlist["snippet"]["title"].encode("utf-8"))

            # Fetch pages of videos until end
            while playlist_items_request:
                playlist_items_response = playlist_items_request.execute()

                # Print videos in each playlist
                for i, video in enumerate(playlist_items_response["items"], start=1):
                    print "{}. {}".format((i + video_count), video["snippet"]["title"].encode("utf-8"))

                # Request next page of videos
                playlist_items_request = youtube.playlistItems().list_next(
                    playlist_items_request, playlist_items_response)

                if playlist_items_request is not None:
                    video_count += MAX_RESULTS
                else:
                    print

        # Request next page of playlists
        playlists_request = youtube.playlists().list_next(
            playlists_request, playlists_response)

