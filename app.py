import streamlit as st
import pandas as pd
import bcrypt
import os
import time
import json
import base64
from datetime import datetime, timedelta

st.set_page_config(page_title="本格漫画アプリ", layout="wide")

# =====================================================================
# 💾 データの永続化設定（画像もBase64化して完全にJSONに保存）
# =====================================================================
USER_FILE = "users_db.json"
POST_FILE = "posts_db.json"
ADMIN_REGISTER_SECRET = "ore_dake_no_himitsu_999"

def load_data():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            st.session_state.users = json.load(f)
    else:
        st.session_state.users = {}

    if os.path.exists(POST_FILE):
        with open(POST_FILE, "r") as f:
            st.session_state.posts = json.load(f)
    else:
        st.session_state.posts = []

def save_data():
    with open(USER_FILE, "w") as f:
        json.dump(st.session_state.users, f)
    with open(POST_FILE, "w") as f:
        json.dump(st.session_state.posts, f)

# 初回データ読み込み
if 'users' not in st.session_state:
    load_data()

if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# =====================================================================
# 🎫 無料券・タイマーの計算ロジック
# =====================================================================
def update_user_tickets(username):
    user = st.session_state.users[username]
    now = datetime.now()
    last_check = datetime.fromisoformat(user.get("last_ticket_update", now.isoformat()))
    
    if (now - last_check).total_seconds() > 3600: 
        if (last_check.hour < 12 <= now.hour) or (last_check.day != now.day and now.hour < 12) or (now - last_check).days >= 1:
            user["tickets"] = 2  # 0時と12時に2枚に回復
            user["last_ticket_update"] = now.isoformat()
            save_data()

def can_read_paid_manga(username, post_id):
    user = st.session_state.users[username]
    now = datetime.now()
    
    # 共通の無料券で一度「解放（購入）」した漫画かどうかのチェック
    if "unlocked_posts" not in user:
        user["unlocked_posts"] = []
    if str(post_id) in user["unlocked_posts"]:
        return "unlocked"

    # 24時間タイマーのチェック
    timer_key = f"timer_{post_id}"
    if timer_key in user:
        unlock_time = datetime.fromisoformat(user[timer_key])
        if now >= unlock_time:
            return "timer_free"
        else:
            return f"wait_{int((unlock_time - now).total_seconds() // 3600)}h"
            
    return "locked"

# =====================================================================
# 🌐 画面表示・ルーティング
# =====================================================================

if st.session_state.current_user and st.sidebar.button("🚪 ログアウト"):
    st.session_state.current_user = None
    st.session_state.is_admin = False
    st.rerun()

