import json
import sys
from typing import Final

import slack


def actuate(api_token, channel, message):
    client = slack.WebClient(token=api_token)

    response = client.chat_postMessage(
        channel=channel,
        text=message)
    assert response["ok"]
    assert response["message"]["text"] == message


def actuate_blocks(api_token, channel, message, blocks):
    client = slack.WebClient(token=api_token)

    response = client.chat_postMessage(
        channel=channel,
        text=message,
        blocks=blocks)
    assert response["ok"]
    assert response["message"]["text"] == message


def print_usage():
    print("Arguments:")
    print("\tslack_actuator.py --simple [API_TOKEN] [channel name (no #)] [message]")
    print("\tslack_actuator.py --blocks [API_TOKEN] [channel name (no #)] [backup_message] [blocks]")
    print("\t\t[blocks] is a string of a JSON formatting for a blocks of a message")
    print("\t\t[backup_message] is a message that may be shown instead in certain situations")
    print("(args length: " + str(sys.argv.__len__()) + ")")  # Note args length includes slack_actuator, at sys.argv[0]


def main():
    if sys.argv.__len__() < 2:
        print_usage()
        return
    mode = sys.argv[1]
    if mode == "--simple":
        if sys.argv.__len__() == 5:
            # Normal case with a simple message
            SLACK_API_TOKEN: Final = sys.argv[2]
            CHANNEL = sys.argv[3]
            MESSAGE = sys.argv[4]
            return actuate(SLACK_API_TOKEN, CHANNEL, MESSAGE)
        else:
            print_usage()
            return
    elif mode == "--blocks":
        if sys.argv.__len__() == 6:
            # Supported for more advanced message formats using blocks
            SLACK_API_TOKEN: Final = sys.argv[2]
            CHANNEL = sys.argv[3]
            MESSAGE = sys.argv[4]
            BLOCKS = json.loads(sys.argv[5])  # TODO better handling this as input from the probe JSON?
            return actuate_blocks(SLACK_API_TOKEN, CHANNEL, MESSAGE, BLOCKS)
        else:
            print_usage()
            return
    elif mode == "--help" or mode == "-h":
        print_usage()
        return
    else:
        print("Unrecognized mode: " + mode)
        print_usage()
        return


if __name__ == "__main__":
    main()
