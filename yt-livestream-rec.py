"""yt-livestream-rec

Usage:
    yt-livestream-rec.py <channel_id>
"""

import signal
import subprocess
import sys
import time
from pathlib import Path

import requests
from docopt import docopt


api_key_p = Path(__file__).parent / "api.key"


class BadApiResponseException(Exception):
    pass


class NoLivestreamException(Exception):
    pass


def load_api_key(api_key_path):
    try:
        api_key = api_key_p.read_text(encoding="utf-8").rstrip()
        return api_key
    except FileNotFoundError:
        print(f"No api.key found... exiting.")
        sys.exit(2)


def get_livestream(api_key, yt_channel_id):
    yt_api_search_endpoint = "https://www.googleapis.com/youtube/v3/search"
    yt_api_search_params = {"part": "snippet",
                            "type": "video",
                            "eventType": "live",
                            "channelId": yt_channel_id,
                            "key": api_key}
    api_resp = requests.get(yt_api_search_endpoint, params=yt_api_search_params)
    if api_resp.status_code == 200:
        resp_json = api_resp.json()
        num_results = int(resp_json["pageInfo"]["totalResults"])
        if num_results == 0:
            raise NoLivestreamException()
        elif num_results == 1:
            # Extract livestream information from json
            item = resp_json["items"][0]
            return item["snippet"]["channelTitle"], item["snippet"]["title"], item["id"]["videoId"]
        else:
            raise Exception("{num_results} livestreams airing on channel, this is weird and unhandled... exiting.")
            sys.exit(1)
    else:
        raise BadApiResponseException(f"Bad response status '{api_resp.status_code}':\n{api_resp.text}")


def poll_for_livestream(api_key, video_id):
    i, i_max, sleep_interval = 0, 20, 30
    while True:
        try:
            i += 1
            channel_name, title, video_id = get_livestream(api_key, yt_channel_id)
            return channel_name, title, video_id
        except NoLivestreamException:
            if i < i_max:
                time.sleep(sleep_interval)
            else:
                raise


def download_livestream(yt_video_id):
    # TODO: Consider importing youtube-dl and using it as a module instead
    yt_video_url = f"https://www.youtube.com/watch?v={yt_video_id}"
    subprocess.run(["youtube-dl.exe", "-f", "best", yt_video_url, "-o", "rec/%(title)s.%(ext)s"])


if __name__ == '__main__':
    args = docopt(__doc__)
    yt_channel_id = args["<channel_id>"]

    print(f"Loading API key...")
    api_key = load_api_key(api_key_p)

    print(f"Polling for livestream on YouTube channel '{yt_channel_id}'...")
    try:
        channel_name, title, video_id = poll_for_livestream(api_key, yt_channel_id)
    except NoLivestreamException:
        print("No livestream found whilst polling... exiting.")
        sys.exit(3)
    except KeyboardInterrupt:
        print("Polling cancelled by user... exiting.")
        sys.exit(4)

    print(f"'{channel_name}' are livestreaming '{title}' [{video_id}]")
    print(f"Downloading '{video_id}'...")
    try:
        download_livestream(video_id)
    except KeyboardInterrupt:
        print("Download cancelled by user")
