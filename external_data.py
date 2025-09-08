import os
import tweepy
from textblob import TextBlob

class ExternalData:
    def __init__(self):
        TW_CONSUMER_KEY = os.getenv("TW_CONSUMER_KEY", "")
        TW_CONSUMER_SECRET = os.getenv("TW_CONSUMER_SECRET", "")
        TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN", "")
        TW_ACCESS_TOKEN_SECRET = os.getenv("TW_ACCESS_TOKEN_SECRET", "")
        try:
            auth = tweepy.OAuth1UserHandler(TW_CONSUMER_KEY, TW_CONSUMER_SECRET,
                                            TW_ACCESS_TOKEN, TW_ACCESS_TOKEN_SECRET)
            self.api = tweepy.API(auth)
        except:
            self.api = None

    def get_features(self, symbol="BTC"):
        score = 0
        if self.api:
            try:
                tweets = self.api.search_tweets(q=symbol, count=10, lang="en")
                for t in tweets:
                    score += TextBlob(t.text).sentiment.polarity
                score /= max(len(tweets),1)
            except:
                score = 0
        return {"sentiment": score}
