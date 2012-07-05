import json
import datetime
from errbot.botplugin import BotPlugin
from errbot.jabberbot import botcmd
from urllib2 import urlopen,quote

__author__ = 'gbin'

PLUS_URL = 'https://www.googleapis.com/plus/v1/people/%s/activities/public?alt=json&pp=1&key=%s'
def parse_isodate(date_string):
    return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")

class Item(object):
    def __init__(self, json_item):
        self.title = json_item['title']
        self.url = json_item['url']
        self.content = json_item['object']['originalContent']
        if json_item['object'].has_key('attachments'):
            self.attachments = [attachment['fullImage']['url'] for attachment in json_item['object']['attachments'] if attachment.has_key('fullImage')]
        else:
            self.attachments = None
        self.updated = parse_isodate(json_item['updated'])

class Feed(object):
    def __init__(self, userid, key):
        result = json.load(urlopen(PLUS_URL%(userid, key)))
        self.title = result['title']
        self.updated = datetime.datetime.strptime(result['updated'], "%Y-%m-%dT%H:%M:%S.%fZ")
        self.items = [Item(json_item) for json_item in result['items']]

class Plus(BotPlugin):

    min_err_version = '1.3.0' # it needs the configuration feature

    def get_configuration_template(self):
        return {'GOOGLECLIENT_APIKEY' : 'AIzaSyAKXi64lkJvAIHtTRf0WwQCGiw08gu8xsq'}

    def configure(self, configuration):
        if configuration:
            if type(configuration) != dict:
                super(Plus, self).configure(None)
                raise Exception('Wrong configuration type')

            if not configuration.has_key('GOOGLECLIENT_APIKEY'):
                super(Plus, self).configure(None)
                raise Exception('Wrong configuration type, it should contain GOOGLECLIENT_APIKEY')
            if len(configuration) > 1:
                raise Exception('What else did you try to insert in my config ?')
        super(Plus, self).configure(configuration)

    @botcmd
    def plus_last(self, mess, args):
        """
        Find the last items from the specified user (i.e. 101905029512356212669)
        """
        if not self.config:
            return 'This plugin needs to be configured... run !config Plus'
        if not args:
            return 'Who you want to see ?'
        f = Feed(args, self.config['GOOGLECLIENT_APIKEY'])
        self.send(mess.getFrom(), '****   ' + f.title, message_type=mess.getType())
        for item in f.items:
            self.send(mess.getFrom(), unicode(item.updated) + ' -- ' + item.title, message_type=mess.getType())
            if item.attachments:
                for image in item.attachments:
                    self.send(mess.getFrom(), image, message_type=mess.getType())
        return None