from flask import Flask, request, abort
from api.chat import route as chat_route
from api.text import route as text_route
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import dotenv
import os

# Priority use environment variable
if ".env" in os.listdir():
    dotenv.load_dotenv()

app = Flask(__name__)
app.register_blueprint(chat_route,url_prefix='/chat')
app.register_blueprint(text_route,url_prefix='/text')

_access_token = os.environ.get('access_token')
_channel_secret = os.environ.get('channel_secret')

configuration = Configuration(access_token=_access_token)
line_handler = WebhookHandler(_channel_secret)


@app.route("/")
def isAlive():
    return "OK"


@app.route("/echo", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=event.message.text)]
            )
        )


if __name__ == "__main__":
    app.run(debug=True)
