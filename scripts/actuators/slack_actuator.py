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


if __name__ == "__main__":
    if sys.argv.__len__() == 4:
        # Normal case with a simple message
        SLACK_API_TOKEN: Final = sys.argv[1]
        CHANNEL = sys.argv[2]
        MESSAGE = sys.argv[3]
        actuate(SLACK_API_TOKEN, CHANNEL, MESSAGE)
    elif sys.argv.__len__() == 5:
        # Supported for more advanced message formats using blocks
        SLACK_API_TOKEN: Final = sys.argv[1]
        CHANNEL = sys.argv[2]
        MESSAGE = sys.argv[3]
        BLOCKS = json.loads(sys.argv[4])  # TODO better handling this as input from the probe JSON
        actuate_blocks(SLACK_API_TOKEN, CHANNEL, MESSAGE, BLOCKS)
    else:
        print("Usage:")
        print("\tslack_actuator.py [API_TOKEN] [channel name (no #)] [message]")
        print("\tslack_actuator.py [API_TOKEN] [channel name (no #)] [backup_message] [blocks]")  # TODO clarify use for blocks
        print("(args length: " + str(sys.argv.__len__()) + ")")
