from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import bcrypt
import os
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)

# =====================================================================
# 🔒 セキュリティ基本設定
# =====================================================================
# 1. セッション暗号化用の強力なキー
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_strong_random_secret_key_123456789!@#")

# 2. クッキーのセキュリティ設定（ハッキング対策）
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,  # JavaScriptからのクッキー盗難を防止
    SESSION_COOKIE_SAMESITE='Lax', # CSRF（クロスサイトリクエストフォージェリ）攻撃を防止
)

# 3. 👑 あなた（管理者）だけが知っている秘密の登録用コード
# アカウント登録時にこのコードを入力した人だけが、本物の「管理者」に昇格できます。
ADMIN_REGISTER_SECRET = "ore_dake_no_himitsu_999"

# =====================================================================
# 📁 画像アップロード設定
# =====================================================================
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =====================================================================
# 💾 データベース初期化
# =====================================================================
def init_db():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn = sqlite3.connect("manga_site.db")
    cursor = conn.cursor()
    
    # ユーザーテーブル（is_admin: 0=一般ユーザー, 1=管理者）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            ip_address TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)
    
    # 漫画投稿テーブル（status: pending=承認待ち, approved=承認済み）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filenames TEXT NOT NULL, 
            author TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    # 閲覧数管理テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS views (
            post_id INTEGER,
            username TEXT,
            PRIMARY KEY (post_id, username)
        )
    """)
    conn.commit()
    conn.close()

# 入力バリデーション（セキュリティ強化：12文字以上）
def validate_user_input(username, password):
    if len(username) < 3 or len(username) > 15:
        return "エラー: ユーザー名は3文字以上、15文字以内で入力してください。"
    if len(password) < 12:
        return "エラー: パスワードはセキュリティ保護のため12文字以上で入力してください。"
    if " " in username or "　" in username:
        return "エラー: ユーザー名にスペースは使用できません。"
    return None

# =====================================================================
# 🌐 画面ルーティング（各ページの処理）
# =====================================================================

# 1. ログイン・アカウント登録画面
@app.route("/", methods=["GET", "POST"])
def index():
    if "username" in session:
        return redirect(url_for("main_page"))
        
    message = request.args.get("message", None)
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        admin_key = request.form.get("admin_key", "").strip()
        action = request.form.get("action")
        user_ip = request.remote_addr
        
        validation_error = validate_user_input(username, password)
        if validation_error and action == "register":
            return render_template("index.html", message=validation_error)

        # --- 新規登録処理 ---
        if action == "register":
            conn = sqlite3.connect("manga_site.db")
            cursor = conn.cursor()
            
            # 【アカウント量産防止】同一IPアドレスからの登録上限チェック
            cursor.execute("SELECT COUNT(*) FROM users WHERE ip_address = ?", (user_ip,))
            account_count = cursor.fetchone()[0]
            if account_count >= 3:
                conn.close()
                return render_template("index.html", message="エラー: この端末からのアカウント作成上限に達しました。")
            
            # 管理者コードの厳重判定
            is_admin_flag = 0
            if admin_key != "":
                if admin_key == ADMIN_REGISTER_SECRET:
                    is_admin_flag = 1
                else:
                    conn.close()
                    return render_template("index.html", message="エラー: 管理者登録コードが正しくありません。")

            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            try:
                cursor.execute("INSERT INTO users (username, password_hash, ip_address, is_admin) VALUES (?, ?, ?, ?)", 
                               (username, hashed_password, user_ip, is_admin_flag))
                conn.commit()
                
                session["username"] = username
                session["is_admin"] = is_admin_flag
                return redirect(url_for("main_page"))
            except sqlite3.IntegrityError:
                message = "エラー: そのユーザー名は既に使われています。"
            finally:
                conn.close()
        
        # --- ログイン処理 ---
        elif action == "login":
            conn = sqlite3.connect("manga_site.db")
            cursor = conn.cursor()
            # パラメーター化クエリでSQLインジェクションを完全防御
            cursor.execute("SELECT password_hash, is_admin FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            conn.close()
            
            if row and bcrypt.checkpw(password.encode('utf-8'), row[0]):
                session["username"] = username
                session["is_admin"] = row[1]
                return redirect(url_for("main_page"))
            else:
                message = "エラー: ユーザー名またはパスワードが違います。"
                
    return render_template("index.html", message=message)

# 2. メイン画面（タイムライン ＆ 管理者ダッシュボード）
@app.route("/main")
def main_page():
    if "username" not in session:
        return redirect(url_for("index", message="ログインが必要です。"))
    
    current_user = session["username"]
    is_admin = session.get("is_admin", 0)
    message = request.args.get("message", None)
        
    conn = sqlite3.connect("manga_site.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 承認された（status = 'approved'）漫画のみタイムラインに取得
    cursor.execute("SELECT id, title, filenames, author FROM posts WHERE status = 'approved' ORDER BY id DESC")
    rows = cursor.fetchall()
    
    posts = []
    for row in rows:
        post_id = row["id"]
        cursor.execute("SELECT COUNT(*) FROM views WHERE post_id = ?", (post_id,))
        views_count = cursor.fetchone()[0]
        
        file_list = row["filenames"].split(",")
        cover_image = file_list[0] if file_list else ""
        
        posts.append({
            "id": post_id,
            "title": row["title"],
            "cover": cover_image,
            "author": row["author"],
            "views": views_count
        })
        
    # 本物の管理者の場合のみ、未承認（status = 'pending'）の申請リストを取得
    pending_posts = []
    if is_admin == 1:
        cursor.execute("SELECT id, title, author FROM posts WHERE status = 'pending' ORDER BY id DESC")
        pending_posts = cursor.fetchall()
        
    conn.close()
    return render_template("main.html", username=current_user, posts=posts, pending_posts=pending_posts, is_admin=is_admin, message=message)

# 3. 漫画の詳細閲覧画面（ビューア）
@app.route("/view/<int:post_id>")
def view_manga(post_id):
    if "username" not in session:
        return redirect(url_for("index", message="ログインが必要です。"))
        
    current_user = session["username"]
    is_admin = session.get("is_admin", 0)
    
    conn = sqlite3.connect("manga_site.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, title, filenames, author, status FROM posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return redirect(url_for("main_page", message="エラー: 作品が見つかりません。"))
        
    # 厳重な閲覧ブロック：未承認のものは「管理者」か「投稿者本人」以外はURL直打ちでも閲覧不可
    if row["status"] == "pending" and is_admin != 1 and current_user != row["author"]:
        conn.close()
        return redirect(url_for("main_page", message="エラー: この作品はまだ管理者の承認待ちです。"))
        
    # 閲覧数を重複なしでカウント
    cursor.execute("INSERT OR IGNORE INTO views (post_id, username) VALUES (?, ?)", (post_id, current_user))
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM views WHERE post_id = ?", (post_id,))
    views_count = cursor.fetchone()[0]
    
    file_list = row["filenames"].split(",")
    
    post_data = {
        "id": row["id"],
        "title": row["title"],
        "filenames": file_list,
        "author": row["author"],
        "views": views_count
    }
    
    conn.close()
    return render_template("view.html", post=post_data)

# 4. 👑 管理者専用：漫画の公開承認処理
@app.route("/approve/<int:post_id>", methods=["POST"])
def approve_manga(post_id):
    # セッション内の特権フラグを厳密にチェック
    if session.get("is_admin") != 1:
        return redirect(url_for("main_page", message="エラー: 権限がありません。"))
        
    conn = sqlite3.connect("manga_site.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET status = 'approved' WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("main_page", message="作品の公開を許可しました！"))

# 5. 漫画のアップロード申請処理（複数選択対応）
@app.route("/upload", methods=["POST"])
def upload():
    if "username" not in session:
        return redirect(url_for("index"))
        
    title = request.form.get("title", "").strip()
    files = request.files.getlist("manga_files")
    
    if not title:
        return redirect(url_for("main_page", message="エラー: タイトルを入力してください。"))
    if not files or len(files) == 0 or files[0].filename == '':
        return redirect(url_for("main_page", message="エラー: ファイルが選択されていません。"))
        
    saved_filenames = []
    for i, file in enumerate(files):
        if file and allowed_file(file.filename):
            secure_name = secure_filename(file.filename)
            filename = f"{session['username']}_{int(time.time())}_{i}_{secure_name}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            saved_filenames.append(filename)
        else:
            return redirect(url_for("main_page", message="エラー: 許可されていない形式のファイルが含まれています。"))
            
    filenames_str = ",".join(saved_filenames)
    
    conn = sqlite3.connect("manga_site.db")
    cursor = conn.cursor()
    # 投稿時は自動的に status = 'pending' (承認待ち) に設定
    cursor.execute("INSERT INTO posts (title, filenames, author, status) VALUES (?, ?, ?, 'pending')", 
                   (title, filenames_str, session["username"]))
    conn.commit()
    conn.close()
    
    return redirect(url_for("main_page", message="漫画の投稿申請を送信しました！管理者の許可をお待ちください。"))

# 6. 🚪 ログアウト処理（ログイン画面へ確実にリダイレクト）
@app.route("/logout")
def logout():
    session.clear() # セッションデータを完全消去
    return redirect(url_for("index") + "?message=ログアウトしました。")

# =====================================================================
# 🚀 サーバー起動
# =====================================================================
if __name__ == "__main__":
    init_db()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )
