# app.py
# グノーシア風・一人用人狼っぽいミニゲーム（ターン制限追加版）
# 実行方法：streamlit run app.py

import random
import streamlit as st

# ---------------------------------------
# 基本設定
# ---------------------------------------
PLAYER_NAME = "あなた"
NPC_NAMES = ["シグマ", "レムナ", "ジョナス"]
ROLES = ["人間", "グノーシア"]
MAX_DISCUSSION_TURNS = 5  # 議論最大ターン数

# ---------------------------------------
# ゲーム状態の初期化
# ---------------------------------------
def init_game():
    """ゲーム開始時に一度だけ呼び出して状態を初期化する。"""
    all_names = [PLAYER_NAME] + NPC_NAMES
    roles = {name: "人間" for name in all_names}
    gnosia = random.choice(all_names)
    roles[gnosia] = "グノーシア"

    st.session_state.roles = roles
    st.session_state.alive = {name: True for name in all_names}
    st.session_state.day = 1
    st.session_state.phase = "discussion"
    st.session_state.log = []
    st.session_state.vote_target = None
    st.session_state.npc_votes = {}
    st.session_state.game_over = False
    st.session_state.win = None
    st.session_state.player_statement = None
    st.session_state.discussion_turn = 0  # 議論ターンカウンター（新追加）

    # 冒頭メッセージ
    st.session_state.log.append("🌌 **ゲーム開始！** あなたを含む4人の中に、グノーシアが1人います。")
    st.session_state.log.append("あなたの役職はサイドバーで確認してください。")
    st.session_state.log.append("議論→投票を繰り返し、勝利を目指しましょう！")
    st.session_state.log.append(f"※1日あたり議論は最大{MAX_DISCUSSION_TURNS}ターンです。")

# ---------------------------------------
# NPC発言ロジック
# ---------------------------------------
def npc_talks():
    """NPCが順番に発言する（1ラウンド分）"""
    alive_names = [name for name, alive in st.session_state.alive.items() if alive]
    current_npcs = [n for n in NPC_NAMES if st.session_state.alive[n]]

    if len(alive_names) <= 2:
        return

    st.session_state.log.append("")
    st.session_state.log.append(f"―― NPCたちの発言（{st.session_state.day}日目・{st.session_state.discussion_turn + 1}/{MAX_DISCUSSION_TURNS}ターン）――")

    for npc in current_npcs:
        candidates = [n for n in alive_names if n != npc]
        if not candidates:
            continue
        target = random.choice(candidates)

        role = st.session_state.roles[npc]
        if role == "グノーシア" and st.session_state.roles[target] == "人間":
            msg = f"{npc}：{target}が怪しい気がする……。"
        else:
            msg = f"{npc}：{target}は信用してもよさそうだね。"
        st.session_state.log.append(msg)

# ---------------------------------------
# 投票ロジック
# ---------------------------------------
def npc_votes():
    """NPCの投票を決定"""
    alive_names = [name for name, alive in st.session_state.alive.items() if alive]
    current_npcs = [n for n in NPC_NAMES if st.session_state.alive[n]]

    votes = {}
    if len(alive_names) <= 1:
        return votes

    for npc in current_npcs:
        candidates = [n for n in alive_names if n != npc]
        if not candidates:
            continue
        weights = [1.5 if c == PLAYER_NAME else 1.0 for c in candidates]
        target = random.choices(candidates, weights=weights, k=1)[0]
        votes[npc] = target

    st.session_state.npc_votes = votes
    return votes

def apply_vote():
    """投票結果を適用"""
    alive_names = [name for name, alive in st.session_state.alive.items() if alive]
    votes = {}
    votes.update(st.session_state.npc_votes)

    if st.session_state.vote_target is not None:
        votes[PLAYER_NAME] = st.session_state.vote_target
    else:
        candidates = [n for n in alive_names if n != PLAYER_NAME]
        if candidates:
            votes[PLAYER_NAME] = random.choice(candidates)

    # 集計
    counter = {}
    for v in votes.values():
        counter[v] = counter.get(v, 0) + 1

    st.session_state.log.append("―― 投票結果 ――")
    for voter, target in votes.items():
        st.session_state.log.append(f"{voter} → {target}")

    max_votes = max(counter.values())
    top_candidates = [name for name, cnt in counter.items() if cnt == max_votes]
    eliminated = random.choice(top_candidates)

    st.session_state.alive[eliminated] = False
    role = st.session_state.roles[eliminated]
    st.session_state.log.append(f"【{eliminated}】が排除されました。（正体：{role}）")
    check_win_condition()

