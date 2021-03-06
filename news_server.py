from flask import Flask, request, session, redirect, url_for, render_template
from Article import Article
import requests
import pymongo
from xml.etree import ElementTree


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(SECRET_KEY='sd*&^!@#*123987')
    client = pymongo.MongoClient("mongodb+srv://news:123@cluster0-avowj.mongodb.net/test?retryWrites=true")
    db = client["newsapp"]
    #update_index(db)

    @app.route('/')
    def index():
        if 'username' in session:
            index_articles = db["index_articles"]
            articles = []
            for item in index_articles.find({}, {
                "_id": 0,
                'source': 1,
                'title': 1,
                'url': 1,
                'topImage': 1,
                'text': 1,
                'keywords': 1,
                'tags': 1,
                'time': 1
                }):
                articles.append(item)
                hot_word = trending() # hot_word is a dictionary, element:{word: weight}
            return render_template('articles.html', articles=articles, hot_words=hot_word.keys())
        return render_template('login.html')

    @app.route('/search', methods=['POST', 'GET'])
    def search():
        if 'username' in session:
            payload = {'q': request.form['keyword'], 'from': '2018-10-20','sortBy': 'publishedAt', 'apiKey': 'eb4ad8625c5b4f57bb62f8c95601038a'}
            r = requests.get('https://newsapi.org/v2/everything', params=payload)
            articles = []
            # TODO: make into Article objects as in update_index()
            # This way, we can also have the time value for articles from search.
            for obj in r.json()['articles']:
                temp = {}
                temp['title'] = obj['title']
                temp['source'] = ''
                temp['url'] = obj['url']
                temp['topImage'] = obj['urlToImage']
                articles.append(temp)
            return render_template('articles.html', articles=articles)
        return 'You are not logged in'

    @app.route('/login', methods=['POST', 'GET'])
    def login():
        if request.method == 'POST':
            if valid_login(db):
                session['username'] = request.form['username']
                return redirect(url_for('index'))
            else:
                return 'Invalid username/password'
        else:
            return render_template('login.html')

    @app.route('/signup', methods=['POST', 'GET'])
    def signup():
        user_info = db["user_info"]
        if request.method == 'POST':
            if user_info.find({'username': request.form['username']}).count() > 0:
                return 'the username has been used!'
            user_info.insert_one({'username': request.form['username'], 'password': request.form['password']})
            return 'insert success!'
        else:
            return 'use post to signup!'

    @app.route('/logout')
    def logout():
        # remove the username from the session if it's there
        session.pop('username', None)
        return redirect(url_for('index'))

    return app


def valid_login(db):
    user_info = db["user_info"]
    cursor = user_info.find({'username': request.form['username'], 'password': request.form['password']})
    if cursor.count() > 0:
        return True
    return False


def trending():
    TRENDING_URL = 'http://www.google.com/trends/hottrends/atom/feed?pn=p1'
    r = requests.get(TRENDING_URL)
    root = ElementTree.fromstring(r.content)
    res = {}
    for channel in root[0].findall('item'):
        tem = channel.find('{https://trends.google.com/trends/hottrends}approx_traffic').text.split('+')[0]
        tem = tem.split(',')
        weight = ''
        for i in tem:
            weight += i
        res[channel.find('title').text] = int(weight)
    return res


def update_index(db):
    print('updating main page...')
    payload = {'country': 'US', 'apiKey': 'eb4ad8625c5b4f57bb62f8c95601038a'}
    r = requests.get('https://newsapi.org/v2/top-headlines', params=payload)
    raw_json = r.json()
    index_articles = db["index_articles"]
    index_articles.delete_many({})
    for item in raw_json['articles']:
        article = Article(item['url'])
        article.build()
        index_articles.insert_one({
            'source': article.source_url,
            'title': article.title,
            'url': article.url,
            'topImage':article.top_image,
            'text':article.text,
            'keywords':article.keywords,
            'tags': article.tags,
            'time': article.time
            })
    print('update finished!')

# the code below is executed if the request method
# was GET or the credentials were invalid
# return render_template('login.html', error=error)


if __name__ == '__main__':
    app = create_app()
    app.run()