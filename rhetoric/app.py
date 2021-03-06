# -*- coding: utf-8 -*-
"""
Some initial ideas for noun phrase queries (which is parsed from Hansard data in app.py)
"""
import os, sys
import getopt
import re
from bson.code import Code

from flask import Flask, request, redirect, jsonify, url_for
from flask.ext.cache import Cache  

from mako.template import Template
from pymongo import MongoClient

app = Flask(__name__)
app.config.from_pyfile('../app.conf', silent=True)
app.cache = Cache(app)
client = MongoClient(app.config['MONGO_HOST'], app.config['MONGO_PORT'], connect=False)
db = client.hansard

def make_key ():
  """Make a key that includes GET parameters."""
  """ https://github.com/thadeusb/flask-cache/issues/104 """
  return request.full_path

def get_speaker_phrase_counts(speakername, how_many=25, from_date=None, to_date=None):
    ''' A list of phrases by number of occurrences ''' 
    query = {"speakername": speakername}
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    print query
    map = Code("function () {"
                "   emit(this.phrase,1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1).limit(how_many):
        yield doc


def get_phrase_speaker_counts(phrase, how_many=25, from_date=None, to_date=None):
    ''' A list of speakers by number of occurrences for a phrase '''  
    query = {"phrase": phrase}
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    map = Code("function () {"
                "   emit(this.speakername,1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1).limit(how_many):
        yield doc

def get_phrase_speaker_heading_counts(phrase, speakername):
    ''' A list of speakers by number of occurrences for a phrase '''  
    query = {"phrase": phrase, "speakername": speakername}
    map = Code("function () {"
                "   var key = {title:this.headingtitle.substring(0,64) + ' ('+ this.date + ')', speechid:this.speechid, house:this.house};"
                "   emit(key ,1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1):
        "_id: {speechid:..., house:..., title:...}, value:..."
        yield doc

def get_heading_phrase_counts(headingtitle, how_many=25):
    ''' A list of headings by number of occurrences for a phrase '''
    date = None
    if headingtitle[-1]==')' and headingtitle[-4]=='-' and headingtitle[-12]=='(':
        date = headingtitle[-11:-1]
        headingtitle = headingtitle[:-12].strip()  
    #query = {"headingtitle": { "$regex": "^"+headingtitle+".*" }}
    query = {"headingtitle": headingtitle}
    if date:
        query["date"] = date.strip()
    map = Code("function () {"
                "   emit(this.phrase,1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1).limit(how_many):
        yield doc

def get_phrase_heading_counts(phrase, speakername=None, how_many=25, from_date=None, to_date=None):
    ''' A list of headings by number of occurrences for a phrase '''  
    query = {"phrase": phrase}
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    if speakername:
        query["speakername"] = speakername
    map = Code("function () {"
                "   emit(this.headingtitle.substring(0,64) + ' ('+ this.date + ')',1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1).limit(how_many):
        yield doc

def get_phrase_usage_compiled(phrase, speakername=None, from_date=None, to_date=None):
    ''' A list of headings by number of occurrences for a phrase '''  
    query = {"phrase": phrase}
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    if speakername:
        query["speakername"] = speakername
    map = Code("function () {"
                "   emit({speakername: this.speakername, headingtitle: this.headingtitle.substring(0,64) + ' ('+ this.date + ')', url: this.house + '/' + this.speechid + '.html'},1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find():
        yield doc


def get_phrase_usage(phrase, speakername=None):
    ''' A list of phrases by number of occurrences '''
    query = {"phrase": phrase}
    if speakername:
        query["speakername"] = speakername
    map = Code("function () {"
                "   emit(this.date.substring(0,7),1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("_id", 1):
        yield doc

def get_detailed_phrase_usage(phrase, speakername=None):
    ''' A list of phrases by number of occurrences ordered by date '''
    query = {"phrase": phrase}
    if speakername:
        query["speakername"] = speakername
    map = Code("function () {"
                "   emit( this.date,1 );"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("_id", 1):
        yield doc

def get_phrases_containing(fragment, how_many=25, from_date=None, to_date=None, speakername=None):
    ''' A list of phrases containing some text '''  
    #query = {"phrase":re.compile(".*"+fragment+".*", re.IGNORECASE)}
    query = {"phrase":re.compile("(^|\s)("+fragment+")($|\s)", re.IGNORECASE)}
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    if speakername:
        query["speakername"] = speakername
    map = Code("function () {"
                "   emit(this.phrase,1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1).limit(how_many):
        yield doc


@app.route('/', methods=['GET','POST'])
@app.route('/index.html', methods=['GET','POST'])
@app.route('/home', methods=['GET','POST'])
def index():
    if request.form and 'query' in request.form:
        query = re.sub(r'[^a-zA-Z0-9\s]','', request.form['query'])
        return redirect(url_for('phrase_variations', fragment=query.lower()))
    else:
        t = Template(filename='templates/rhetoric/index.html')
        return t.render()

@app.route("/speaker/<speakername>")
def speaker_phrases(speakername):
    title = "what %s spoke about" % speakername
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        data_url = url_for('api_speaker_phrases', speakername=speakername, from_date=from_date, to_date=to_date)
        title += " between %s and %s" % (from_date, to_date)
    else:
        data_url = url_for('api_speaker_phrases', speakername=speakername)
    t = Template(filename='templates/rhetoric/bar-chart.html')
    return t.render(
        data_url=data_url,
        title=title,
        linked_title=title
    )

@app.route("/api/v1.0/speaker/<speakername>")
@app.cache.cached(key_prefix=make_key, timeout=86400) 
def api_speaker_phrases(speakername):
    ret = {"items":[]}
    results = get_speaker_phrase_counts(speakername, how_many=50)
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('phrase_speakers', phrase=str(r["_id"]))
            })
    return jsonify(**ret)

@app.route("/phrase/<phrase>/speakers")
def phrase_speakers(phrase):
    title = "People who said '%s'" % phrase
    linked_title = "People who said '<a href='%s'>%s</a>'" % (url_for('phrase_usage',phrase=phrase), phrase)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        data_url = url_for('api_phrase_speakers', phrase=phrase, from_date=from_date, to_date=to_date)
        title += " between %s and %s" % (from_date, to_date)
    else:
        data_url = url_for('api_phrase_speakers', phrase=phrase)
    t = Template(filename='templates/rhetoric/bubble-chart.html')
    return t.render(
        data_url=data_url,
        title = title,
        linked_title=linked_title
    )

@app.route("/api/v1.0/phrase/<phrase>/speakers")
@app.cache.cached(key_prefix=make_key, timeout=86400)
def api_phrase_speakers(phrase):
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        results = get_phrase_speaker_counts(phrase, how_many=50, from_date=from_date, to_date=to_date)
    else:
        results = get_phrase_speaker_counts(phrase, how_many=50)
    ret = {"items":[]}
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('phrase_speaker_headings', phrase=phrase, speakername=str(r["_id"]))
            })
    return jsonify(**ret)

@app.route("/phrase/<phrase>/speaker/<speakername>")
def phrase_speaker_headings(phrase, speakername):
    title = "where %s said '%s'" % (speakername, phrase)
    linked_title = "where <a href='%s'>%s</a> said '<a href='%s'>%s</a>'" % (
        url_for('speaker_phrases', speakername=speakername), speakername, 
        url_for('phrase_usage', phrase=phrase), phrase)
    data_url = url_for('api_phrase_speaker_headings', phrase=phrase, speakername=speakername)
    t = Template(filename='templates/rhetoric/bubble-chart.html')
    return t.render(
        data_url=data_url,
        title = title,
        linked_title=linked_title
    )

@app.route("/api/v1.0/phrase/<phrase>/speaker/<speakername>")
@app.cache.cached(key_prefix=make_key, timeout=86400)
def api_phrase_speaker_headings(phrase, speakername):
    results = get_phrase_speaker_heading_counts(phrase, speakername)
    ret = {"items":[]}
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]["title"]), 
            "num": int(r["value"]),
            #"url": url_for('heading_phrases', headingtitle=str(r["_id"]["title"]))
            "url": 'http://rhetoric.metadada.xyz/speeches/'+r["_id"]["house"]+"/"+r["_id"]["speechid"]+".html"
            })
    return jsonify(**ret)

@app.route("/phrase/<phrase>/headings")
def phrase_headings(phrase):
    title = "where '%s' was said" % phrase
    linked_title = "where '<a href='%s'>%s</a>' was said" % (url_for('phrase_usage', phrase=phrase), phrase)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        data_url = url_for('api_phrase_headings', phrase=phrase, from_date=from_date, to_date=to_date)
        title += " between %s and %s" % (from_date, to_date)
        linked_title += " between %s and %s" % (from_date, to_date)
    else:
        data_url = url_for('api_phrase_headings', phrase=phrase)
    t = Template(filename='templates/rhetoric/bubble-chart.html')
    return t.render(
        title = title,
        linked_title = linked_title,
        data_url=data_url
    )

@app.route("/api/v1.0/phrase/<phrase>/headings")
@app.cache.cached(key_prefix=make_key, timeout=86400)
def api_phrase_headings(phrase):
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        results = get_phrase_heading_counts(phrase, how_many=50, from_date=from_date, to_date=to_date)
    else:
        results = get_phrase_heading_counts(phrase, how_many=50)
    ret = {"items":[]}
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('heading_phrases', headingtitle=str(r["_id"]))
            })
    return jsonify(**ret)


