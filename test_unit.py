from twitter_video_generator import workflow

def test_pressure_test():
    keys = ['preselect', 'coronavirus', 'tornado', 'face+mask', 'kitty', 'puppy', 'punderworld', 'watercolor'
        , 'Louvre', 'Mecca', 'Dows', 'Bill+Gates', 'quit']
    workflow(keys)