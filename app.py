import streamlit as st
import pandas as pd
import bcrypt
import os
import time
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="本格漫画アプリ", layout="wide")

# =====================================================================
# 💾 データの永続化設定（ファイル保存でリセットを防止）
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

# ログイン状態のキープ
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
    
    # 【機能】12時と0時に無料券を2枚配布（最大2枚キープ）
    last_check = datetime.fromisoformat(user.get("last_ticket_update", now.isoformat()))
    
    # 前回チェック時から、0時または12時を跨いでいるか判定
    # 簡易的に、半日以上経っているか、または時間を跨いだかでチケットを2枚にリセット
    if (now - last_check).total_seconds() > 3600: 
        if (last_check.hour < 12 <= now.hour) or (last_check.day != now.day and now.hour < 12) or (now - last_check).days >= 1:
            user["tickets"] = 2
            user["last_ticket_update"] = now.isoformat()
            save_data()

def can_read_paid_manga(username, post_id):
    user = st.session_state.users[username]
    now = datetime.now()
    
    # 24時間タイマーのチェック
    timer_key = f"timer_{post_id}"
    if timer_key in user:
        unlock_time = datetime.fromisoformat(user[timer_key])
        if now >= unlock_time:
            return "timer_free" # 24時間経過して無料
        else:
            return f"wait_{int((unlock_time - now).total_seconds() // 3600)}h" # まだ待ち時間
            
    return "locked"

# =====================================================================
# 🌐 画面表示・ルーティング
# =====================================================================

# --- ログアウト ---
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
                
                # 初期ユーザーデータ（チケット2枚、24時間タイマー用空枠）
                st.session_state.users[r_user] = {
                    "password_hash": hashed,
                    "is_admin": is_admin,
                    "tickets": 2,
                    "last_ticket_update": datetime.now().isoformat()
                }
                save_data()
                st.success("アカウントを作成しました！ログインしてください。")

# --- 2. メイン画面（ログイン後） ---
else:
    username = st.session_state.current_user
    update_user_tickets(username) # チケットの自動更新
    
    # サイドバー情報
    st.sidebar.write(f"👤 ユーザー: **{username}**")
    st.sidebar.write(f"🎫 保有無料券: **{st.session_state.users[username]['tickets']} 枚**")
    st.sidebar.caption("※無料券は毎日0:00と12:00に2枚に回復します")
    if st.session_state.is_admin:
        st.sidebar.warning("👑 管理者モード")
        
    st.title("📚 本格漫画アプリ")
    menu = st.sidebar.radio("メニュー", ["🏠 タイムライン", "📤 漫画を投稿する", "🛠️ 管理者ダッシュボード"])
    
    # --- 【機能】検索バー ---
    search_query = st.text_input("🔍 漫画のタイトルや投稿者で検索...", "")

    # --- タイムライン画面 ---
    if menu == "🏠 タイムライン":
        st.subheader("作品一覧")
        
        # 検索と公開状態（approved）でフィルタリング
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
                    with col1:
                        st.write("🖼️ [Manga Cover]")
                    with col2:
                        # 【機能】有料/無料バッジの表示
                        pay_status = "💰 有料作品" if p.get("is_paid", False) else "🆓 完全無料"
                        st.subheader(f"{p['title']} ({pay_status})")
                        st.write(f"👤 投稿者: {p['author']} | 👀 閲覧数: {p['views']}")
                        
                        # 閲覧ボタンの制御
                        status = can_read_paid_manga(username, p["id"])
                        
                        if not p.get("is_paid", False) or status == "timer_free":
                            if st.button("📖 読む", key=f"read_{p['id']}"):
                                p["views"] += 1
                                save_data()
                                st.session_state.viewing_post = p["id"]
                                st.rerun()
                        else:
                            # 有料作品の場合の選択肢
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.session_state.users[username]["tickets"] > 0:
                                    if st.button("🎫 無料券を1枚使って読む", key=f"ticket_{p['id']}"):
                                        st.session_state.users[username]["tickets"] -= 1
                                        p["views"] += 1
                                        save_data()
                                        st.session_state.viewing_post = p["id"]
                                        st.rerun()
                                else:
                                    st.button("🎫 券がありません", disabled=True, key=f"ticket_dis_{p['id']}")
                            with col_btn2:
                                # 【機能】24時間タイマーの発動
                                if f"timer_{p['id']}" not in st.session_state.users[username]:
                                    if st.button("⏳ 24時間待って無料で読む", key=f"time_start_{p['id']}"):
                                        st.session_state.users[username][f"timer_{p['id']}"] = (datetime.now() + timedelta(days=1)).isoformat()
                                        save_data()
                                        st.success("タイマーを開始しました！24時間後に読めるようになります。")
                                        st.rerun()
                                else:
                                    st.write(f"⏱️ 解放まで時間: {status.replace('wait_', '')}")

        # ビューア画面
        if 'viewing_post' in st.session_state:
            post_id = st.session_state.viewing_post
            post_data = next((p for p in st.session_state.posts if p["id"] == post_id), None)
            if post_data:
                st.markdown("---")
                st.header(f"📖 本編ビューア: {post_data['title']}")
                if st.button("❌ ビューアを閉じる"):
                    del st.session_state.viewing_post
                    st.rerun()
                st.info("（ここに漫画の原稿画像が1ページずつ表示されます）")

    # --- 投稿画面 ---
    elif menu == "📤 漫画を投稿する":
        st.subheader("新規作品の投稿申請")
        with st.form("upload_form"):
            title = st.text_input("作品タイトル")
            files = st.file_uploader("原稿ファイル（複数選択可）", accept_multiple_files=True)
            submit = st.form_submit_button("申請を送信")
            
            if submit and title and files:
                new_id = len(st.session_state.posts) + 1
                st.session_state.posts.append({
                    "id": new_id,
                    "title": title,
                    "author": username,
                    "status": "pending",
                    "is_paid": False, # 初期値は無料
                    "views": 0
                })
                save_data()
                st.success("投稿申請を送りました！管理者の承認をお待ちください。")

    # --- 管理者ダッシュボード ---
    elif menu == "🛠️ 管理者ダッシュボード":
        if not st.session_state.is_admin:
            st.error("権限がありません。")
        else:
            st.subheader("👑 投稿管理・【機能】有料化コントロール")
            
            for p in st.session_state.posts:
                with st.container(border=True):
                    st.write(f"**作品:** {p['title']} | **投稿者:** {p['author']} | **現在の状態:** {p['status']}")
                    
                    # 【機能】管理者が有料・無料を切り替えるスイッチ
                    is_paid = st.toggle("有料作品にする", value=p.get("is_paid", False), key=f"pay_toggle_{p['id']}")
                    if is_paid != p.get("is_paid", False):
                        p["is_paid"] = is_paid
                        save_data()
                        st.toast(f"「{p['title']}」の料金設定を更新しました。")
                    
                    # 承認・却下ボタン
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
