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


def main():
    # SLACK_API_TOKEN: Final = os.environ["SLACK_API_TOKEN"]  # TODO switch to using environment variable
    SLACK_API_TOKEN: Final = sys.argv[1]
    CHANNEL = sys.argv[2]
    MESSAGE = sys.argv[3]

    actuate(SLACK_API_TOKEN, CHANNEL, MESSAGE)


if __name__ == "__main__":
    if sys.argv.__len__() != 4:
        print("Usage: slack_actuator.py [API_TOKEN] [channel name (no #)] [message]")
    else:
        main()
