#!/usr/bin/env python

from resources import *

if __name__ == "__main__":
    args = process_arguments()

    opt = Options()
    opt.process_options(args)

    try:
        create_resource_object(opt.id, opt.username, args)

        if (args.id or opt.id_config and args.username is None):
            req = create_id_request(opt.id)
            ch_req = create_id_channel_request(opt.id)
        elif (args.username or opt.username_config and args.id is None):
            req = create_username_request(opt.username)
            ch_req = create_username_channel_request(opt.username)
        else:
            req = create_private_request()
            ch_req = create_private_channel_request()

        backup_playlists(req)

        if (opt.related):
            req = create_related_request(ch_req)
            backup_playlists(req)

    except HttpError as e:
        print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

