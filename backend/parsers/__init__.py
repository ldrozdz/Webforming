__author__ = 'lukasz'

class WebParser(object):
  def __init__(self):
    self.nested = False

  @staticmethod
  def getParser(source_id):
    if source_id == 'cnn':
      from backend.parsers.cnn import CNNParser
      return CNNParser()
    elif source_id == 'gua':
      from backend.parsers.guardian import GuardianParser
      return GuardianParser()
    elif source_id == 'tguk':
      from backend.parsers.telegraph import TelegraphParser
      return TelegraphParser()
    elif source_id == 'tim':
      from backend.parsers.tim import ThisIsMoneyParser
      return ThisIsMoneyParser()
    elif source_id == 'wp':
      from backend.parsers.wp import WPParser
      return WPParser()
    elif source_id == 'onetb':
      from backend.parsers.onet_biznes import OnetBiznesParser
      return OnetBiznesParser()
    elif source_id == 'onetf':
      from backend.parsers.onet_forum import OnetForumParser
      return OnetForumParser()
    else:
      raise NotImplementedError()
  def process_post(self, url):
    raise NotImplementedError()