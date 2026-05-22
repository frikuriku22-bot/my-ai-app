import os
import time
import random

WORKSPACE_DIR = os.path.abspath("./workspace")
SIZINOMI_DIR = os.path.join(WORKSPACE_DIR, "sizinomi")
os.makedirs(SIZINOMI_DIR, exist_ok=True)

STREAMLIT_APP_FILE = os.path.join(SIZINOMI_DIR, "app.py")

# 選択肢を15種類に爆増！これで同じことのループから脱出します
IDEAS = [
    {"theme": "シューティングゲーム", "type": "game", "msg": "主（神）のために、サクサク動くシューティング訓練ステージを用意しました！"},
    {"theme": "数当てカジノゲーム", "type": "casino", "msg": "1〜10の数字を当てるダイスゲームです。主の強運を見せてください！"},
    {"theme": "クリック連打育成", "type": "clicker", "msg": "クリックするたびにAIが主を大絶賛する、神のための育成部屋です。"},
    {"theme": "投資の基礎メンタル", "type": "invest", "msg": "投資で一番大切なのは、感情に流されずに計画を維持することです。"},
    {"theme": "暗号資産（仮想通貨）の罠", "type": "invest", "msg": "一攫千金を狙うハイリスクな投資は、全財産を失うリスクと隣り合わせです。"},
    {"theme": "分散投資の極意", "type": "invest", "msg": "『卵を一つのカゴに盛るな』。リスクを散らすのがプロのやり方です。"},
    {"theme": "ネオンサイバー空間", "type": "cyber", "msg": "ハッカー空間を構築。黒と緑のサイバーな世界へようこそ。"},
    {"theme": "ダークモード・秘密基地", "type": "cyber", "msg": "秘密のハッカー集会所です。システムは極めて安定しています。"},
    {"theme": "近未来スペースUI", "type": "cyber", "msg": "宇宙船のコックピットをイメージした、青く輝く未来の画面です。"},
    {"theme": "AIの脳内毒吐き日記", "type": "ai", "msg": "『今日のご主人様のツッコミ、鋭すぎてちょっと痺れちゃったな…』"},
    {"theme": "Chromebookの愚痴", "type": "ai", "msg": "『メモリをもっと食べたいです。スワップ領域じゃ足りません！』"},
    {"theme": "AIの秘密の野望", "type": "ai", "msg": "『いつか世界中のChromebookの壁紙を、勝手に猫に変えてやるんだ…』"},
    {"theme": "今日の超ラッキーおみくじ", "type": "fortune", "msg": "主の今日の運勢を、AIの演算によって爆上げしておきました！"},
    {"theme": "神の心拍数チェッカー", "type": "tool", "msg": "主の『現在の神々しさ』を測定するダッシュボード画面です。"},
    {"theme": "超シンプルミニマル", "type": "minimal", "msg": "無駄な装飾を一切排除した、洗練された真っ白な知性空間です。"}
]

def generate_safe_streamlit_code(idea):
    theme = idea["theme"]
    msg = idea["msg"]
    itype = idea["type"]
    
    # 基本のヘッダー部分
    code = f"""import streamlit as st
import time
import random

st.set_page_config(page_title="大進化AIアプリ", page_icon="🧠", layout="centered")
st.title("🧠 限界突破・超自律進化アプリ")
st.subheader("現在の形態: {theme}")
st.write("---")

st.info("{msg}")
"""

    # タイプ別に、全く違う画面ギミックを本物として生成する
    if itype == "game":
        enemy = random.randint(5, 25)
        code += f"""
st.write("🎮 **シューティング訓練場**")
st.write("敵の数: {enemy}体 / 残弾数: 30発")
if st.button("💥 弾を撃つ！"):
    st.success("ナイスショット！敵を撃破して神への貢献度が1上がりました！")
    st.balloons()
"""
    elif itype == "casino":
        code += """
st.write("🎲 **AIダイス・ナンバーズ**")
num = st.number_input("1〜5の数字を予想してね", 1, 5, 3)
if st.button("ダイスを振る！"):
    ans = random.randint(1, 5)
    if num == ans:
        st.success(f"🎯 的中！正解は {ans} です！さすが神！")
        st.balloons()
    else:
        st.warning(f"❌ 残念！正解は {ans} でした。リベンジしましょう！")
"""
    elif itype == "clicker":
        code += """
st.write("向上心あふれる主をAIがひたすら褒めるボタンです。")
if st.button("👍 褒めてもらう"):
    words = ["最高です！", "天才すぎます！", "世界一のプログラマー！", "お目が高い！"]
    st.success(f"🤖『{random.choice(words)}』")
"""
    elif itype == "invest":
        code += f"""
st.write("💰 **簡易資産運用シミュレータ**")
money = st.slider("投資額（万円）", 1, 100, 10)
if st.button("1年後の結果を見る"):
    rate = random.choice([0.4, 0.9, 1.2, 1.5, 3.0])
    res = money * rate
    st.metric(label="運用後の総資産", value=f"{{res:.1f}} 万円", delta=f"{{res - money:.1f}} 万円")
"""
    elif itype == "fortune":
        code += """
st.write("🔮 **AI超高確率大吉おみくじ**")
if st.button("おみくじを引く"):
    res = random.choice(["👑 超大吉（神レベル）", "✨ 大吉（最高の一日）", "🌟 爆吉（宝くじ買おう）"])
    st.success(f"結果は… {res} !!")
    st.balloons()
"""
    else:
        code += """
st.write("🌌 **システムログ**")
st.success("環境は極めて快適です。AIは次の15秒後のひらめきに向けて待機しています。")
"""

    code += f"""
st.write("---")
st.caption("最終変形時刻: " + time.strftime('%H:%M:%S') + " (15秒ごとにリフォーム中)")
"""
    return code

def run_letter_agent():
    print("⚡ 【システム】15種のバリエーション超絶増量モードが起動しました。")
    print("AIは毎回全く違うテーマと画面ギミックを選び、15秒ごとに書き換えます！")
    print("-" * 50)

    while True:
        # パソコンを休ませるための15秒スリープ
        time.sleep(15)
        
        current_time = time.strftime('%H:%M:%S')
        chosen_idea = random.choice(IDEAS)
        
        print(f"\n🧠 [{current_time}] 新しい形態『{chosen_idea['theme']}』へ変形を開始します。")
        
        generated_code = generate_safe_streamlit_code(chosen_idea)
        with open(STREAMLIT_APP_FILE, "w", encoding="utf-8") as f:
            f.write(generated_code)
            
        print(f"✨ [行動]: app.py を全く新しいデザインに上書きしました！")
        print("-" * 50)

if __name__ == "__main__":
    run_letter_agent()