@app.route("/phrase/<phrase>")
def phrase_usage_compiled(phrase):
    title = "mapping the use of '%s'" % phrase
    linked_title = "mapping the use of '<a href='%s'>%s</a>'" % (url_for('phrase_usage_detailed', phrase=phrase), phrase)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        data_url = url_for('api_phrase_usage_compiled', phrase=phrase, from_date=from_date, to_date=to_date)
        title += " between %s and %s" % (from_date, to_date)
        linked_title += " between %s and %s" % (from_date, to_date)
    else:
        data_url = url_for('api_phrase_usage_compiled', phrase=phrase)
    t = Template(filename='templates/rhetoric/treemap.html', input_encoding='utf-8', output_encoding='utf-8')
    return t.render(
        title = title,
        linked_title = linked_title,
        data_url=data_url,
        phrase=phrase
    )

def build_treemap_data(data, level1, level2, urlkey):
    ''' Builds a treemap 2 levels deep '''
    data = list(data)
    treemap = {"name": "usage", "children":[]}
    level1_keys = list(set([d['_id'][level1] for d in data]))
    tmp_data = {}
    for k in level1_keys:
        tmp_data[k] = []
    for d in data:
        k = d['_id'][level1]
        tmp_data[k].append({
            "name": d['_id'][level2],
            "value": d['value'],
            "url": d['_id'][urlkey]
            })
    for d in tmp_data:
        treemap["children"].append({
            "name": d, 
            "children": tmp_data[d]
            })
    return treemap


