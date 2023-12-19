from flask import Flask
from api.chat import route as chat_route
from api.keyword import route as keyword_route
from api.echo import route as echo_route


# 創建 Flask 伺服器
# __name__ 代表目前執行的模組
# 如果以主程式執行，__name__ 會是 __main__
# 如果是被引用，__name__ 會是模組名稱（也就是檔案名稱）
app = Flask(__name__)
# 註冊另一個模組 chat.py 的藍圖
# 註冊後，chat.py 中的路由就會生效
# 但是 chat.py 中的路由前面都會有 chat/ 的前綴 (url_prefix)
app.register_blueprint(chat_route,url_prefix='/chat')
app.register_blueprint(keyword_route,url_prefix='/keyword')
app.register_blueprint(echo_route,url_prefix='/echo')

@app.route("/")
def isAlive():
    return "OK"

# 主程式進入點
if __name__ == "__main__":
    # 啟動網路伺服器
    app.run(debug=True)
