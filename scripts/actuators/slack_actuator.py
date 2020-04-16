import json
import logging
import sys
from typing import Dict, Final, List, Optional

import slack
from slack.errors import SlackClientError


def handle_slack_error(e: SlackClientError):
    logging.warning("Slack message not posted successfully: " + str(e))


def actuate_simple(token: str, channel: str, text: str) -> bool:
    client = slack.WebClient(token=token)
    try:
        response = client.chat_postMessage(
            channel=channel,
            text=text)
        assert response['ok']
        return True
    except SlackClientError as e:
        handle_slack_error(e)
        return False


def actuate_blocks(token: str, channel: str, text: str, blocks: List[Optional[Dict]]) -> bool:
    client = slack.WebClient(token=token)
    try:
        response = client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks)
        assert response['ok']
        return True
    except SlackClientError as e:
        handle_slack_error(e)
        return False


def print_usage():
    print("Arguments:")
    print("\tslack_actuator.py --simple [API_TOKEN] [channel (no #)] [text]")
    print("\t\t[channel] is the channel name (without #), or member ID (for direct messages)")
    print("\tslack_actuator.py --blocks [API_TOKEN] [channel (no #)] [text] [blocks]")
    print("\t\t[blocks] is a string of a JSON formatting for a blocks of a message")
    print("\t\t[text] is a fallback string that may be shown instead of the blocks in certain situations")


def print_args_count():
    print("(args length: " + str(sys.argv.__len__()) + ")")  # Note args length includes slack_actuator, at sys.argv[0]


def main():
    if sys.argv.__len__() < 2:
        print_usage()
        return
    mode = sys.argv[1]
    if mode == '--simple':
        if sys.argv.__len__() == 5:
            # Normal case with a simple message
            token: Final = sys.argv[2]
            channel = sys.argv[3]
            text = sys.argv[4]
            return actuate_simple(token, channel, text)
        else:
            print_usage()
            print_args_count()
            return
    elif mode == '--blocks':
        if sys.argv.__len__() == 6:
            # Supported for more advanced message formats using blocks
            token: Final = sys.argv[2]
            channel = sys.argv[3]
            text = sys.argv[4]
            blocks: List[Optional[Dict]] = json.loads(sys.argv[5], strict=False)  # TODO handle better as input from the probe JSON?
            return actuate_blocks(token, channel, text, blocks)
        else:
            print_usage()
            print_args_count()
            return
    elif mode == '--help' or mode == '-h':
        print_usage()
        return
    else:
        print("Unrecognized mode: " + mode)
        print_usage()
        return


if __name__ == "__main__":
    main()
