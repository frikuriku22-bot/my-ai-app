import streamlit as st
import pandas as pd

st.title("私の漫画管理サイト 📚")

# データの保存用（セッション）
if 'manga_list' not in st.session_state:
    st.session_state.manga_list = pd.DataFrame([
        {"タイトル": "ワンピース", "巻数": "108巻", "メモ": "最新刊まで読んだ"},
        {"タイトル": "呪術廻戦", "巻数": "26巻", "メモ": "アニメの続きから"}
    ])

df = st.session_state.manga_list

# 1. データの確認
st.subheader("現在登録されている漫画一覧")
st.dataframe(df, use_container_width=True)

# 2. データの追加・書き換え
st.subheader("新しい漫画を追加・編集")
with st.form("manga_form", clear_on_submit=True):
    title = st.text_input("漫画のタイトル")
    volume = st.text_input("どこまで読んだ？（巻数など）")
    memo = st.text_area("メモ・感想")
    submit = st.form_submit_button("保存する")
    
    if submit and title:
        new_data = pd.DataFrame([{"タイトル": title, "巻数": volume, "メモ": memo}])
        st.session_state.manga_list = pd.concat([df, new_data], ignore_index=True)
        st.success(f"「{title}」を保存しました！")
        st.rerun()
