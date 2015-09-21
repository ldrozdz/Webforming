# -*- coding: utf-8 -*-

from urllib2 import urlopen, urlparse
import datetime
import hashlib
import traceback
import string
import json

from bs4 import BeautifulSoup, SoupStrainer, Comment
from dateutil.parser import parse as dparse
from backend.parsers import WebParser

from backend.web_item import WebItem

class TelegraphParser(WebParser):

  def __init__(self):
    self.nested = False
    self.disqus_api_key = 'E8Uh5l5fHZ6gD8U3KycjAIAk46f68Zw7C6eW8WSjZvCLXebZ7p0r1yrYDrLilk2F'
    self.disqus_info_url = 'http://disqus.com/api/3.0/threads/details?api_key=%(api_key)s&thread:ident=%(ident)s&forum=telegraphuk'
    self.disqus_url = 'http://disqus.com/api/3.0/threads/listPostsThreaded?limit=100&thread=%(thread)s&forum=telegraphuk&order=asc&cursor=%(cursor)s&api_key=%(api_key)s'
    self.baseurl = None
    self.collection = 'telegraph.co.uk'
    self.domain = 'news'
    self.url = None
    self.title = None
    self.author = None
    self.post_id = None
    self.disqus_id = None
    self.disqus_ident = None
    self.items = {}
    self.start_urls = []

  def getParser(source_id):
    raise NotImplementedError()

  def _get_disqus_id(self, article_id):
    info_url = self.disqus_info_url % {'api_key':self.disqus_api_key, 'ident':article_id}
    info_handle = urlopen(info_url)
    info_json = json.load(info_handle)
    self.disqus_id = info_json['response']['id']


  def process_post(self, post_url):
    self.items.clear()
    self.url = post_url

    print '---- Post ----'
    print self.url
    try:
      self.baseurl = urlparse.urlparse(self.url).hostname
      handle = urlopen(self.url)
      page = handle.read()
      handle.close()
      #parse
      soup = BeautifulSoup(page, "lxml")
    except Exception, e:
      print traceback.print_exc()
    else:
      head = soup.head
      #disqus id
      article_id = head.find('meta',attrs={'name':'article-id'})['content']
      self._get_disqus_id(article_id)
      self.post_id = 'tguk%s' % self.disqus_id
      #author
      try:
        self.author = head.find('meta',attrs={'name':'DCSext.author'})['content']
      except Exception, e:
        self.author = None
      #date
      try:
        raw_date = head.find('meta',attrs={'name':'DCSext.articleFirstPublished'})['content']
        parsed_date = dparse(raw_date, dayfirst=True, fuzzy=True)
      except Exception, e:
        raw_date = ''
        parsed_date = None
      #title
        try:
          self.title = head.find('meta',attrs={'name':'title'})['content']
        except Exception, e:
          self.title = None
      soup = BeautifulSoup(soup.prettify(), "lxml", parse_only=SoupStrainer('div',attrs={'id':'mainBodyArea','itemprop':'articleBody'}))
      [script.decompose() for script in soup.find_all('script')]
      [iframe.decompose() for iframe in soup.find_all('iframe')]
      [input.decompose() for input in soup.find_all('input')]
      [img.decompose() for img in soup.find_all('img')]
      [comment.extract() for comment in soup.find_all(text=lambda t:isinstance(t, Comment))]
      [inline.extract() for inline in soup.find_all('div','related_links_inline')]
      #content
      try:
        body = '\n'.join([_.get_text(strip=True) for _ in soup.find_all('p')])
      except Exception, e:
        body = ''
      i = WebItem()
      i.post_id = self.post_id
      i.thread_starter_id = self.post_id
      i.post_url = self.url
      i.site_url = self.baseurl
      i.source_id = self.collection
      i.type = 'post'
      i.hash = hashlib.sha1(unicode.encode(unicode(string.join(body)),'utf8')).hexdigest()
      i.post_date = raw_date
      i.crawl_date = datetime.datetime.now()
      i.parsed_post_date = parsed_date
      i.post_title = self.title
      i.post_author = self.author
      i.post_author_id = self.author
      i.content = body
      i.notes = self.domain
      i.language = 'en'
      #TODO: this should be parsed
      i.likes = 0
      i.dislikes = 0
      i.facebooked = 0
      i.tweeted = 0
      self.items[self.post_id] = i
      #comments
      comments_to_process = True
      comments_cursor = '0:0:0'
      while comments_to_process:
        print '--- Getting comments %s ---' % comments_cursor
        comments_url = self.disqus_url % {'thread':self.disqus_id, 'cursor': comments_cursor, 'api_key': self.disqus_api_key}
        comments_handle = urlopen(comments_url)
        comments_json = json.load(comments_handle)
        comments_handle.close()
        comments_to_process = comments_json['cursor']['hasNext']
        comments_cursor = comments_json['cursor']['next']
        self.process_comments(comments_json['response'])
      self.update_parent_fields()

  def process_comments(self, csoup):
    for comment in csoup:
      print '--- Comment %s ---' % comment['id']
      body = BeautifulSoup(comment['message']).get_text(strip=True)
      post_url = 'http://disqus.com/api/3.0/posts/details?post=%(post_id)s&api_key=%(api_key)s'
      i = WebItem()
      i.post_id = '%s#comment%s' % (self.post_id, comment['id'])
      i.parent_id = '%s#comment%s' % (self.post_id, comment['parent']) if comment['parent'] else  self.post_id
      i.thread_starter_id = self.post_id
      i.post_url = post_url % {'post_id': comment['id'], 'api_key': self.disqus_api_key}
      i.hash = hashlib.sha1(unicode.encode(unicode(string.join(body)),'utf8')).hexdigest()
      i.post_date = comment['createdAt']
      i.crawl_date = datetime.datetime.now()
      i.parsed_post_date = dparse(comment['createdAt'])
      i.post_title = None
      i.post_author = comment['author']['name']
      i.post_author_id = 'tguk#%s' % comment['author']['id'] if not comment['author']['isAnonymous'] else 'tguk#%s' % comment['author']['name']
      i.post_author_reputation = comment['author']['reputation'] if not comment['author']['isAnonymous'] else None
      i.content = body
      i.page_category = None
      i.sub_category = None
      i.likes = comment['likes']
      i.dislikes = comment['dislikes']
      i.source_id = self.collection
      i.notes = self.domain
      i.thread_starter_title = self.title
      i.thread_starter_url = self.url
      i.thread_starter_author = self.author
      i.site_url = self.baseurl
      i.type = 'comment'
      i.language = 'en'
      self.items[i.post_id] = i

  def update_parent_fields(self):
    for item in self.items.values():
      try:
        parent = self.items[item.parent_id]
        item.parent_url = parent.post_url
        item.parent_title = parent.post_title
        item.parent_author = parent.post_author
      except Exception, e:
        item.parent_url = None
        item.parent_title = None
        item.parent_author = None
