import json
from datetime import datetime
import logging
from config import CHATROOM_PRESENCE

try:
    from urllib2 import urlopen, quote
except ImportError:
    from urllib.request import urlopen, quote

# Backward compatibility
from errbot.version import VERSION
from errbot.utils import version2array
if version2array(VERSION) >= [1,6,0]:
    from errbot import botcmd, BotPlugin
else:
    from errbot.botplugin import BotPlugin
    from errbot.jabberbot import botcmd


__author__ = 'gbin'

PLUS_STREAM_URL = 'https://www.googleapis.com/plus/v1/people/%s/activities/public?alt=json&pp=1&key=%s'
PLUS_SEARCH_URL = 'https://www.googleapis.com/plus/v1/people?alt=json&key=%s&query=%s'
PLUS_PROFILE_URL = 'https://www.googleapis.com/plus/v1/people/%s?key=%s'

def parse_isodate(date_string):
    return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")


class Item(object):
    def __init__(self, json_item):
        self.title = json_item['title']
        self.url = json_item['url']
        self.content = json_item['object']['originalContent'] if 'originalContent' in json_item['object'] else ''
        if 'attachments' in json_item['object']:
            self.attachments = [attachment['fullImage']['url'] for attachment in json_item['object']['attachments'] if 'fullImage' in attachment]
        else:
            self.attachments = None
        self.updated = parse_isodate(json_item['updated'])


class Feed(object):
    def __init__(self, userid, key):
        result = json.loads(urlopen(PLUS_STREAM_URL % (userid, key)).read().decode('utf-8'))
        self.title = result['title']
        self.updated = datetime.strptime(result['updated'], "%Y-%m-%dT%H:%M:%S.%fZ")
        self.items = [Item(json_item) for json_item in result['items']]


class Plus(BotPlugin):
    min_err_version = '1.4.1' # it needs the new automatic configuration feature

    def get_configuration_template(self):
        return {'GOOGLECLIENT_APIKEY': 'AIzaSyAKXi64lkJvAIHtTRf0WwQCGiw08gu8xsq'}

    def poll_plus(self):
        room = CHATROOM_PRESENCE[0]
        follow = self['follow']
        for id in follow:
            f = Feed(id, self.config['GOOGLECLIENT_APIKEY'])
            if f.updated > follow[id]:
                self.send(room, f.title, message_type='groupchat')
                for item in [item for item in f.items if item.updated > self['follow'][id]]:
                    self.send(room, item.url + '\n' + unicode(item.updated) + '--' + item.title , message_type='groupchat')
                    if item.attachments:
                        for image in item.attachments:
                            self.send(room, image, message_type='groupchat')
                follow[id] = f.updated
            else:
                logging.debug(str(id) + ' has no update %s > %s' % (str(f.updated), str(follow[id])))
            self['follow'] = follow

    def activate(self):
        super(Plus, self).activate()
        if not CHATROOM_PRESENCE:
            raise Exception('You need at least one chatroom configured')
        self.start_poller(600, self.poll_plus)

    def get_display_name(self, id):
        return json.loads(urlopen(PLUS_PROFILE_URL % (id, self.config['GOOGLECLIENT_APIKEY'])).read().decode('utf-8'))['displayName']

    @botcmd
    def plus_last(self, mess, args):
        """
        Find the last items from the specified user (i.e. 101905029512356212669)
        for example : !plus last 101905029512356212669
        """
        if not self.config:
            return 'This plugin needs to be configured... run !config Plus'
        if not args:
            return 'Who you want to see ?'
        f = Feed(args, self.config['GOOGLECLIENT_APIKEY'])
        self.send(mess.getFrom(), f.title, message_type=mess.getType())
        self.send(mess.getFrom(), '****   ' + f.title, message_type=mess.getType())
        for item in f.items:
            self.send(mess.getFrom(), item.url + '\n' + unicode(item.updated) + ' -- ' + item.title, message_type=mess.getType())
            if item.attachments:
                for image in item.attachments:
                    self.send(mess.getFrom(), image, message_type=mess.getType())
        return None

    @botcmd
    def plus_search(self, mess, args):
        """
        Search for the id of a person or google plus page by name
        for example : !plus search Guillaume BINET
        """
        if not self.config:
            return 'This plugin needs to be configured... run !config Plus'
        if not args:
            return 'Who you want to look for ?'
        result = json.loads(urlopen(PLUS_SEARCH_URL % (self.config['GOOGLECLIENT_APIKEY'], quote(args))).read().decode('utf-8'))
        for item in result['items']:
            self.send(mess.getFrom(), item['displayName'] + ' (!plus follow ' + item['id'] + ') ' + item['image']['url'], message_type=mess.getType())
        return None

    @botcmd
    def plus_follow(self, mess, args):
        """
        Follow the specified google plus stream by id
        for example : !plus follow 101905029512356212669
        """
        if not self.config:
            return 'This plugin needs to be configured... run !config Plus'
        if not args:
            return 'Who you want to follow ?'
        if not args.isdigit():
            return 'The google plus id must be a digit like 110857536631648345380'

        follow = self.get('follow', {})
        if args in follow:
            return 'You already follow %s' % args
        follow[args] = datetime.utcnow()
        self['follow'] = follow
        return "You are now following %s" % args

    @botcmd
    def plus_unfollow(self, mess, args):
        """
        Unfollow the specified google plus stream by id
        for example : !plus unfollow 101905029512356212669
        """
        if not args:
            return 'Who you want to unfollow ?'
        if not args.isdigit():
            return 'The google plus id must be a digit like 110857536631648345380'

        follow = self.get('follow', {})
        if args in follow:
            del follow[args]
            self['follow'] = follow
            return "OK, you don't follow %s anymore" % args

        return "You apparently not following %s already" % args

    @botcmd
    def plus_following(self, mess, args):
        """
        List the pages/persons you are following
        """
        ids = self.get('follow', {}).keys()
        return '\n'.join([self.get_display_name(id) + ' (!plus unfollow %s)'%id for id in ids])
