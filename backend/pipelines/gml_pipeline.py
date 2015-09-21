import codecs
from collections import OrderedDict
import os
import networkx as nx

class GmlPipeline(object):
  def __init__(self, data_dir, id):
    self.data_dir = data_dir
    self.id = id

  def _create_node(self, item):
    id =  item.post_author_id
    node = {}
    node['group'] = 1
    node['name'] = item.post_author

    self.node_map[id] = self.seq
    self.link_map[(item.post_author_id, item.parent_author_id)] += 1

    link = {}
    link['source'] = self.node_map[id]
    link['value'] = self.link_map[(item.post_author_id, item.parent_author_id)]
    link['target'] = self.node_map[item.parent_author_id]

    self.nodes.append(node)
    self.links.append(link)
    self.seq += 1

  def process(self, items, nested=False):
    #include post
    sorted_items = sorted(items.values(), key=lambda i: i.parsed_post_date.replace(tzinfo=None))
    out_file = os.path.join(self.data_dir, '%sp.graphml' % self.id)
    self._process(sorted_items, out_file, nested=False)
    #exclude post
    thread_starter_author = filter(lambda i: i.type=='post', sorted_items)[0].post_author
    sorted_items = [i for i in sorted_items if (i.post_author!= thread_starter_author and i.parent_author!= thread_starter_author)]
    out_file = os.path.join(self.data_dir, '%sc.graphml' % self.id)
    self._process(sorted_items, out_file, nested=False)

  def _process(self, items, out_file, nested=False):
    self.nodes = []
    self.links = OrderedDict()
    self.seq = 0
    for item in items:
      post_a_idx = self._find_or_append_node(item.post_author)
      parent_a_idx = self._find_or_append_node(item.parent_author)
      if (post_a_idx, parent_a_idx) not in self.links:
        self.links[(post_a_idx, parent_a_idx)] = 0
      self.links[(post_a_idx, parent_a_idx)] += 1
    g = nx.Graph()
    for idx, node in enumerate(self.nodes):
      g.add_node(idx, label=unicode(node))
    for k,v in self.links.items():
      g.add_edge(k[0], k[1], value=v)
    print '--- Writing file %s ---' % out_file
    nx.write_graphml(g, out_file, 'utf8')
    #Fix for networkx's idiocy
    with codecs.open(out_file, 'r', 'utf8') as fh:
      lines = fh.readlines()
    lines.pop(0)
    lines.insert(0, "<?xml version='1.0' encoding='utf8'?>\n")
    with codecs.open(out_file, 'w', 'utf8') as fh:
      fh.writelines(lines)

  def _find_or_append_node(self, value):
    try:
      return self.nodes.index(value)
    except ValueError:
      self.nodes.append(value)
      return len(self.nodes)