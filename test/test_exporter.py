import os
import pickle
from backend.pipelines.gml_pipeline import GmlPipeline

from backend.pipelines.json_pipeline import JsonPipeline
from backend.pipelines.xls_pipeline import XlsPipeline


def process(id):
  data_dir = '/tmp/webforming/'
  exporters = (JsonPipeline(data_dir, id),
               XlsPipeline(data_dir, id),
               GmlPipeline(data_dir, id))
  picklef = open(os.path.join(data_dir, '%s.pckl' % id), 'r')
  items = pickle.load(picklef)
  picklef.close()
  for exporter in exporters:
    exporter.process(items, False)

if __name__ == '__main__':
  ids = ['rciv7']
  for id in ids:
    process(id)