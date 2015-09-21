# -*- coding: utf-8 -*-
import pickle
import os

from backend.pipelines.gml_pipeline import GmlPipeline
from backend.pipelines.json_pipeline import JsonPipeline
from backend.pipelines.xls_pipeline import XlsPipeline
from parsers import WebParser


def crawl(id, source, url, data_dir):
  parser = WebParser.getParser(source)
  parser.process_post(url)
  picklef = open(os.path.join(data_dir, '%s.pckl' % id), 'w')
  pickle.dump(parser.items, picklef)
  picklef.close()


def export(id, data_dir):
  exporters = (JsonPipeline(data_dir, id),
               XlsPipeline(data_dir, id),
               GmlPipeline(data_dir, id))
  picklef = open(os.path.join(data_dir, '%s.pckl' % id), 'r')
  items = pickle.load(picklef)
  picklef.close()
  for exporter in exporters:
    exporter.process(items, False)