# --- 1. ログイン / アカウント登録 ---
if st.session_state.current_user is None:
    st.title("🎬 漫画アプリ - 認証")
    tab1, tab2 = st.tabs(["🔒 ログイン", "📝 新規登録"])
    
    with tab1:
        l_user = st.text_input("ユーザー名", key="l_u")
        l_pass = st.text_input("パスワード", type="password", key="l_p")
        if st.button("ログイン"):
            if l_user in st.session_state.users:
                stored_pass = st.session_state.users[l_user]["password_hash"].encode('utf-8')
                if bcrypt.checkpw(l_pass.encode('utf-8'), stored_pass):
                    st.session_state.current_user = l_user
                    st.session_state.is_admin = st.session_state.users[l_user]["is_admin"]
                    st.success("ログイン成功！")
                    st.rerun()
            st.error("ユーザー名またはパスワードが違います。")
            
    with tab2:
        r_user = st.text_input("ユーザー名（3〜15文字）", key="r_u")
        r_pass = st.text_input("パスワード（12文字以上）", type="password", key="r_p")
        a_key = st.text_input("管理者登録コード（一般は空欄）", type="password")
        
        if st.button("登録する"):
            if len(r_user) < 3 or r_user in st.session_state.users:
                st.error("ユーザー名が無効か、既に存在します。")
            elif len(r_pass) < 12:
                st.error("パスワードは12文字以上にしてください。")
            else:
                is_admin = (a_key == ADMIN_REGISTER_SECRET)
                hashed = bcrypt.hashpw(r_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                st.session_state.users[r_user] = {
                    "password_hash": hashed,
                    "is_admin": is_admin,
                    "tickets": 2,
                    "unlocked_posts": [],
                    "last_ticket_update": datetime.now().isoformat()
                }
                save_data()
                st.success("アカウントを作成しました！ログインしてください。")

# --- 2. メイン画面（ログイン後） ---
else:
    username = st.session_state.current_user
    update_user_tickets(username)
    
    # 【改善】全アプリ共通の無料券残高をいちばん目立つサイドバー上部に表示
    st.sidebar.markdown(f"### 🎫 あなたの共通無料券: **{st.session_state.users[username]['tickets']} 枚**")
    st.sidebar.caption("（どれでも好きな有料漫画を1話読めます。毎日0時/12時に2枚にチャージされます）")
    st.sidebar.write(f"👤 ユーザー: **{username}**")
    if st.session_state.is_admin:
        st.sidebar.warning("👑 管理者モード")
        
    st.title("📚 本格漫画アプリ")
    menu = st.sidebar.radio("メニュー", ["🏠 タイムライン", "📤 漫画を投稿する", "🛠️ 管理者ダッシュボード"])
    
    search_query = st.text_input("🔍 漫画のタイトルや投稿者で検索...", "")

    # --- タイムライン画面 ---
    if menu == "🏠 タイムライン":
        st.subheader("作品一覧")
        
        display_posts = [
            p for p in st.session_state.posts 
            if p["status"] == "approved" and 
            (search_query.lower() in p["title"].lower() or search_query.lower() in p["author"].lower())
        ]
        
        if not display_posts:
            st.info("該当する漫画が見つかりません。")
        else:
            for p in display_posts:
                with st.container(border=True):
                    col1, col2 = st.columns([1, 4])
                    
                    status = can_read_paid_manga(username, p["id"])
                    pay_status = "💰 有料作品" if p.get("is_paid", False) else "🆓 完全無料"
                    
                    with col1:
                        # 【改善】表紙画像を表示し、クリック（ボタン化）で開けるように実装
                        if "images" in p and p["images"]:
                            try:
                                cover_data = base64.b64decode(p["images"][0])
                                st.image(cover_data, use_container_width=True)
                            except Exception:
                                st.write("🖼️ [画像読み込みエラー]")
                        else:
                            st.write("🖼️ [表紙なし]")
                        
                        # 【改善】表紙の下に「タップして読む」ボタンを配置して表紙クリック連動を実現
                        if not p.get("is_paid", False) or status in ["timer_free", "unlocked"]:
                            if st.button("📖 表紙を押して読む", key=f"cover_btn_{p['id']}", use_container_width=True):
                                p["views"] += 1
                                save_data()
                                st.session_state.viewing_post = p["id"]
                                st.rerun()
                    
                    with col2:
                        st.subheader(f"{p['title']} ({pay_status})")
                        st.write(f"👤 投稿者: {p['author']} | 👀 閲覧数: {p['views']}")
                        
                        if not p.get("is_paid", False) or status in ["timer_free", "unlocked"]:
                            st.success("✅ この作品は現在すぐに読めます！")
                        else:
                            # 有料作品で、まだ未解放の場合
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.session_state.users[username]["tickets"] > 0:
                                    # 【改善】共通無料券を消費して、この漫画を全体共通枠から解放する
                                    if st.button("🎫 共通無料券を1枚使って読む", key=f"ticket_{p['id']}", type="primary"):
                                        st.session_state.users[username]["tickets"] -= 1
                                        if "unlocked_posts" not in st.session_state.users[username]:
                                            st.session_state.users[username]["unlocked_posts"] = []
                                        st.session_state.users[username]["unlocked_posts"].append(str(p["id"]))
                                        p["views"] += 1
                                        save_data()
                                        st.session_state.viewing_post = p["id"]
                                        st.rerun()
                                else:
                                    st.button("🎫 券が足りません", disabled=True, key=f"ticket_dis_{p['id']}")
                            with col_btn2:
                                if f"timer_{p['id']}" not in st.session_state.users[username]:
                                    if st.button("⏳ 24時間待って無料で読む", key=f"time_start_{p['id']}"):
                                        st.session_state.users[username][f"timer_{p['id']}"] = (datetime.now() + timedelta(days=1)).isoformat()
                                        save_data()
                                        st.success("タイバーを開始しました！24時間後に無料化します。")
                                        st.rerun()
                                else:
                                    st.write(f"⏱️ 無料解放まであと: {status.replace('wait_', '')}")

        # --- ビューア画面（画像が1枚ずつ縦に並んで表示される本編） ---
        if 'viewing_post' in st.session_state:
            post_id = st.session_state.viewing_post
            post_data = next((p for p in st.session_state.posts if p["id"] == post_id), None)
            if post_data:
                st.markdown("---")
                st.header(f"📖 {post_data['title']} - 本編ビューア")
                if st.button("❌ ビューアを閉じる", type="primary"):
                    del st.session_state.viewing_post
                    st.rerun()
                
                # 【改善】保存されている原稿画像をすべてデコードして縦に綺麗に表示
                if "images" in post_data and post_data["images"]:
                    for idx, img_b64 in enumerate(post_data["images"]):
                        try:
                            img_bytes = base64.b64decode(img_b64)
                            st.image(img_bytes, caption=f"{idx + 1} ページ", use_container_width=True)
                        except Exception:
                            st.error(f"{idx + 1}ページの画像表示に失敗しました。")
                else:
                    st.warning("この作品には原稿画像がありません。")

    # --- 投稿画面 ---
    elif menu == "📤 漫画を投稿する":
        st.subheader("新規作品の投稿申請")
        with st.form("upload_form"):
            title = st.text_input("作品タイトル")
            files = st.file_uploader("原稿ファイル（複数選択可 / 1枚目が表紙になります）", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
            submit = st.form_submit_button("申請を送信")
            
            if submit and title and files:
                new_id = len(st.session_state.posts) + 1
                
                # 【改善】アップロードされた画像をBase64文字列に変換して完全にデータ保存
                encoded_images = []
                for f in files:
                    file_bytes = f.read()
                    b64_string = base64.b64encode(file_bytes).decode('utf-8')
                    encoded_images.append(b64_string)
                
                st.session_state.posts.append({
                    "id": new_id,
                    "title": title,
                    "author": username,
                    "status": "pending",
                    "is_paid": False,
                    "images": encoded_images, # 画像データを格納
                    "views": 0
                })
                save_data()
                st.success("原稿付きで投稿申請を送りました！管理者の承認をお待ちください。")

    # --- 管理者ダッシュボード ---
    elif menu == "🛠️ 管理者ダッシュボード":
        if not st.session_state.is_admin:
            st.error("権限がありません。")
        else:
            st.subheader("👑 投稿管理・有料化コントロール")
            
            if not st.session_state.posts:
                st.info("投稿された作品はまだありません。")
            else:
                for p in st.session_state.posts:
                    with st.container(border=True):
                        st.write(f"**作品:** {p['title']} | **投稿者:** {p['author']} | **現在の状態:** {p['status']}")
                        
                        is_paid = st.toggle("有料作品にする", value=p.get("is_paid", False), key=f"pay_toggle_{p['id']}")
                        if is_paid != p.get("is_paid", False):
                            p["is_paid"] = is_paid
                            save_data()
                            st.toast(f"「{p['title']}」の料金設定を更新しました。")
                        
                        if p["status"] == "pending":
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ 公開を承認", key=f"app_{p['id']}"):
                                    p["status"] = "approved"
                                    save_data()
                                    st.rerun()
                            with col2:
                                if st.button("❌ 却下・削除", key=f"del_{p['id']}", type="primary"):
                                    st.session_state.posts.remove(p)
                                    save_data()
                                    st.rerun()
