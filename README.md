# Readme

This API aims to search for tweets with regard to a keyword you specify and summarize them into a .avi video.

## Usage

To use this API, all packages you need is `python 3`, `Twython` and `pillow`. You need also install `FFMPEG` on your computer and have twitter keys and tokens (put them in the file 'keys').

After you have all the dependencies ready, let's start with some fun demo. To run the demo, just type `python twitter_video_generator.py` and you can find the videos in directory 'twitter_videos.'

If you would like to specify your own keywords for searching, just change the elements in twitter_video_generator.py. 
```
if __name__ == '__main__':
    keys = ["preselect", "quit"]   # change here but please reserve the 'quit' in the last
    workflow(keys)
```

## API structure

The program consists of one producer which continuously provides list of tweets with regard to the sprcified keywords, and three consumers whose work is generating videos using those tweets. So this API can reponse to any amount of user requests as long as the burst is not overwhelmingly large because search for tweets won't take much time and one thread is enough for real-time reponsing. Meanwhile, the three consumer threads will work together to generate the videos demanded by users in a reasonable period of time.

![alt](./structure.png)

## Results

![pic](./twitter_images/tornado/tornado_1.png)

[demo video](./twitter_videos/tornado.avi)
