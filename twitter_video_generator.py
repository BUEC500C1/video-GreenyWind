import concurrent.futures
import configparser
import logging
import os
import queue
import re
import signal
import subprocess
import textwrap
import time
import threading
# import the twython libraries for using Twitter APIs
from twython import Twython
from twython import TwythonError
# import PIL packages for image generation
from PIL import Image, ImageDraw, ImageFont

MAX_TWEETS = 20
# TIMEOUT = 10

# def time_out():
#     print("You didn't enter anything in 10 seconds, \
#         so it is timed-out. Try again later.")
#     time.sleep(0.01)  # siwtch to consumer thread

# # set time_out as the interruption dealing function for SIGALRM
# signal.signal(signal.SIGALRM, time_out)

'''
A public queue/cache to store the twitter lists genrated by
the producer (generate_twitter_list) and provide them
to the consumer (generate_video)
'''
class messageQueue(queue.Queue):

    def __init__(self):
        super().__init__(maxsize=5)  # cache 10 messages at most

    def get_twitter_list(self):

        logging.info('in func get twiiter list: ' + str(self.qsize()))
        twitter_list = self.get()  # read a twitter list from the cache
        logging.info('in func get twitter list: ' + str(self.qsize()))
        return twitter_list

    def set_twitter_list(self, twitter_list):

        logging.info('in func set twitter list: ' + str(self.qsize()))
        self.put(twitter_list)  # put the twitter list into cache
        logging.info('in func set twitter list: ' + str(self.qsize()))

'''
A warped class for tweet searching and processing
'''
class twitter_processor():

    def __init__(self):
        
        config = configparser.ConfigParser()
        config.read('keys')
        self.consumer_key = config['auth']['consumer_key']
        self.consumer_secret = config['auth']['consumer_secret']
        self.access_token = config['auth']['access_token']
        self.access_token_secret = config['auth']['access_secret']

    def filter(self, text):  # delete non-sense characters from the tweet
        
        text = re.sub('RT \@+\w+\:','',text)  #delete head of retweet
        text = re.sub('\#+\w+\s','',text)     #delete hashtag
        text = re.sub('https://t.co/+\w+.','',text)  #delete url
        text = re.sub('\@+\w+(\\n|\s)','',text)      #delete @people  
        text = re.sub('\n','',text)                  #delete \n
        return text

    def generate_twitter_list(self, keyword):
        
        logging.info('in func generate twitter list')
        twitter_list = [keyword]
        hash_list = []
        # set up the twitter api
        APP_KEY= self.consumer_key
        APP_SECRET = self.consumer_secret
        OAUTH_TOKEN = self.access_token
        OAUTH_TOKEN_SECRET = self.access_token_secret
        twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

        SUPPORTED_LANGUAGE = ['zh', 'zh-Hant', 'en', 'fr', 'de', 'it',  # supported languages
                        'ja', 'ko', 'pt', 'es', 
                        ]
        try:
            results = twitter.cursor(twitter.search, q=keyword, result_type = 'recent'
                                , count = MAX_TWEETS, include_entities = True)
            for idx, status in enumerate(results):  # 'results' is a generator. It yields tweet objects
                if idx < MAX_TWEETS:
                    content={}
                    content['lang'] = status['lang']
                    hashValue = hash(status["text"])  #if texts are identical, hash value is same
                    if content['lang'] in SUPPORTED_LANGUAGE:
                        if (hashValue not in hash_list) : #or (content["hash"] in twitter_list and content['text'] not in twitter_list)
                            hash_list.append(hashValue)
                            content["text"] = self.filter(status['text'])
                            content["entities"] = status['entities']
                            twitter_list.append(content)
                else:
                    break
        except TwythonError as e:
            if e.error_code == 429:
                print("Too many requests!")
            else:
                print(e.error_code)

        logging.info('in func generate twitter list: about to return')
        return twitter_list

    def twilist2img(self, twitter_list):

        logging.info('in func twilist2img')
        keyword = twitter_list[0]
        dir_path = './twitter_images/' + keyword + '/'
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)
        font = ImageFont.truetype('./arial.ttf', 16)
        for i in range(1, len(twitter_list)):
            background = Image.new('RGBA', (1000, 750), (153, 217, 234, 255))
            img = ImageDraw.Draw(background)
            txt = twitter_list[i]["text"]
            lines = textwrap.wrap(txt, width=120)
            x, y = 10, 75
            for line in lines:
                width, height = font.getsize(line)
                img.text(((x), y), line, font=font, fill="black")
                y += 20
            background.save(dir_path + keyword + '_' + str(i) + '.png')
        logging.info('in func twilist2img: ' + twitter_list[0] + ' about to return')

    def img2video(self, keyword):

        logging.info('in func img2video')
        file_name =  './twitter_images/' + keyword +'/' + keyword + '_' + '%d' + '.png'
        avi =  "./twitter_videos/" + keyword + ".avi"
        subprocess.call(['ffmpeg', '-framerate', '0.3', '-i', file_name, avi])
        logging.info('in func img2video: ' + keyword + ' about to return')

