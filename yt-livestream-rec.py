import signal
import subprocess
import sys
from pathlib import Path

import colorama
import requests


colorama.init(autoreset=True)


yt_gns_channel_id = "UCaBf1a-dpIsw8OxqH4ki2Kg"
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
        print(colorama.Fore.RED + f"No api.key found... exiting.")
        sys.exit(2)


# TODO: Rename get_livestream
def search_livestream(api_key, yt_channel_id):
    yt_api_search_endpoint = "https://www.googleapis.com/youtube/v3/search"
    yt_api_search_params = {"part": "snippet",
                            "type": "video",
                            "eventType": "live",
                            "channelId": yt_channel_id,
                            "key": api_key}
    api_resp = requests.get(yt_api_search_endpoint, params=yt_api_search_params)
    if api_resp.status_code == 200:
        return api_resp.json()
    else:
        raise BadApiResponseException(f"Bad response status '{api_resp.status_code}':\n{api_resp.text}")


# TODO: Bake this into search_livestream after testing is complete
def decode_search_livestream_response(resp_json):
    num_results = int(resp_json["pageInfo"]["totalResults"])
    if num_results == 0:
        raise NoLivestreamException()
    elif num_results > 1:
        raise Exception("More than one livestream airing on channel, weird and unhandled, exit...")
        sys.exit(1)
    else:
        # Extract livestream information from json
        item = resp_json["items"][0]
        channel, title, video_id = item["snippet"]["channelTitle"], item["snippet"]["title"], item["id"]["videoId"]
        return channel, title, video_id


def download_livestream(yt_video_id):
    # run 'youtube-dl.exe -F https://www.youtube.com/watch?v={yt_video_id}' with subprocess
    # TODO: Implement other variables such as output directory and filename
    # TODO: Consider importing youtube-dl and using it as a module instead
    yt_video_url = f"https://www.youtube.com/watch?v={yt_video_id}"
    try:
        ytdl = subprocess.Popen(["youtube-dl.exe", yt_video_url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # While the process is not finished/terminated...
        while not ytdl.poll():
            try:
                # Attempt to communicate with the process for 1 second
                stdout, stderr = ytdl.communicate(input=None, timeout=1)
                # Handle youtube-dl and, by extension, ffmpeg output
                output_lines = stdout.decode("utf-8").splitlines()
                for output_line in output_lines:
                    # TODO: Match lines and only output ones of interest
                    print(f"{output_line}")
                # Display any error output
                error_lines = stderr.decode("utf-8").splitlines()
                for error_line in error_lines:
                    print(colorama.Fore.RED + f"{error_line}")
            except subprocess.TimeoutExpired:
                # If communication times out, ignore the exception and attempt to communicate again
                pass
    except KeyboardInterrupt:
        # Terminate the background ytdl process and re-raise KeyboardInterrupt
        ytdl.terminate()
        raise


if __name__ == '__main__':
    print(f"Loading API key...")
    api_key = load_api_key(api_key_p)

    print(f"Searching for livestream on YouTube channel '{yt_gns_channel_id}'...")
    # resp_json = search_livestream(api_key, yt_gns_channel_id)
    # DEBUG: load filled response from file for dev purposes
    import json
    resp_json = json.loads((Path(__file__).parent / "example_filled_resp.json").read_text())
    try:
        livestream = decode_search_livestream_response(resp_json)
    except NoLivestreamException:
        print(colorama.Fore.RED + "No livestream on channel...")
        sys.exit(3)

    print(colorama.Fore.GREEN + f"'{livestream[0]}' are livestreaming '{livestream[1]}' [{livestream[2]}]")
    print("Downloading livestream with youtube-dl...")
    download_livestream(livestream[2])
