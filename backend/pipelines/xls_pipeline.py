from collections import Counter
from xlwt import Workbook
import os

__author__ = 'admin'

class XlsPipeline(object):
  def __init__(self, data_dir, id):
    self.data_dir = data_dir
    self.id = id

  def process(self, items, nested=False):
    sorted_items = sorted(items.values(), key=lambda i: i.parsed_post_date.replace(tzinfo=None))
    counts = Counter([(_.post_author, _.parent_author) for _ in sorted_items])
    book = Workbook()
    sheet1 = book.add_sheet('Details')

    sheet1.write(0,0,'post_author')
    sheet1.write(0,1,'replied_to')
    sheet1.write(0,2,'timestamp')
    sheet1.write(0,3,'post_type')
    sheet1.write(0,4,'content')
    i = 1
    for item in sorted_items:
      for idx, val in enumerate((item.post_author, item.parent_author, item.post_date, item.type, item.content[:1024])):
        sheet1.write(i, idx, val)
      i += 1
    sheet2 = book.add_sheet('Stats')
    sheet2.write(0,0,'post_author')
    sheet2.write(0,1,'replied_to')
    sheet2.write(0,2,'num_replies')
    i = 1
    for k,v in counts.items():
      sheet2.write(i, 0, k[0])
      sheet2.write(i, 1, k[1])
      sheet2.write(i, 2, v)
      i += 1
    out_file = os.path.join(self.data_dir, '%s.xls' % self.id)
    print '--- Writing file %s ---' % out_file
    book.save(out_file)

  def _find_or_append_node(self, value):
    try:
      return self.nodes.index(value)
    except ValueError:
      self.nodes.append(value)
      return len(self.nodes)