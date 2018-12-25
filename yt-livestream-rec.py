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
            raise Exception("{num_results} livestreams airing on channel, weird and unhandled, exiting.")
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
    # This is buggy af below - sometimes the pipes just don't receive any stdout/stderr even if the process runs
    # try:
    #     ytdl = subprocess.Popen(["youtube-dl.exe", yt_video_url,
    #                              "-o", "rec/%(title)s.%(ext)s"],
    #                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #     # While the process is not finished/terminated...
    #     while ytdl.poll() is None:
    #         try:
    #             # Attempt to communicate with the process for 1 second
    #             stdout, stderr = ytdl.communicate(input=None, timeout=1)
    #         except subprocess.TimeoutExpired as e:
    #             stdout, stderr = e.stdout, e.stderr
    #         # Handle youtube-dl and, by extension, ffmpeg output
    #         if stdout:
    #             output_lines = stdout.decode("utf-8").splitlines()
    #             for output_line in output_lines:
    #                 # TODO: Match lines and only output ones of interest
    #                 print(f"{output_line}")
    #         if stderr:
    #             # Display any error output
    #             error_lines = stderr.decode("utf-8").splitlines()
    #             for error_line in error_lines:
    #                 print(f"{error_line}")
    # except KeyboardInterrupt:
    #     # Terminate the background ytdl process and re-raise KeyboardInterrupt
    #     ytdl.terminate()
    #     raise


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

    print(f"'{channel_name}' are livestreaming '{title}' [{video_id}]")
    print(f"Downloading '{video_id}'...")
    try:
        download_livestream(video_id)
    except KeyboardInterrupt:
        print("Download interrupted by user")
