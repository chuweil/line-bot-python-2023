# 引入需要的模組
from collections import defaultdict
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
import google.generativeai as genai
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
genai.configure(api_key=_google_generativeai_token)

# 建立一個新的藍圖
route = Blueprint(name="__chat", import_name=__name__)

# 設定 Line Bot 的設定
configuration = Configuration(access_token=_access_token)
line_handler = WebhookHandler(_channel_secret)

# 從 Google generativeai 中取得所有支援文字生成的模型
models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
print("Available models:")
# Available models:
# models/gemini-pro
# models/gemini-pro-vision
print("\n".join([m.name for m in models]))

StartMessage = [
    
]

# 從 Google generativeai 中取得指定的模型
model = genai.GenerativeModel('gemini-pro')
# 建立一個使用者字典，用於儲存不同使用者的歷史訊息
users = defaultdict(lambda: {'history': [msg for msg in StartMessage]})


# 定義一個路由，用於接收 Line Bot 的訊息
@route.route("/", methods=['POST'])
def chat_callback():
    # 取得 Line Bot 的認證資訊
    signature = request.headers['X-Line-Signature']

    # 取得請求的內容
    body = request.get_data(as_text=True)
    current_app.logger.info("Request body: " + body)

    # 處理 webhook 的內容
    # 若驗證失敗，則回傳錯誤訊息 (400)
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        current_app.logger.error(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)

    return 'OK'


# 定義一個處理訊息的函數
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        current_app.logger.debug("User:" + event.source.to_dict()['userId'])
        global users, model
        # 開始聊天，若沒有歷史訊息，則建立一個新的聊天
        chat = model.start_chat(history=users[event.source.to_dict()['userId']]['history'])

        # 將使用者的訊息送入Google generativeai中運算
        response = chat.send_message(event.message.text)
        reply = response.text
        # 使用 Line Bot API 回覆訊息
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=str(reply))]
            )
        )
        # 將聊天的歷史訊息儲存起來
        users[event.source.to_dict()['userId']]['history'] = chat.history
        print("User history:", users[event.source.to_dict()['userId']]['history'])
