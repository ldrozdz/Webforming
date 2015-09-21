import string
import random
import datetime
import cairosvg
from flask import Flask, render_template, send_from_directory, request, make_response, flash
import sqlite3 as lite
import sys
from backend import transforming
import os

app = Flask(__name__)
app.config['DATA_DIR'] = '/var/lib/uwsgi/app/webforming'
app.secret_key = 'A5F8B139C65132B773E3AE380B5A5F9C101BA759115538E4589924EFD06C030D'
host = '127.0.0.1'
port = 9000

@app.route('/', methods=['GET','POST'])
def index():
  #Crawl
  if request.method=='POST':
    _crawl()
  data = []
  #Display index
  con = lite.connect(os.path.join(app.config['DATA_DIR'],'wbfmng.db'))
  with con:
    cur = con.cursor()
    cur.execute('select id,url,timestamp from crawls where status=0')
    for r in cur.fetchall():
      data.append({'id': r[0],
        'url':  r[1],
        'timestamp': r[2]})
  return render_template('index.html', batches=data)

def _crawl():
  urls = [_.strip() for _ in request.form['urls'].split()]
  src = request.form['source'].strip()
  con = lite.connect(os.path.join(app.config['DATA_DIR'],'wbfmng.db'))
  with con:
    cur = con.cursor()
    cur.execute('select count(*) from crawls')
    cnt = cur.fetchone()[0]
    for url in urls:
      id = _get_hash(cnt)
      timestamp = datetime.datetime.now()
      error = "Unfortunately we couldn't parse your data (error at the %s stage, error message: %s on line %s)."
      status = 2
      # crawl
      try:
        transforming.crawl(id, src, url, app.config['DATA_DIR'])
        cnt += 1
        status = 1
        # export
        try:
          transforming.export(id, app.config['DATA_DIR'])
          status = 0
        except Exception as e:
          flash(error % ("export", e, sys.exc_info()[-1].tb_lineno))
      except Exception as e:
        flash(error % ("crawl", e, sys.exc_info()[-1].tb_lineno))
      if status < 2:
        con.execute('insert into crawls values(?,?,?,?)', (id, url, timestamp, status))

def _get_hash(suffix):
  char_set = string.ascii_lowercase + string.digits
  return ''.join(random.sample(char_set*4,4)) + str(suffix)

@app.route('/graph/<id>')
def graph(id):
  return render_template('graph.html', id=id)

@app.route('/tree/<id>')
def tree(id):
  return render_template('tree.html', id=id)

@app.route('/radial/<id>')
def radial(id):
  return render_template('radial.html', id=id)

@app.route('/data/<filename>')
def serve_file(filename):
  return send_from_directory(app.config['DATA_DIR'], filename)

@app.route('/export', methods=['POST'])
def export_file():
  data = request.form['data']
  fname = request.form['filename']
  png = cairosvg.svg2png(data)
  response = make_response(png)
  response.headers["Content-Disposition"] = "attachment; filename=%s.png" % fname
  return response

@app.route('/test')
def test():
  print 'Hello world!'
  return 'Hello world!'

if __name__ == '__main__':
  app.run(host=host, port=port, debug=True)
