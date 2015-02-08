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

# Backs-up playlists using the provided request
def backup_playlists(playlists_request):
    path = time.strftime("%Y%m%d-%H%M%S")
    os.mkdir(path)

    playlist_page = 0

    # Fetch pages of playlists until end
    while playlists_request:
        playlists_response = playlists_request.execute()

        for i, playlist in enumerate(playlists_response["items"], start=1):
            print "Saving playlist {} of {}".format(i + playlist_page * 50, playlists_response["pageInfo"]["totalResults"]), "\r",
            sys.stdout.flush()

            # Create new file for playlist
            # Assemble request for videos in each playlist
            playlist_items_request = youtube.playlistItems().list(
                part="id,snippet",
                fields="items(id,snippet/title),nextPageToken",
                playlistId=playlist["id"],
                maxResults=50
            )

            with open(os.path.join(path, playlist["snippet"]["title"]), 'w') as f:

                # Fetch pages of videos until end
                while playlist_items_request:
                    playlist_items_response = playlist_items_request.execute()

                    # Print videos in each playlist
                    for i, video in enumerate(playlist_items_response["items"], start=1):
                        f.write("{}. ".format(i) + video["snippet"]["title"].encode("utf-8") + '\n')

                    # Request next page of videos
                    playlist_items_request = youtube.playlistItems().list_next(
                        playlist_items_request, playlist_items_response)

            f.close()

        # Request next page of playlists
        playlists_request = youtube.playlists().list_next(
            playlists_request, playlists_response)

        playlist_page += 1

    print "\r"

# Creates the initial playlists request used in backup_playlists()
# Checks the commandline arguments and assembles the correct request
def setup_request(options):
    if (options.channelid):
        request = youtube.playlists().list(
            part="id,snippet",
            fields="items(id,snippet/title),nextPageToken,pageInfo/totalResults",
            channelId=options.channelid,
            maxResults=50
        )
    elif (options.youtube_username):
        # Create channel request to obtain channel id from YouTube username
        channel_request = youtube.channels().list(
            part="id",
            forUsername=options.youtube_username,
            maxResults=50
        )

        channel_response = channel_request.execute()

        try:
            request = youtube.playlists().list(
                part="id,snippet",
                fields="items(id,snippet/title),nextPageToken,pageInfo/totalResults",
                channelId=channel_response["items"][0]["id"],
                maxResults=50
            )
        except IndexError:
            sys.exit("No channel found for {}".format(options.youtube_username))
    else:
        request = youtube.playlists().list(
            part="id,snippet",
            fields="items(id,snippet/title),nextPageToken,pageInfo/totalResults",
            mine="true",
            maxResults=50
        )

    return request

# Creates the resource object for interacting with the YouTube API
# Sets up OAuth 2.0 for authorized requests if necessary
def create_resource_obj(options):
    global youtube

    if (options.channelid or options.youtube_username):
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
            developerKey=DEVELOPER_KEY)
    else:
        flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
            message=MISSING_CLIENT_SECRETS_MESSAGE,
            scope=YOUTUBE_READONLY_SCOPE)

        storage = Storage("%s-oauth2.json" % sys.argv[0])
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, options)

        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
            http=credentials.authorize(httplib2.Http()))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[argparser])

    parser.add_argument("-c", "--channelid", help="Use channel ID instead of authenticated request")
    parser.add_argument("-y", "--youtube-username", help="Retrieve playlists using legacy YouTube username")
    args = parser.parse_args()

    youtube = None

    try:
        create_resource_obj(args)
        req = setup_request(args)
        backup_playlists(req)
    except HttpError, e:
        print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

