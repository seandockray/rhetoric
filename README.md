# rhetoric

Project located at [http://rhetoric.metadada.xyz](http://rhetoric.metadada.xyz)

An interface for browsing Hansard transcripts through noun-phrase usage. You need to have MongoDB installed and a database called _hansard_ filled with data from [https://github.com/seandockray/hansard](https://github.com/seandockray/hansard)

```
 git clone https://github.com/seandockray/rhetoric.git
 cd rhetoric 
 virtualenv venv
 source venv/bin/activate
 pip install -r requirements.txt
 nano app.conf
```
and edit the document:
```
PORT = 5000
MONGO_HOST = "localhost"
MONGO_PORT = 27017
CACHE_TYPE = "filesystem"
CACHE_DIR = "_api_cache"
```
and now you should be able to run it with:
```
python rhetoric/app.py
```

## Acknowledgments

The data for these charts is pulled from [Open Australia](http://www.openaustralia.org.au) in a simple script located at [https://github.com/seandockray/hansard](https://github.com/seandockray/hansard). The charts themselves are all done with D3, using code from [examples in the D3 Gallery](https://github.com/d3/d3/wiki/Gallery) with minor modification.