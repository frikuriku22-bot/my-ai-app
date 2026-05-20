import streamlit as st
import pandas as pd
import bcrypt
import os
import time

st.set_page_config(page_title="自由な漫画サイト", layout="wide")

# =====================================================================
# 🔒 セキュリティ・データ管理設定
# =====================================================================
ADMIN_REGISTER_SECRET = "ore_dake_no_himitsu_999"

# 簡易データベース（サーバー上のセッションと擬似ファイルで保持）
# ※本格運用時はGoogleスプレッドシート等と繋ぐとデータが永続化します
if 'users' not in st.session_state:
    st.session_state.users = pd.DataFrame(columns=["username", "password_hash", "is_admin"])
if 'posts' not in st.session_state:
    st.session_state.posts = pd.DataFrame(columns=["id", "title", "images", "author", "status", "views"])
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# =====================================================================
# 🌐 画面処理
# =====================================================================

# --- ログアウト処理 ---
if st.session_state.current_user and st.sidebar.button("🚪 ログアウト"):
    st.session_state.current_user = None
    st.session_state.is_admin = False
    st.rerun()

# --- 1. ログイン・アカウント登録画面 ---
if st.session_state.current_user is None:
    st.title("🎬 漫画サイト認証")
    
    tab1, tab2 = st.tabs(["🔒 ログイン", "📝 新規登録"])
    
    with tab1:
        login_user = st.text_input("ユーザー名", key="login_u")
        login_pass = st.text_input("パスワード", type="password", key="login_p")
        if st.button("ログインする", type="primary"):
            users_df = st.session_state.users
            user_row = users_df[users_df["username"] == login_user]
            
            if not user_row.empty and bcrypt.checkpw(login_pass.encode('utf-8'), user_row.iloc[0]["password_hash"]):
                st.session_state.current_user = login_user
                st.session_state.is_admin = bool(user_row.iloc[0]["is_admin"])
                st.success("ログインしました！")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが違います。")
                
    with tab2:
        reg_user = st.text_input("ユーザー名（3〜15文字）", key="reg_u")
        reg_pass = st.text_input("パスワード（12文字以上）", type="password", key="reg_p")
        admin_key = st.text_input("管理者登録コード（一般ユーザーは空欄）", type="password")
        
        if st.button("アカウントを作成する"):
            if len(reg_user) < 3 or len(reg_user) > 15 or " " in reg_user:
                st.error("ユーザー名は3〜15文字（スペース不可）で入力してください。")
            elif len(reg_pass) < 12:
                st.error("パスワードは12文字以上で入力してください。")
            elif not st.session_state.users[st.session_state.users["username"] == reg_user].empty:
                st.error("そのユーザー名は既に使われています。")
            else:
                is_admin_flag = False
                if admin_key:
                    if admin_key == ADMIN_REGISTER_SECRET:
                        is_admin_flag = True
                    else:
                        st.error("管理者登録コードが正しくありません。")
                        st.stop()
                
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(reg_pass.encode('utf-8'), salt)
                
                new_user = pd.DataFrame([{"username": reg_user, "password_hash": hashed, "is_admin": is_admin_flag}])
                st.session_state.users = pd.concat([st.session_state.users, new_user], ignore_index=True)
                
                st.session_state.current_user = reg_user
                st.session_state.is_admin = is_admin_flag
                st.success("登録が完了しました！")
                st.rerun()

# --- 2. メイン画面（ログイン後） ---
else:
    st.sidebar.write(f"👤 ログイン中: **{st.session_state.current_user}**")
    if st.session_state.is_admin:
        st.sidebar.warning("👑 管理者権限モード")
        
    st.title("📚 自由な漫画サイト")
    
    menu = st.sidebar.radio("メニュー", ["🏠 タイムライン", "📤 漫画を投稿する", "🛠️ 管理者ダッシュボード"])
    
    # --- タイムライン画面 ---
    if menu == "🏠 タイムライン":
        st.subheader("現在の公開作品一覧")
        posts_df = st.session_state.posts
        approved_posts = posts_df[posts_df["status"] == "approved"]
        
        if approved_posts.empty:
            st.info("現在公開されている漫画はありません。")
        else:
            for idx, row in approved_posts.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        # 最初の1枚をカバー画像として表示
                        if row["images"]:
                            st.image(row["images"][0], width=150)
                    with col2:
                        st.subheader(row["title"])
                        st.write(f"👤 投稿者: {row['author']} | 👀 閲覧数: {row['views']}")
                        if st.button("📖 読む", key=f"read_{row['id']}"):
                            # 閲覧数を増やす
                            st.session_state.posts.loc[st.session_state.posts["id"] == row["id"], "views"] += 1
                            st.session_state.viewing_post = row["id"]
                            st.experimental_rerun()
                            
        # 漫画ビューアのポップアップ表示
        if 'viewing_post' in st.session_state:
            post_id = st.session_state.viewing_post
            post_data = st.session_state.posts[st.session_state.posts["id"] == post_id].iloc[0]
            st.markdown("---")
            st.header(f"📖 作品名: {post_data['title']}")
            if st.button("❌ ビューアを閉じる"):
                del st.session_state.viewing_post
                st.rerun()
            for img in post_data["images"]:
                st.image(img, use_container_width=True)

    # --- 投稿画面 ---
    elif menu == "📤 漫画を投稿する":
        st.subheader("漫画の投稿申請（複数画像対応）")
        with st.form("upload_form", clear_on_submit=True):
            title = st.text_input("漫画のタイトル")
            uploaded_files = st.file_uploader("画像ファイルを選択", type=["png", "jpg", "jpeg", "webp", "gif"], accept_multiple_files=True)
            submit = st.form_submit_button("投稿申請を送る")
            
            if submit:
                if not title:
                    st.error("タイトルを入力してください。")
                elif not uploaded_files:
                    st.error("ファイルが選択されていません。")
                else:
                    new_id = len(st.session_state.posts) + 1
                    # 画像データをメモリ上に保存
                    images_data = [file.read() for file in uploaded_files]
                    
                    new_post = pd.DataFrame([{
                        "id": new_id,
                        "title": title,
                        "images": images_data,
                        "author": st.session_state.current_user,
                        "status": "pending",  # 最初は承認待ち
                        "views": 0
                    }])
                    st.session_state.posts = pd.concat([st.session_state.posts, new_post], ignore_index=True)
                    st.success("🎉 投稿申請を送信しました！管理者の承認をお待ちください。")

    # --- 管理者ダッシュボード ---
    elif menu == "🛠️ 管理者ダッシュボード":
        if not st.session_state.is_admin:
            st.error("このページは管理者専用です。")
        else:
            st.subheader("👑 未承認の投稿一覧（管理用）")
            posts_df = st.session_state.posts
            pending_posts = posts_df[posts_df["status"] == "pending"]
            
            if pending_posts.empty:
                st.info("現在、承認待ちの作品はありません。")
            else:
                for idx, row in pending_posts.iterrows():
                    with st.container(border=True):
                        st.write(f"**作品名:** {row['title']} | **投稿者:** {row['author']}")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ 公開を承認する", key=f"app_{row['id']}"):
                                st.session_state.posts.loc[st.session_state.posts["id"] == row["id"], "status"] = "approved"
                                st.success(f"「{row['title']}」の公開を許可しました！")
                                st.rerun()
                        with col2:
                            if st.button("❌ 却下・削除する", key=f"del_{row['id']}", type="primary"):
                                st.session_state.posts = st.session_state.posts[st.session_state.posts["id"] != row["id"]]
                                st.warning("申請を却下し、削除しました。")
                                st.rerun()
