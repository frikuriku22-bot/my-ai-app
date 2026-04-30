from flask import Flask, request

app = Flask(__name__)

password = "1234"

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_input = request.form["password"]  # ←エラー出る用
        
        if user_input == password:
            return "ログイン成功"
        else:
            return "パスワード違う"

    return '''
        <form method="POST">
            <input type="password" name="pass">
            <button type="submit">ログイン</button>
        </form>
    '''

app.run(host="0.0.0.0", port=5000, debug=True)
