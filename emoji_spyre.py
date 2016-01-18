# coding=utf-8
from __future__ import division
from spyre import server
import pandas as pd
import tweepy
import re
import numpy as np
import cnfg
import matplotlib.pyplot as plt
import os
import pattern.es
import pattern.fr
from textblob import TextBlob

pd.options.display.max_colwidth = 0

# Load Twitter authentification information
config = cnfg.load(".twitter_config")
auth = tweepy.OAuthHandler(config["consumer_key"],
                           config["consumer_secret"])
auth.set_access_token(config["access_token"],
                      config["access_token_secret"])
api = tweepy.API(auth)


def return_first_in_list(x):
    try:
        return x[0]
    except:
        return np.nan


def search_twitter(params):
    # Query = dropdown selection value
    query = params['words']
    max_tweets = 200
    # Search Twitter for the 200 most recent tweets with the selected query
    search_results = tweepy.Cursor(api.search, q=query).items(max_tweets)
    return search_results


def get_tweet_data(search_results):
    d = []
    for tweet in search_results:
        text = tweet.text
        num_followers = tweet.user.followers_count
        user_name = tweet.user.screen_name
        num_friends = tweet.user.friends_count
        num_retweets = tweet.retweet_count
        if not tweet.retweeted and 'RT @' not in tweet.text:
            retweeted = False
        else:
            retweeted = True
        d.append({'username': user_name, 'num_followers': num_followers, "num_friends": num_friends, "text": text,
                  "num_retweets": num_retweets, 'retweeted': retweeted})
    df = pd.DataFrame(d)
    return df


def remove_punctuation(text):
    return re.sub(ur"\p{P}+", "", text).lower()


def spanish_pos_tagger(text):
    return pattern.es.Sentence(pattern.es.parse(text, tokenize = True, chunks = False, relations=False, lemmata= False))


def french_pos_tagger(text):
    return pattern.fr.Sentence(pattern.fr.parse(text, tokenize = True, chunks = False, relations=False, lemmata= False))


def get_relevant_noun_phrase(nouns):
    emoji_index = nouns.index("emoji")
    noun_list = []
    for i, noun in enumerate(nouns):
        if  i == emoji_index + 1:
            noun_list.append(noun)
        else:
            pass
    return noun_list


def translate(language, word):
    try:
        blob = TextBlob(word[0])
        return blob.translate(from_lang = language, to='en')
    except:
        return np.nan


def get_english_emojis(df):
    df.text = df.text.map(lambda x: x.lower())
    df['emoji'] = df.text.map(lambda x: re.findall(r'why is there no(.*?)emoji', x))
    return df


def get_german_emojis(df):
    df.text = df.text.map(lambda x: x.lower())
    df['emoji'] = df.text.map(lambda x: re.findall(r'WARUM GIBT ES KEINE(.*?)EMOJI', x))
    #df.emoji = df.emoji.map(lambda x: translate("de", x))
    return df


def get_other_lang_emojis(df, pos_tagger, language):
    df.text = df.text.apply(remove_punctuation)
    df['sentence'] = df.text.apply(pos_tagger)
    df['nouns'] = df.sentence.map(lambda x: x.nouns)
    df.nouns = df.nouns.map(lambda x: [word.string for word in x])
    df['emoji'] = df.nouns.apply(get_relevant_noun_phrase)
    #df.emoji = df.emoji.map(lambda x: translate(language, x))
    return df


class EmojiApp(server.App):
    title = "Emoji requests"

    inputs = [{"type": "dropdown",
               "key": "words",
               "label": "Language",
               "options": [{"label": "English", "value": "why is there no emoji"},
                           {"label": "Spanish", "value": "por qué no hay emoji"},
                           {"label": "French", "value": "il devrait y avoir un emoji"},
                           {"label": "German", "value": "WARUM GIBT ES KEINE EMOJI"}],
               "action_id": "update_data"}]

    controls = [{"type": "hidden",
                 "id": "update_data"}]

    tabs = ["Plot", "Table"]

    outputs = [{"type": "plot",
                "id": "plot",
                "control_id": "update_data",
                "tab": "Plot"},
               {"type": "table",
                "id": "table_id",
                "control_id": "update_data",
                "tab": "Table",
                "on_page_load": "True"}]

    def getData(self, params):
        # Search Twitter for the 200 most recent tweets about emojis in the selected language
        search_results = search_twitter(params)

        # Go through list of tweets and collect relevant info into dataframe
        df = get_tweet_data(search_results)

        # Based on selected language, process tweets to extract asked for emoji
        if params['words'] == "why is there no emoji":
            df = get_english_emojis(df)
        elif params['words'] == "por qué no hay emoji":
            df = get_other_lang_emojis(df, spanish_pos_tagger, "es")
        elif params['words'] == "il devrait y avoir un emoji":
            df = get_other_lang_emojis(df, french_pos_tagger, "fr")
        elif params['words'] == "WARUM GIBT ES KEINE EMOJI":
            df = get_german_emojis(df)

        # Get only the first emoji asked for in tweet
        df.emoji = df.emoji.apply(return_first_in_list)
        df.emoji = df.emoji.replace(" ", np.nan)


        # Count up emojis requested and list users who made the request
        cum_df = df.groupby('emoji').sum()
        cum_df = cum_df.sort('num_followers', ascending=False)
        cum_df['emoji'] = cum_df.index
        cum_df = cum_df.reset_index(drop=True)
        grouped = df.groupby('emoji')
        df2 = grouped.aggregate(lambda x: list(x))
        df2['emoji'] = df2.index
        df2 = df2[['emoji', 'username']].reset_index(drop=True)
        df3 = df2.merge(cum_df, on="emoji", how="left")
        df3 = df3.sort("num_followers", ascending=False)
        df3 = df3[['emoji', "num_followers", 'num_retweets', "username"]]
        return df3

    def getPlot(self, params):
        # Search Twitter for the 200 most recent tweets about emojis in the selected language
        search_results = search_twitter(params)

        # Go through list of tweets and collect relevant info into dataframe
        df = get_tweet_data(search_results)

        # Based on selected language, process tweets to extract asked for emoji
        if params['words'] == "why is there no emoji":
            df = get_english_emojis(df)
        elif params['words'] == "por qué no hay emoji":
            df = get_other_lang_emojis(df, spanish_pos_tagger, "es")
        elif params['words'] == "il devrait y avoir un emoji":
            df = get_other_lang_emojis(df, french_pos_tagger, "fr")
        elif params['words'] == "WARUM GIBT ES KEINE EMOJI":
            df = get_german_emojis(df)

        # Get only the first emoji asked for in tweet
        df.emoji = df.emoji.apply(return_first_in_list)
        df.emoji = df.emoji.replace(" ", np.nan)

        # Plot sum of followers for each emoji request made and plot
        cum_df = df.groupby('emoji').sum()
        cum_df = cum_df.sort('num_followers', ascending=False)
        cum_df = cum_df[0:20]
        plt_obj = cum_df.num_followers.plot(kind='bar')
        plt.ylabel("Total number of followers")
        plt.title((params['words']).upper())
        fig = plt_obj.get_figure()
        return fig


if __name__ == '__main__':
    app = EmojiApp()
    app.launch(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