'''
The producer: continues acquiring keywords from a given list,
 generating twitter lists and storing them into the queue/cache
 until meets 'quit'.
'''
def command_line_inteface(keys, msgs, event):

    logging.info('Producer: in producer')
    searcher = twitter_processor()
    # while (not event.is_set()):
    # # continue listening to the commandline requests unless user entered 'quit'
        # signal.alarm(TIMEOUT)  # wait for input for 10 seconds
        # key = input("Please enter a key you would like to search:")
        # signal.alarm(0)  # if success, disable the alarm
    for key in keys:
        if key == 'quit':
            logging.info('Producer: the key is quit')
            logging.info('Producer: about to set event')
            event.set()
            logging.info('Producer: event is set: ' + str(event.is_set()))
        else:
            logging.info('Producer: the key is ' + key)
            logging.info('Producer: about to generate twitter_list')
            twitter_list = searcher.generate_twitter_list(key)
            logging.info('Producer: about to set message queue ' + twitter_list[0]
                        + ': ' + str(msgs.qsize()))
            msgs.set_twitter_list(twitter_list)
            logging.info('Producer: message queue ' + twitter_list[0]
                        + ' set: ' + str(msgs.qsize()))

    logging.info('Producer: all work done')

'''
The consumer: continue generating video according to the twitter lists
in the queue/cache until the producer meets keyword 'quit' and the
queue/cache is empty (all works are done)
'''
def generate_video(msgs, event, thread_num):

    logging.info('Consumer ' + str(thread_num) + ': in consumer')
    processor = twitter_processor()
    while ((not event.is_set()) or (not msgs.empty())):
    # stop only when the message queue is empty and user entered 'quit'
        logging.info('Consumer' + str(thread_num) + ': the message queue is '
            + str( msgs.empty()) + ' empty and the event is '
            + str(event.is_set()) + ' set')
        logging.info('Consumer' + str(thread_num) 
            + ': about to get twitter list from message queue: '
            + str(msgs.qsize()))
        twitter_list = msgs.get_twitter_list()
        logging.info('Consumer' + str(thread_num)
            + ': twitter list acquired: ' + str(msgs.qsize()))
        logging.info('Consumer' + str(thread_num)
            + ': about to generate imgs of ' + twitter_list[0])
        processor.twilist2img(twitter_list)
        logging.info('Consumer' + str(thread_num)
            + ': about to generate video of ' + twitter_list[0])
        processor.img2video(twitter_list[0])

    logging.info('Consumer' + str(thread_num) + ': all work done')

'''
The function generates thread(s) for producer and consumer to accompolish
the task, the goal of which is summarizing recent tweets of a specific
 keyword and generating corresponding video.
'''
def workflow(keys):
    # print("Welcome! Thanks for using our twitter message video generator!")
    # print("-------------------====== Usage Info ======-------------------")
    # print("")

    msgs = messageQueue()
    event = threading.Event()

    producer = threading.Thread(target=command_line_inteface, args=(keys, msgs, event), daemon=False)
    logging.info('Main: about to create producer')
    producer.start()
    logging.info('Main: producer has been started')
    logging.info('Main: about to create consumers')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for tnumber in range(1, 4):
            executor.submit(generate_video, msgs, event, tnumber)
            logging.info('Main: consumer ' + str(tnumber) + "'s task is submitted")

    logging.info("Main: Exiting...")
    return True

if __name__ == '__main__':

    #logging.getLogger().setLevel(logging.INFO)
    keys = ['preselect', 'coronavirus', 'tornado', 'face+mask', 'kitty', 'puppy', 'punderworld', 'watercolor'
        , 'Louvre', 'Mecca', 'Dows', 'Bill+Gates', 'quit']
    workflow(keys)