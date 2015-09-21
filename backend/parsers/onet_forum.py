# -*- coding: utf-8 -*-
import re
from urllib2 import urlparse
import datetime
import hashlib
import traceback
import string

import requests

from bs4 import BeautifulSoup, SoupStrainer, Comment

from dateutil.parser import parse as dparse

from backend.parsers import WebParser
from backend.web_item import WebItem


class OnetForumParser(WebParser):
  def __init__(self):
    self.nested = False
    self.post_id = None
    self.baseurl = None
    self.post_path = None
    self.comments_url = None
    self.collection = 'wiadomosci.onet.pl'
    self.domain = 'news'
    self.url = None
    self.title = None
    self.author = None
    self.items = {}
    self.month_names = {'sty': 1,
                        'lut': 2,
                        'mar': 3,
                        'kwi': 4,
                        'maj': 5,
                        'cze': 6,
                        'lip': 7,
                        'sie': 8,
                        'wrz': 9,
                        'paź': 10,
                        'lis': 11,
                        'gru': 12}

  def getParser(source_id):
    raise NotImplementedError()

  def process_post(self, post_url):
    self.items.clear()
    self.url = post_url
    print '---- Post %s ----' % self.url
    try:
      self.baseurl = urlparse.urlparse(self.url).hostname
      self.post_path = urlparse.urlparse(self.url).path.split('/')[-1]
      resp = requests.get(self.url)
      page = resp.text
      resp.close()
      soup = BeautifulSoup(page, 'lxml')
    except Exception, e:
      print traceback.print_exc()
    else:
      head = soup.head
      body = BeautifulSoup(soup.prettify(), 'lxml', parse_only=SoupStrainer('div', id='main'))
      [script.decompose() for script in body.find_all('script')]
      [iframe.decompose() for iframe in body.find_all('iframe')]
      [input.decompose() for input in body.find_all('input')]
      [img.decompose() for img in body.find_all('img')]
      [comment.extract() for comment in body.find_all(text=lambda t: isinstance(t, Comment))]
      content = BeautifulSoup(page, 'lxml', parse_only=SoupStrainer('p', 'hyphenate'))
      [table.decompose() for table in content.find_all('table')]
      # date
      try:
        raw_date = head.find('meta', property='article:published_time')['content']
        parsed_date = dparse(raw_date, dayfirst=True, fuzzy=True)
      except Exception, e:
        raw_date = ''
        parsed_date = datetime.datetime.now()
      # title
      try:
        self.title = head.find('meta', property='og:title')['content']
      except Exception, e:
        self.title = None
      # author
      try:
        author_tag = body.find('span', 'k_sourceName')
        if author_tag:
          self.author = author_tag.text.strip()
        else:
          self.author = 'Onet Biznes'
      except Exception, e:
        self.author = None
      # content
      try:
        text = '\n'.join([_.get_text(strip=True, separator=' ') for _ in content.find_all('p', recursive=False)])
      except Exception, e:
        text = None
      # comments
      try:
        forum_tag = body.find('div', id='forum')
        forum_url = forum_tag.find('div', 'k_nForumReaderMenu').find('a', text=re.compile('w.tki'))['href']
        self.comments_url = 'http://%s%s' % (self.baseurl, forum_url)
        requests.get(self.comments_url)
        comments_to_process = True
        self.post_id = re.findall('\d\d+', forum_url)[-1]
      except:
        comments_to_process = False
      i = WebItem()
      i.post_id = self.post_id
      i.thread_starter_id = self.post_id
      i.post_url = self.url
      i.site_url = self.baseurl
      i.source_id = self.collection
      i.type = 'post'
      i.hash = hashlib.sha1(unicode.encode(unicode(string.join(text)), 'utf8')).hexdigest()
      i.post_date = raw_date
      i.crawl_date = datetime.datetime.now()
      i.parsed_post_date = parsed_date
      i.post_title = self.title
      i.post_author = self.author
      i.post_author_id = self.author
      i.content = text
      i.notes = self.domain
      i.language = 'pl'
      # TODO: this should be parsed
      i.likes = 0
      i.dislikes = 0
      i.facebooked = 0
      i.tweeted = 0
      self.items[self.post_id] = i
      comments_url = self.comments_url
      while comments_to_process:
        comments_url = self.process_comments(comments_url)
        if comments_url:
          comments_to_process = True
        else:
          comments_to_process = False
      self.update_parent_fields()

  def process_comments(self, comments_url):
    print '--- Getting comments page %s ---' % (comments_url)
    comments_resp = requests.get(comments_url)
    comments_page = comments_resp.text
    comments_resp.close()
    csoup = BeautifulSoup(comments_page)
    try:
      next_page = 'http://%s%s' % (self.baseurl, csoup.find('a', 'k_nForum_LinksNext')['href'])
    except:
      next_page = None
    ccsoup = BeautifulSoup(csoup.prettify(), parse_only=SoupStrainer('div', id='forum'))
    for comment in ccsoup.div.find_all('div', 'k_nForum_ReaderItem'):
      try:
        self.parse_comment(comment)
      except Exception, e:
        traceback.print_exc()
    return next_page

  def parse_comment(self, csoup):
    comment_tag = csoup.find('div', 'k_commentHolder')
    comment_id = comment_tag['id'].strip('attachment-')
    print '--- Comment %s ---' % comment_id
    # parent
    parent_id = self.post_id
    try:
      parent_url = csoup.find('div', 'k_parentNickTooltipHolder').find('div', 'k_noteHref').a['href']
      parent_id = '%s#comment%s' % (self.post_id, re.findall('\d\d+', parent_url)[-1])
    except:
      pass
    # author
    try:
      comment_author = csoup.find('span', 'k_nForumUserNickStrong').text.strip()
      comment_author_id = 'onetb#%s' % (comment_author.replace(' ', '_'))
    except:
      comment_author = None
      comment_author_id = None
    # date
    try:
      comment_date_raw = csoup.find('div', 'k_nForum_CommentInfo').span.text.strip()
    except:
      comment_date_raw = None
    comment_date = self.parse_date(comment_date_raw)
    # likes/dislikes
    comment_meta = csoup.find('div', 'k_nForum_MarkTipHands')
    try:
      likes = int(comment_meta.find('span', 'k_nForum_MarkTipUpPercent').text.strip().strip('%'))
    except:
      likes = None
    try:
      dislikes = int(comment_meta.find('span', 'k_nForum_MarkTipDownPercent').text.strip().strip('%'))
    except:
      dislikes = None
    body_tag = csoup.find('span', 'k_content')
    try:
      body_tag.find('span', 'read-more').decompose()
      body_tag.find('span', 'recollapse').decompose()
    except:
      pass
    body = body_tag.get_text(strip=True, separator='\n')
    i = WebItem()
    i.post_id = '%s#comment%s' % (self.post_id, comment_id)
    i.parent_id = parent_id
    i.thread_starter_id = self.post_id
    i.post_url = self.url
    i.hash = hashlib.sha1(unicode.encode(unicode(string.join(body)), 'utf8')).hexdigest()
    i.post_date = comment_date_raw
    i.crawl_date = datetime.datetime.now()
    i.parsed_post_date = comment_date
    i.post_title = None
    i.post_author = comment_author
    i.post_author_id = comment_author_id
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
    i.language = 'pl'
    self.items[i.post_id] = i

  def parse_date(self, dt):
    now = datetime.datetime.now()
    parsed_date = now
    try:
      dt = dt.split()
      if (dt[1] == 'min' and dt[-1] == 'temu'):
        parsed_date = now - datetime.timedelta(minutes=int(dt[0]))
      elif (dt[0] == 'dzisiaj'):
        parsed_date = dparse(dt[1])
      elif (dt[1] == 'wczoraj'):
        parsed_date = dparse('%s %s', (now - datetime.timedelta(days=1)).date.strftime('%Y-%m-%d'), dparse(dt[1]))
      else:
        dd = int(dt[0])
        mm = self.month_names[dt[1]]
        yy = now.year if (len(dt) == 3) else int(dt[2])
        t = dt[-1]
        parsed_date = dparse('%s/%s/%s %s' % (dd, mm, yy, t), dayfirst=True, fuzzy=True)
    except:
      pass
    return parsed_date

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
