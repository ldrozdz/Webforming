import os
import pickle
from backend.parsers import WebParser

if __name__=='__main__':
  data_dir = '/tmp'
  id = 'tim'
  url = 'http://www.thisismoney.co.uk/money/news/article-3143020/What-happening-Greece-debt-default-affect-us.html'
  parser = WebParser.getParser(id)
  parser.process_post(url)
  picklef = open(os.path.join(data_dir, '%s.pckl' % id), 'w')
  pickle.dump(parser.items, picklef)
  picklef.close()
