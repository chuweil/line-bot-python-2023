# 引入需要的模組
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

# 如果當前目錄有 .env 檔案，則優先使用 .env 檔案中的環境變數
if ".env" in os.listdir():
    dotenv.load_dotenv()

# 從環境變數中取得需要的資訊
_google_generativeai_token = os.environ.get('google_generativeai_token')
_access_token = os.environ.get('access_token')
_channel_secret = os.environ.get('channel_secret')

# 設定 Google generativeai 的 API 金鑰
palm.configure(api_key=_google_generativeai_token)

# 建立一個新的藍圖
route = Blueprint(name="__chat", import_name=__name__)

# 設定 Line Bot 的設定
configuration = Configuration(access_token=_access_token)
line_handler = WebhookHandler(_channel_secret)

# 從 Google generativeai 中取得所有支援文字生成的模型
models = [m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]
model = models[0].name


# 定義一個路由，用於接收 Line Bot 的訊息
@route.route("/", methods=['POST'])
def callback():
    # 取得 Line Bot 的簽章
    signature = request.headers['X-Line-Signature']

    # 取得請求的內容
    body = request.get_data(as_text=True)
    current_app.logger.info("Request body: " + body)

    # 處理 webhook 的內容
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        current_app.logger.info(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)

    return 'OK'


# 建立一個空的歷史訊息列表
history = []


# 定義一個處理訊息的函數
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        global history
        # 將新的訊息加入到歷史訊息中，並只保留最後 10 條訊息
        history.append(event.message.text)
        history = history[-10:]
        # 使用 Google generativeai 產生回覆訊息
        response = palm.chat(messages=history)
        current_app.logger.info(response)
        if response.filters:
            current_app.logger.info(response.filters)
            reply = "回覆內容被阻擋 (不支援中文)"
        else:
            reply = response.last

        # 使用 Line Bot API 回覆訊息
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=str(reply))]
            )
        )