def check_win_condition():
    """勝敗判定（役職ごとの陣営勝利を正確に判定）"""
    alive_roles = [
        st.session_state.roles[name]
        for name, alive in st.session_state.alive.items()
        if alive
    ]
    human_count = alive_roles.count("人間")
    gn_count = alive_roles.count("グノーシア")

    your_role = st.session_state.roles[PLAYER_NAME]

    if gn_count == 0:  # グノーシア全滅
        st.session_state.game_over = True
        st.session_state.win = (your_role == "人間")
        st.session_state.phase = "result"
        st.session_state.log.append("グノーシアはすべて排除されました！")
        return

    if human_count <= gn_count:  # グノーシア有利
        st.session_state.game_over = True
        st.session_state.win = (your_role == "グノーシア")
        st.session_state.phase = "result"
        st.session_state.log.append("人間よりグノーシアの数が多くなってしまった……。")
        return

    # 続行（ターンカウンターをリセット）
    st.session_state.game_over = False
    st.session_state.win = None
    st.session_state.phase = "discussion"
    st.session_state.discussion_turn = 0  # リセット
    st.session_state.day += 1
    st.session_state.log.append("")
    st.session_state.log.append(f"―― 第{st.session_state.day}日 朝 ――")

# ---------------------------------------
# Streamlit UI
# ---------------------------------------
def main():
    st.set_page_config(page_title="グノーシア風ミニゲーム", page_icon="🛰")
    st.title("🛰 一人用・グノーシア風ミニゲーム")

    if "roles" not in st.session_state:
        init_game()

    # サイドバー：ゲーム情報＋プレイヤー役職
    with st.sidebar:
        st.header("📊 ゲーム情報")
        st.markdown(f"**日数**: 第 {st.session_state.day} 日")
        st.markdown(f"**現在のフェーズ**: {st.session_state.phase}")
        st.markdown(f"**議論ターン**: {st.session_state.discussion_turn}/{MAX_DISCUSSION_TURNS}")
        
        alive_list = [name for name, alive in st.session_state.alive.items() if alive]
        st.markdown("**生存者**:")
        for name in alive_list:
            if name == PLAYER_NAME:
                st.markdown(f"• **{name}**（{st.session_state.roles[name]}）")
            else:
                st.markdown(f"• {name}")

        st.markdown("---")
        if st.button("🔄 新ゲーム開始"):
            init_game()
            st.rerun()

    # メイン：ログ表示
    st.subheader("📜 議論ログ")
    for line in st.session_state.log:
        st.write(line)
    st.markdown("---")

    # ゲーム中
    if not st.session_state.game_over:
        if st.session_state.phase == "discussion":
            st.subheader("💬 議論フェーズ")
            
            # ターン制限警告
            remaining_turns = MAX_DISCUSSION_TURNS - st.session_state.discussion_turn
            if remaining_turns <= 2:
                st.warning(f"⚠️ 議論はあと{remaining_turns}ターンです！")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ NPCに発言させる", use_container_width=True):
                    npc_talks()
                    st.session_state.discussion_turn += 1  # ターン加算
                    st.rerun()
            
            with col2:
                if st.button("➡️ 投票フェーズへ", use_container_width=True):
                    st.session_state.phase = "vote"
                    st.session_state.log.append("―― 投票タイム ――")
                    st.rerun()

            # プレイヤーの疑う/庇う発言
            st.markdown("### あなたの立場表明")
            alive_names = [name for name, alive in st.session_state.alive.items() if alive]
            candidates = [n for n in alive_names if n != PLAYER_NAME]
            
            stance_options = []
            for name in candidates:
                stance_options.append(f"{name}を**疑う**")
                stance_options.append(f"{name}を**庇う**")
            
            stance = st.selectbox(
                "立場を表明：",
                options=stance_options,
                key="stance_select"
            )
            
            if st.button("発言する", use_container_width=True):
                if stance:
                    st.session_state.log.append(f"{PLAYER_NAME}：{stance}")
                    st.session_state.player_statement = stance
                    st.rerun()

            # ターン制限超過チェック
            if st.session_state.discussion_turn >= MAX_DISCUSSION_TURNS:
                st.error("⏰ 議論ターン上限に達しました！強制的に投票フェーズへ移行します。")
                st.session_state.phase = "vote"
                st.session_state.log.append("―― 議論時間終了！投票タイムへ強制移行 ――")
                st.rerun()

        elif st.session_state.phase == "vote":
            st.subheader("🗳️ 投票フェーズ")
            alive_names = [name for name, alive in st.session_state.alive.items() if alive]
            candidates = [n for n in alive_names if n != PLAYER_NAME]

            st.write("怪しいと思う人物に投票してください。")
            vote_choice = st.radio("投票先：", options=candidates)
            
            if st.button("投票する", use_container_width=True):
                st.session_state.vote_target = vote_choice
                npc_votes()
                apply_vote()
                st.rerun()

    # ゲーム終了
    if st.session_state.game_over and st.session_state.phase == "result":
        st.subheader("🏁 ゲーム結果")
        your_role = st.session_state.roles[PLAYER_NAME]
        
        st.markdown(f"### あなたの役職：**{your_role}**")
        
        if st.session_state.win:
            st.success("🎉 **あなたの陣営の勝利！**")
        else:
            st.error("💥 **あなたの陣営の敗北…**")
        
        with st.expander("👥 全員の役職と結果"):
            for name, role in st.session_state.roles.items():
                alive_status = "☠️排除済み" if not st.session_state.alive[name] else "✅生存"
                st.write(f"- {name}：{role} ({alive_status})")
        
        if st.button("🔄 もう一度遊ぶ", use_container_width=True):
            init_game()
            st.rerun()

if __name__ == "__main__":
    main()
