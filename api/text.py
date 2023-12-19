from flask import request, abort, Blueprint, current_app

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
import google.generativeai as palm
import dotenv
import os

# Priority use environment variable
if ".env" in os.listdir():
    dotenv.load_dotenv()

_google_generativeai_token = os.environ.get('google_generativeai_token')
_access_token = os.environ.get('access_token')
_channel_secret = os.environ.get('channel_secret')

palm.configure(api_key=_google_generativeai_token)

route = Blueprint(name="__text", import_name=__name__)

configuration = Configuration(access_token=_access_token)
line_handler = WebhookHandler(_channel_secret)

models = [m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]
model = models[0].name


@route.route("/", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    current_app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        current_app.logger.info(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)

    return 'OK'


@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        prompt = event.message.text
        completion = palm.generate_text(
            model=model,
            prompt=prompt,
            temperature=0,
            # The maximum length of the response
            max_output_tokens=800,
        )
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=str(completion.result))]
            )
        )
