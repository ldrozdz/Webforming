# -*- coding: utf-8 -*-
import re

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

#TODO: possible improvements through Guardian's Open Platform: http://www.theguardian.com/open-platform
class GuardianParser(WebParser):

  def __init__(self):
    self.nested = False
    self.post_id = None
    self.guardian_id = None
    self.comments_url = 'http://discussion.theguardian.com/discussion/%(guardian_id)s?orderby=oldest&per_page=50&commentpage=%(page)s&noposting=true&tab=all&forcetab=true&threads=expanded'
    self.baseurl = None
    self.collection = 'guardian.co.uk'
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
      #parse
      soup = BeautifulSoup(page, 'lxml')
    except Exception, e:
      print traceback.print_exc()
    else:
      head = soup.head
      #guardian_id
      guardian_id_url = head.find('link',rel='shorturl')['href']
      self.guardian_id = urlparse.urlparse(guardian_id_url).path[1:]
      self.post_id = 'gua%s' % self.guardian_id.replace('/','')
      #author
      try:
        author_url = head.find('meta',property='article:author')['content']
        author_handle = urlopen(author_url.strip())
        author_page = author_handle.read()
        author_handle.close()
        author_soup = BeautifulSoup(author_page)
        self.author = author_soup.find('meta',property='og:title')['content'].strip()
      except Exception, e:
        self.author = None
      #date
      try:
        raw_date = head.find('meta',property='article:published_time')['content']
        parsed_date = dparse(raw_date)
      except Exception, e:
        raw_date = ''
        parsed_date = None
      #title
      try:
        self.title = head.find('meta',property='og:title')['content']
      except Exception, e:
        self.title = None
      #lead
      try:
        lead = head.find('meta',property='og:description')['content']
      except Exception, e:
        lead = None
      soup = BeautifulSoup(soup.prettify(),'lxml',parse_only=SoupStrainer('div',id='article-body-blocks'))
      [script.decompose() for script in soup.find_all('script')]
      [iframe.decompose() for iframe in soup.find_all('iframe')]
      [input.decompose() for input in soup.find_all('input')]
      [img.decompose() for img in soup.find_all('img')]
      [comment.extract() for comment in soup.find_all(text=lambda t:isinstance(t, Comment))]
      #content
      try:
        body = '\n'.join([_.get_text(strip=True,separator=' ') for _ in soup.find_all('p')])
        if lead: body = '\n'.join((lead, body))
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
      comments_page = 1
      try:
        urlopen(self.comments_url % {'guardian_id':self.guardian_id, 'page':comments_page})
        comments_to_process = True
      except Exception, e:
        comments_to_process = False
      while comments_to_process:
        comments_to_process = self.process_comments(comments_page)
        comments_page += 1
      self.update_parent_fields()

  def process_comments(self, p):
    comments_url = self.comments_url % {'guardian_id':self.guardian_id, 'page':p}
    print '--- Getting comments page %s (%s) ---' % (p, comments_url)
    comments_handle = urlopen(comments_url)
    comments_page = comments_handle.read()
    comments_handle.close()
    csoup = BeautifulSoup(comments_page)
    next_page = True if csoup.find('div','d2-next-page').a else False
    ccsoup = BeautifulSoup(csoup.prettify(),parse_only=SoupStrainer('li','d2-comment'))
    for comment in ccsoup.find_all('li', attrs={'class':'d2-comment', 'data-comment-id':True}):
      try:
        self.parse_comment(comment, self.post_id)
      except Exception, e:
        traceback.print_exc()
    if next_page:
      return True
    else:
      return False

  def find_reply_parent_id(self, comment):
    reply_tag = comment.find('a','d2-in-reply-to')
    if reply_tag:
      return reply_tag['data-action-target']
    else:
      return reply_tag

  def parse_comment(self, csoup, parent_id):
    comment_id = csoup.get('data-comment-id')
    comment_author_id = csoup.get('data-userid')
    comment = csoup.find('div','d2-comment-inner').find('div','d2-right-col')
    print '--- Comment %s ---' % comment_id
    comment_meta = comment.find('div','d2-permalink').find('p','d2-datetime')
    comment_url = comment_meta.find('a','d2-js-permalink')['href']
    comment_date_raw = comment_meta.a.text.strip()
    comment_author = comment.find('a','d2-username').text.strip()
    body_div = comment.find('div','d2-body')
    #TODO: the blockquotes could (in the future) be used to identify the parent if no @xyz present
    try:
      body_div.blockquote.decompose()
    except:
      pass
    body = body_div.get_text(strip=True,separator='\n')
    try:
      likes = int(comment.find('div','d2-recommend-count').text.strip())
    except:
      likes = None
    reply_to = self.find_reply_parent_id(comment)
    i = WebItem()
    i.post_id = '%s#comment%s' % (self.post_id, comment_id)
    i.parent_id = '%s#comment%s' % (self.post_id, reply_to) if reply_to else parent_id
    i.thread_starter_id = self.post_id
    i.post_url = comment_url
    i.hash = hashlib.sha1(unicode.encode(unicode(string.join(body)),'utf8')).hexdigest()
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
    i.source_id = self.collection
    i.notes = self.domain
    i.thread_starter_title = self.title
    i.thread_starter_url = self.url
    i.thread_starter_author = self.author
    i.site_url = self.baseurl
    i.type = 'comment'
    i.language = 'en'
    self.items[i.post_id] = i
    for reply in csoup.find_all('li','d2-reply'):
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
