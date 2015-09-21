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


class ThisIsMoneyParser(WebParser):
  def __init__(self):
    self.nested = False
    self.post_id = None
    self.comments_url = 'http://www.thisismoney.co.uk/reader-comments/p/asset/readcomments/%(id)s?max=100&order-desc&offset=%(offset)s'
    self.baseurl = None
    self.collection = 'thisismoney.co.uk'
    self.domain = 'news'
    self.url = None
    self.title = None
    self.author = None
    self.items = {}
    self.start_urls = []

  def getParser(source_id):
    raise NotImplementedError()

  def process_post(self, post_url):
    self.items.clear()
    self.url = post_url
    print '---- Post %s ----' % self.url
    try:
      self.baseurl = urlparse.urlparse(self.url).hostname
      handle = urlopen(self.url)
      page = handle.read()
      handle.close()
      # parse
      soup = BeautifulSoup(page, 'lxml')
    except Exception, e:
      print traceback.print_exc()
    else:
      head = soup.head
      # guardian_id
      self.post_id = head.find('meta', {'name':'articleid'})['content']
      # author
      try:
        self.author = head.find('meta', property='article:author')['content']
      except Exception, e:
        self.author = None
      # date
      try:
        raw_date = head.find('meta', property='article:published_time')['content']
        parsed_date = dparse(raw_date.split('yyyy')[0])
      except Exception, e:
        raw_date = ''
        parsed_date = None
      # title
      try:
        self.title = head.find('meta', property='og:title')['content']
      except Exception, e:
        self.title = None
      # lead
      try:
        lead = head.find('meta', property='og:description')['content']
      except Exception, e:
        lead = None
      soup = BeautifulSoup(soup.prettify(), 'lxml', parse_only=SoupStrainer('div', id='article-body-blocks'))
      [script.decompose() for script in soup.find_all('script')]
      [iframe.decompose() for iframe in soup.find_all('iframe')]
      [input.decompose() for input in soup.find_all('input')]
      [img.decompose() for img in soup.find_all('img')]
      [comment.extract() for comment in soup.find_all(text=lambda t: isinstance(t, Comment))]
      # content
      try:
        body = '\n'.join([_.get_text(strip=True, separator=' ') for _ in soup.find_all('p', 'mol-para-with-font')])
      except Exception, e:
        body = ''
      i = WebItem()
      i.post_id = self.post_id
      i.thread_starter_id = self.post_id
      i.post_url = self.url
      i.site_url = self.baseurl
      i.source_id = self.collection
      i.type = 'post'
      i.hash = hashlib.sha1(unicode.encode(unicode(string.join(body)), 'utf8')).hexdigest()
      i.post_date = raw_date
      i.crawl_date = datetime.datetime.now()
      i.parsed_post_date = parsed_date
      i.post_title = self.title
      i.post_author = self.author
      i.post_author_id = self.author
      i.content = body
      i.notes = self.domain
      i.language = 'en'
      i.likes = 0
      i.dislikes = 0
      i.facebooked = 0
      i.tweeted = 0
      self.items[self.post_id] = i
      # comments
      offset = 0
      try:
        urlopen(self.comments_url % {'id': self.post_id, 'offset': offset})
        comments_to_process = True
      except Exception, e:
        comments_to_process = False
      while comments_to_process:
        comments_to_process = self.process_comments(offset)
        offset += 100
      self.update_parent_fields()

  def process_comments(self, p):
    comments_url = self.comments_url % {'id': self.post_id, 'offset': p}
    print '--- Getting comments %s-%s (%s) ---' % (p, p + 100, comments_url)
    comments_handle = urlopen(comments_url)
    comments_page = comments_handle.read()
    comments_handle.close()
    csoup = json.loads(comments_page)
    next_page = True if csoup['payload']['total'] >= p + 100 and csoup['payload']['page'] else False
    for comment in csoup['payload']['page']:
      try:
        self.parse_comment(comment, self.post_id)
      except Exception, e:
        traceback.print_exc()
    if next_page:
      return True
    else:
      return False

  def parse_comment(self, comment, parent_id):
    comment_id = comment['id']
    print '--- Comment %s ---' % comment_id
    comment_author_id = comment['userIdentifier']
    comment_author = comment['userAlias']
    comment_date_raw = comment['dateCreated']
    votes = comment['voteCount']
    likes = comment['voteRating']
    body = comment['message']
    dislikes = votes - likes
    i = WebItem()
    i.post_id = '%s#comment%s' % (self.post_id, comment_id)
    i.parent_id = parent_id
    i.thread_starter_id = self.post_id
    i.hash = hashlib.sha1(unicode.encode(unicode(string.join(body)), 'utf8')).hexdigest()
    i.post_date = comment_date_raw
    i.crawl_date = datetime.datetime.now()
    i.parsed_post_date = dparse(comment_date_raw)
    i.post_title = None
    i.post_author = comment_author
    i.post_author_id = 'gua#%s' % comment_author_id
    i.post_author_reputation = None
    i.content = body
    i.page_category = None
    i.sub_category = None
    i.likes = likes
    i.dislikes = dislikes
    i.source_id = self.collection
    i.notes = self.domain
    i.thread_starter_title = self.title
    i.thread_starter_url = self.url
    i.thread_starter_author = self.author
    i.site_url = self.baseurl
    i.type = 'comment'
    i.language = 'en'
    self.items[i.post_id] = i
    for reply in comment['replies']['comments']:
      self.parse_comment(reply, i.post_id)

  def update_parent_fields(self):
    for item in self.items.values():
      try:
        parent = self.items[item.parent_id]
        item.parent_url = parent.post_url
        item.parent_title = parent.post_title
        item.parent_author = parent.post_author
        item.parent_author_id = parent.post_author_id
      except Exception, e:
        item.parent_url = None
        item.parent_title = None
        item.parent_author = None
