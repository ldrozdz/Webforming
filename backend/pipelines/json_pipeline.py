import json
from collections import Counter, OrderedDict
import os


class JsonPipeline(object):
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
    out_file = os.path.join(self.data_dir, '%sp.json' % self.id)
    self._process_flat(sorted_items, out_file)
    #tree
    out_file = os.path.join(self.data_dir, '%st.json' % self.id)
    self._process_nested(sorted_items, out_file)
    #exclude post
    thread_starter_author = filter(lambda i: i.type=='post', sorted_items)[0].post_author
    sorted_items = [i for i in sorted_items if (i.post_author!= thread_starter_author and i.parent_author!=thread_starter_author)]
    out_file = os.path.join(self.data_dir, '%sc.json' % self.id)
    self._process_flat(sorted_items, out_file)

  def _process_flat(self, items, out_file):
    self.nodes = []
    self.links = OrderedDict()
    self.seq = 0
    for item in items:
      post_a_idx = self._find_or_append_node(item.post_author)
      parent_a_idx = self._find_or_append_node(item.parent_author)
      if (post_a_idx, parent_a_idx) not in self.links:
        self.links[(post_a_idx, parent_a_idx)] = 0
      self.links[(post_a_idx, parent_a_idx)] += 1
    cnt_posts = Counter([_.post_author for _ in items])
    cnt_replies = Counter([_.parent_author for _ in items])
    json_nodes = [{'name': _, 'group':1, 'indegree': cnt_replies[_], 'outdegree': cnt_posts[_]} for _ in self.nodes]
    json_links = [{'source': k[0], 'target':k[1], 'value':v} for k,v in self.links.items()]
    print '--- Writing file %s ---' % out_file
    with open(out_file, 'w') as f:
      f.write(json.dumps({'nodes': json_nodes, 'links':json_links}, indent=2))

  def _process_nested(self, items, out_file):
    self.nodes = {}
    root = None
    for item in items:
      if item.type == 'post':
        root = item.post_id
      if not self.nodes.has_key(item.post_id):
        self.nodes[item.post_id] = {'name':item.post_author, 'content': item.content[:1024], 'children':[]}
      if item.parent_id:
        if self.nodes.has_key(item.parent_id):
          self.nodes[item.parent_id]['children'].append(self.nodes[item.post_id])
        else:
          self.nodes[item.post_id] = {'name':item.post_author, 'content': item.content[:1024], 'children':[]}
    self._remove_empty_children(self.nodes[root])
    print '--- Writing file %s ---' % out_file
    with open(out_file, 'w') as f:
      f.write(json.dumps(self.nodes[root], indent=2))

  def _find_or_append_node(self, value):
    try:
      return self.nodes.index(value)
    except ValueError:
      self.nodes.append(value)
      return len(self.nodes)

  def _remove_empty_children(self, node):
    if len(node['children'])>0:
      for child in node['children']:
        self._remove_empty_children(child)
    else:
      del node['children']