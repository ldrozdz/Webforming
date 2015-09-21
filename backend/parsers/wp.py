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


class WPParser(WebParser):
  def __init__(self):
    self.nested = False
    self.post_id = None
    self.baseurl = None
    self.post_path = None
    self.print_url = 'http://%(baseurl)s/drukuj.html?wid=%(post_id)s'
    self.comments_url = 'http://%(baseurl)s/opage,%(page)s,sort,14,%(post_path)s'
    self.replies_url = 'http://%(baseurl)s/odpowiedzi-lista.html?wid=%(post_id)s&oid=%(comment_id)s'
    self.collection = 'biznes.onet.pl'
    self.domain = 'news'
    self.url = None
    self.title = None
    self.author = None
    self.items = {}
    self.start_urls = []
    self.author_map = {}

  def getParser(source_id):
    raise NotImplementedError()

  def process_post(self, post_url):
    self.items.clear()
    self.url = post_url
    post_id = re.match('.*wid,(\d+),wiadomosc.html.*', post_url).groups()
    if post_id:
      self.post_id = post_id[0]
    print '---- Post %s ----' % self.url
    try:
      self.baseurl = urlparse.urlparse(self.url).hostname
      self.post_path = urlparse.urlparse(self.url).path.split('/')[-1]
      handle = urlopen(self.url)
      page = handle.read()
      handle.close()
      #parse
      soup = BeautifulSoup(page, 'lxml')
    except Exception, e:
      print traceback.print_exc()
    else:
      head = soup.head
      body = BeautifulSoup(soup.prettify(), 'lxml', parse_only=SoupStrainer('div', id='bxArtykul'))
      [script.decompose() for script in body.find_all('script')]
      [iframe.decompose() for iframe in body.find_all('iframe')]
      [input.decompose() for input in body.find_all('input')]
      [img.decompose() for img in body.find_all('img')]
      [comment.extract() for comment in body.find_all(text=lambda t: isinstance(t, Comment))]
      #author
      try:
        author_tag = body.find('h2', 'publicysta')
        if author_tag:
          self.author = author_tag.text.strip()
        else:
          self.author = 'wp.pl'
      except Exception, e:
        self.author = None
      #date
      try:
        raw_date = head.find('meta', property='article:published_time')['content']
      except Exception, e:
        raw_date = ''
      parsed_date = self.parse_date(raw_date)
      #title
      try:
        self.title = body.find('h1', 'czytajto').text.strip()
      except Exception, e:
        self.title = None
      #content
      try:
        handle = urlopen(self.print_url % {'baseurl': self.baseurl, 'post_id': self.post_id})
        printpage = handle.read()
        handle.close()
        content = BeautifulSoup(printpage, 'lxml', parse_only=SoupStrainer('div', 'bxDrukujTxt'))
        [div.decompose() for div in content.div.find_all('div')]
        [table.decompose() for table in content.find_all('table')]
        text = '\n'.join(content.get_text(strip=True, separator=' '))
      except Exception, e:
        text = None
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
      #TODO: this should be parsed
      i.likes = 0
      i.dislikes = 0
      i.facebooked = 0
      i.tweeted = 0
      self.items[self.post_id] = i
      #comments
      comments_page = 1
      try:
        urlopen(self.comments_url % {'baseurl': self.baseurl, 'post_path': self.post_path, 'page': comments_page})
        comments_to_process = True
      except Exception, e:
        comments_to_process = False
      while comments_to_process:
        comments_to_process = self.process_comments(comments_page)
        comments_page += 1
      self.update_parent_fields()

  def process_comments(self, p):
    comments_url = self.comments_url % {'baseurl': self.baseurl, 'post_path': self.post_path, 'page': p}
    print '--- Getting comments page %s (%s) ---' % (p, comments_url)
    comments_handle = urlopen(comments_url)
    comments_page = comments_handle.read()
    comments_handle.close()
    csoup = BeautifulSoup(comments_page)
    paging_tag = csoup.find('div', 'opStron')
    next_page = True if (paging_tag and paging_tag.find('a', 'opNext')) else False
    ccsoup = BeautifulSoup(csoup.prettify(), parse_only=SoupStrainer('div', 'opOpinie'))
    for comment in ccsoup.div.find_all('div', 'opOpinia', recursive=False):
      try:
        self.parse_comment(comment, self.post_id)
      except Exception, e:
        traceback.print_exc()
    if next_page:
      return True
    else:
      return False

  def parse_comment(self, csoup, parent_id):
    comment_id = csoup.get('id')
    print '--- Comment %s ---' % comment_id
    comment_meta = csoup.find('div', 'opHd')
    #author
    try:
      comment_author = comment_meta.find('span', 'name').text.strip()
      comment_author_id = 'wp#%s' % (comment_author.replace(' ', '_'))
      self.author_map[comment_author] = '%s#comment%s' % (self.post_id, comment_id)
    except:
      comment_author = None
      comment_author_id = None
    #date
    try:
      comment_date_raw = '%s %s' % (comment_meta.find('span', 'stampZrodloData').text.strip(),
                                    comment_meta.find('span', 'stampZrodloGodzina').text.strip())
    except:
      comment_date_raw = None
    comment_date = self.parse_date(comment_date_raw)
    #url
    comment_url = '%s#%s' % (self.url, comment_id)
    #likes/dislikes
    try:
      likes = csoup.find('div', 'opOcena').find('div', 'green').text.strip()
    except:
      likes = None
    try:
      dislikes = csoup.find('div', 'opOcena').find('div', 'red').text.strip()
    except:
      dislikes = None
    body_div = csoup.find('div', 'opTresc')
    try:
      body_div.blockquote.decompose()
    except:
      pass
    body = body_div.get_text(strip=True, separator='\n')
    i = WebItem()
    i.post_id = '%s#comment%s' % (self.post_id, comment_id)
    i.parent_id = parent_id
    i.thread_starter_id = self.post_id
    i.post_url = comment_url
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
    try:
      next = csoup.next_sibling.next_sibling
    except:
      next = None
    if ((next) and (next.name == 'p') and ('opPokazDrugi' in next['class'])):
      try:
        self.parse_replies(comment_id)
      except Exception as e:
        traceback.print_exc(e)

  def parse_replies(self, comment_id):
    print '-- Getting replies to comment %s --' % comment_id
    replies_url = self.replies_url % {'baseurl': self.baseurl, 'post_id': self.post_id, 'comment_id': comment_id}
    replies_handle = urlopen(replies_url)
    replies_json = replies_handle.read()
    replies_handle.close()
    for r in sorted(json.loads(replies_json).values(), key=lambda x: x['id']):
      reply_id = r['id']
      reply_url = '%s#%s' % (self.url, reply_id)
      body = r['text'].strip()
      reply_date_raw = r['date'].strip()
      reply_date = self.parse_date(reply_date_raw)
      reply_author = r['nick']
      self.author_map[reply_author] = '%s#comment%s' % (self.post_id, reply_id)
      reply_author_id = 'wp#%s' % reply_author.replace(' ', '_')
      reply_likes = r['positiveCounter']
      reply_dislikes = r['negativeCounter']
      i = WebItem()
      i.post_id = '%s#comment%s' % (self.post_id, reply_id)
      i.parent_id = self.find_reply_parent(r, comment_id)
      i.thread_starter_id = self.post_id
      i.post_url = reply_url
      i.hash = hashlib.sha1(unicode.encode(unicode(string.join(body)), 'utf8')).hexdigest()
      i.post_date = reply_date_raw
      i.crawl_date = datetime.datetime.now()
      i.parsed_post_date = reply_date
      i.post_title = None
      i.post_author = reply_author
      i.post_author_id = reply_author_id
      i.post_author_reputation = None
      i.content = body
      i.page_category = None
      i.sub_category = None
      i.likes = reply_likes
      i.dislikes = reply_dislikes
      i.source_id = self.collection
      i.notes = self.domain
      i.thread_starter_title = self.title
      i.thread_starter_url = self.url
      i.thread_starter_author = self.author
      i.site_url = self.baseurl
      i.type = 'comment'
      i.language = 'pl'
      self.items[i.post_id] = i

  def find_reply_parent(self, reply, comment_id):
    parent_id = '%s#comment%s' % (self.post_id, comment_id)
    try:
      parent_id = self.author_map[reply['addnick']]
    except:
      try:
        parent_id = self.author_map[reply.text.split()[0].strip('@^')]
      except:
        pass
    return parent_id

  def parse_date(self, dt):
    now = datetime.datetime.now()
    parsed_date = now
    if (dt.endswith('temu]')):
      try:
        dt = re.sub('[\[\]]', '', dt).split() ##p&#243;&#322;
        if (len(dt) == 2):
          parsed_date = now - datetime.timedelta(hours=1)
        else:
          if dt[1].startswith('godz'):
            if (dt[0] == 'p&#243;&#322;'):
              parsed_date = now - datetime.timedelta(minutes=30)
            else:
              parsed_date = now - datetime.timedelta(hours=int(dt[0]))
          elif dt[1].startswith('min'):
            parsed_date = now - datetime.timedelta(minutes=int(dt[0]))
          elif dt[1].startswith('dz') or dt[1].startswith('dn'):
            parsed_date = now - datetime.timedelta(days=int(dt[0]))
      except Exception as e:
        traceback.print_exc(e)
    else:
      try:
        parsed_date = dparse(dt, fuzzy=True)
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