@app.route("/api/v1.0/phrase/<phrase>")
@app.cache.cached(key_prefix=make_key, timeout=86400)
def api_phrase_usage_compiled(phrase):
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        # Flips the levels so we see heading on top when narrowed by date
        results = get_phrase_usage_compiled(phrase, from_date=from_date, to_date=to_date)
        ret = build_treemap_data(results, 'headingtitle', 'speakername', 'url')
    else:
        results = get_phrase_usage_compiled(phrase)
        ret = build_treemap_data(results, 'speakername', 'headingtitle', 'url')
    return jsonify(**ret)


@app.route("/heading/<headingtitle>/phrases")
def heading_phrases(headingtitle):
    title = "phrases used during '%s'" % headingtitle
    data_url = url_for('api_heading_phrases', headingtitle=headingtitle)
    t = Template(filename='templates/rhetoric/bar-chart.html')
    return t.render(
        data_url=data_url,
        title = title
    )

@app.route("/api/v1.0/heading/<headingtitle>/phrases")
@app.cache.cached(key_prefix=make_key, timeout=86400)
def api_heading_phrases(headingtitle):
    results = get_heading_phrase_counts(headingtitle, how_many=50)
    ret = {"items":[]}
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('phrase_speakers', phrase=str(r["_id"]))
            })
    return jsonify(**ret)

@app.route("/phrase/<phrase>/usage")
def phrase_usage(phrase):
    if ',' in phrase:
        phrases = phrase.split(',')
        title = ' v. '.join(phrases)
        t = Template(filename='templates/rhetoric/multi-line-chart.html')
        return t.render(
            data_url=url_for('api_phrase_usage', phrase=phrase),
            title = title
        )
    else:
        title = "when and how often '%s' was said" % phrase
        t = Template(filename='templates/rhetoric/line-chart.html')
        return t.render(
            data_url=url_for('api_phrase_usage', phrase=phrase),
            title = title
        )

@app.route("/api/v1.0/phrase/<phrase>/usage")
@app.cache.cached(key_prefix=make_key, timeout=86400)
def api_phrase_usage(phrase):
    if ',' in phrase:
        phrases = phrase.split(',')
        ret = {"items":[]}
        for p in phrases:
            results = get_phrase_usage(p)
            for r in results:
                ret["items"].append({
                    "Phrase": p,
                    "Month": str(r["_id"]), 
                    "Usage": int(r["value"])
                })
    else:
        ret = {"filter_url": url_for('phrase_headings', phrase=phrase, from_date="FROM_DATE", to_date="TO_DATE"), "items":[]}
        results = get_phrase_usage(phrase)
        for r in results:
            ret["items"].append({
                "Month": str(r["_id"]), 
                "Usage": int(r["value"])
            })
    return jsonify(**ret)


@app.route("/phrase/<phrase>/usage/detailed")
def phrase_usage_detailed(phrase):
    title = "when and how often '%s' was said" % phrase
    t = Template(filename='templates/rhetoric/calendar.html')
    return t.render(
        data_url=url_for('api_phrase_usage_detailed', phrase=phrase),
        title = title
    )

@app.route("/api/v1.0/phrase/<phrase>/usage/detailed")
@app.cache.cached(key_prefix=make_key, timeout=86400)
def api_phrase_usage_detailed(phrase):
    ret = {"filter_url": url_for('phrase_headings', phrase=phrase, from_date="FROM_DATE", to_date="TO_DATE"), "items":[]}
    results = get_detailed_phrase_usage(phrase)
    for r in results:
        ret["items"].append({
            "Date": str(r["_id"]), 
            "Usage": int(r["value"]),
            "url": url_for('phrase_usage_compiled', phrase=phrase, from_date=str(r["_id"]), to_date=str(r["_id"]))
        })
    return jsonify(**ret)


@app.route("/phrase/<fragment>/variations")
def phrase_variations(fragment):
    title = "phrases containing '%s'" % fragment
    t = Template(filename='templates/rhetoric/bar-chart.html')
    return t.render(
        data_url=url_for('api_phrase_variations', fragment=fragment),
        title = title,
        linked_title = title
    )

@app.route("/api/v1.0/phrase/<fragment>/variations")
@app.cache.cached(key_prefix=make_key, timeout=86400)
def api_phrase_variations(fragment):
    ret = {"items":[]}
    results = list(get_phrases_containing(fragment, how_many=50))
    results = sorted(results, key=lambda k: k['_id']) 
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('phrase_usage_compiled', phrase=str(r["_id"]))
        })
    return jsonify(**ret)


if __name__=="__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=app.config['PORT'])

    """
    print 'get_speaker_phrase_counts("Christine Anne Milne")'
    get_speaker_phrase_counts("Christine Anne Milne")
    print 'get_speaker_phrase_counts("Christine Anne Milne", from_date="2006-02-08", to_date="2007-02-08")'
    get_speaker_phrase_counts("Christine Anne Milne", from_date="2006-02-08", to_date="2007-02-08")
    print 'get_phrase_speaker_counts("the government")'
    get_phrase_speaker_counts("the government")
    print 'get_phrase_usage("the government")'
    get_phrase_usage("the government")
    print 'get_phrase_usage("the government", speakername="Christine Anne Milne")'
    get_phrase_usage("the government", speakername="Christine Anne Milne")
    print 'get_phrases_containing("energy")'
    get_phrases_containing("energy")
    print 'get_phrases_containing("energy", speakername="Christine Anne Milne")'
    get_phrases_containing("energy", speakername="Christine Anne Milne")
    """