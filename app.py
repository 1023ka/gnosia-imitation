# app.py
# グノーシア風・一人用人狼っぽいミニゲーム（議論5ターン固定＋好感度システム）
# 実行方法：streamlit run app.py

import random
import streamlit as st

# ---------------------------------------
# 基本設定
# ---------------------------------------
PLAYER_NAME = "あなた"
NPC_NAMES = ["セツ", "ラキオ", "SQ"]
ROLES = ["人間", "グノーシア"]
MAX_DISCUSSION_TURNS = 5  # 1日あたり議論ターン数（固定）

# 好感度の変化量
LIKE_DELTA_UP = 1     # 庇われたときの上昇量
LIKE_DELTA_DOWN = -1  # 疑われたときの減少量

# ---------------------------------------
# 好感度ユーティリティ
# ---------------------------------------
def init_like_map(names):
    """全キャラ間の好感度を0で初期化（自分自身への好感度は持たない）"""
    like_map = {}
    for a in names:
        like_map[a] = {}
        for b in names:
            if a == b:
                continue
            like_map[a][b] = 0
    return like_map

def change_like(from_name, to_name, delta):
    """from_name から to_name への好感度を変化させる"""
    if "like_map" not in st.session_state:
        return
    if from_name not in st.session_state.like_map:
        return
    if to_name not in st.session_state.like_map[from_name]:
        return
    st.session_state.like_map[from_name][to_name] += delta

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
    st.session_state.discussion_turn = 0  # その日の議論ターン（0〜MAX_DISCUSSION_TURNS）
    st.session_state.like_map = init_like_map(all_names)  # 好感度マップ

    st.session_state.log.append("🌌 **ゲーム開始！** あなたを含む4人の中に、グノーシアが1人います。")
    st.session_state.log.append("あなたの役職はサイドバーで確認してください。")
    st.session_state.log.append("議論→投票を繰り返し、勝利を目指しましょう！")
    st.session_state.log.append(f"※1日あたり議論はちょうど{MAX_DISCUSSION_TURNS}ターン行われます。")

# ---------------------------------------
# NPC発言ロジック（好感度を考慮）
# ---------------------------------------
def npc_talks():
    """NPCが順番に発言する（1ターン分）。好感度と役職を考慮して「疑う/庇う」を選択。"""
    alive_names = [name for name, alive in st.session_state.alive.items() if alive]
    current_npcs = [n for n in NPC_NAMES if st.session_state.alive[n]]

    if len(alive_names) <= 2:
        return

    turn_no = st.session_state.discussion_turn + 1
    st.session_state.log.append("")
    st.session_state.log.append(
        f"―― NPCたちの発言（{st.session_state.day}日目・{turn_no}/{MAX_DISCUSSION_TURNS}ターン）――"
    )

    for npc in current_npcs:
        # 自分以外の生存者
        candidates = [n for n in alive_names if n != npc]
        if not candidates:
            continue

        # 好感度に応じて「誰を疑いやすいか / 誰を庇いやすいか」を決める
        likes = st.session_state.like_map[npc]

        # 疑い先候補：好感度が低い人ほど選ばれやすい
        # 庇い先候補：好感度が高い人ほど選ばれやすい
        def softmax_weights(values, reverse=False):
            # reverse=False: 大きいほど重く, True: 小さいほど重く
            # ここでは簡易的に (base + value) で重みをつける
            base = 1.0
            weights = []
            for v in values:
                if reverse:
                    w = max(0.1, base - 0.2 * v)  # 好感度が高いと軽く
                else:
                    w = max(0.1, base + 0.2 * v)  # 好感度が高いと重く
                weights.append(w)
            return weights

        like_values = [likes.get(c, 0) for c in candidates]

        # 「疑う」or「庇う」をランダムに選ぶが、人間もそれなりに疑う
        # グノーシア：人間を疑いやすいが、好感度も少し考慮
        # 人間：好感度の低い相手を疑いやすく、高い相手を庇いやすい
        role = st.session_state.roles[npc]

        # 行動タイプを決める
        if role == "グノーシア":
            action = random.choices(["疑う", "庇う"], weights=[0.7, 0.3], k=1)[0]
        else:
            action = random.choices(["疑う", "庇う"], weights=[0.6, 0.4], k=1)[0]

        if action == "疑う":
            # 好感度が低いほど重くする
            weights = softmax_weights([-v for v in like_values], reverse=False)
            target = random.choices(candidates, weights=weights, k=1)[0]
            msg = f"{npc}：{target}が怪しい気がする……。"
            st.session_state.log.append(msg)
            # 疑われた側から見て、疑ってきた相手への好感度を下げる
            change_like(target, npc, LIKE_DELTA_DOWN)
        else:
            # 好感度が高いほど重くする
            weights = softmax_weights(like_values, reverse=False)
            target = random.choices(candidates, weights=weights, k=1)[0]
            msg = f"{npc}：{target}は信用してもよさそうだね。"
            st.session_state.log.append(msg)
            # 庇われた側から見て、庇ってくれた相手への好感度を上げる
            change_like(target, npc, LIKE_DELTA_UP)

# ---------------------------------------
# プレイヤー発言の処理（好感度更新）
# ---------------------------------------
def apply_player_statement(statement: str):
    """
    プレイヤーの「〜を疑う／〜を庇う」発言に応じて、対象NPCからプレイヤーへの好感度を更新。
    例: "シグマを疑う", "レムナを庇う"
    """
    if not statement:
        return
    # 対象名と行動をざっくり取り出す
    # 形式: "{名前}を**疑う**" / "{名前}を**庇う**"
    # 太字記号を無視して処理
    s = statement.replace("**", "")
    if "を疑う" in s:
        name = s.split("を疑う")[0]
        action = "疑う"
    elif "を庇う" in s:
        name = s.split("を庇う")[0]
        action = "庇う"
    else:
        return

    target = name
    if target not in st.session_state.alive:
        return

    if action == "疑う":
        # 疑われたNPCから見て、プレイヤーへの好感度ダウン
        change_like(target, PLAYER_NAME, LIKE_DELTA_DOWN)
    elif action == "庇う":
        # 庇われたNPCから見て、プレイヤーへの好感度アップ
        change_like(target, PLAYER_NAME, LIKE_DELTA_UP)

# ---------------------------------------
# 投票ロジック（好感度反映）
# ---------------------------------------
def npc_votes():
    """NPCの投票を決定。好感度が低い相手を狙いやすい。"""
    alive_names = [name for name, alive in st.session_state.alive.items() if alive]
    current_npcs = [n for n in NPC_NAMES if st.session_state.alive[n]]

    votes = {}
    if len(alive_names) <= 1:
        return votes

    for npc in current_npcs:
        candidates = [n for n in alive_names if n != npc]
        if not candidates:
            continue

        likes = st.session_state.like_map[npc]
        like_values = [likes.get(c, 0) for c in candidates]

        # 好感度が低い相手ほど重く（かつプレイヤーにも少しバイアス）
        weights = []
        for c, v in zip(candidates, like_values):
            base = 1.0
            # 好感度が低いほど基礎重みを上げる
            w = base + (-0.3 * v)
            if c == PLAYER_NAME:
                w += 0.3  # プレイヤーに少しヘイトが乗りやすい
            weights.append(max(0.1, w))

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

# ---------------------------------------
# 勝敗判定
# ---------------------------------------
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

    if gn_count == 0:
        st.session_state.game_over = True
        st.session_state.win = (your_role == "人間")
        st.session_state.phase = "result"
        st.session_state.log.append("グノーシアはすべて排除されました！")
        return

    if human_count <= gn_count:
        st.session_state.game_over = True
        st.session_state.win = (your_role == "グノーシア")
        st.session_state.phase = "result"
        st.session_state.log.append("人間よりグノーシアの数が多くなってしまった……。")
        return

    # 続行（新しい日へ）
    st.session_state.game_over = False
    st.session_state.win = None
    st.session_state.phase = "discussion"
    st.session_state.discussion_turn = 0  # 新しい日の議論はまた0から
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

    # サイドバー
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

    # メインログ
    st.subheader("📜 議論ログ")
    for line in st.session_state.log:
        st.write(line)
    st.markdown("---")

    # ゲーム中
    if not st.session_state.game_over:
        if st.session_state.phase == "discussion":
            st.subheader("💬 議論フェーズ")

            remaining_turns = MAX_DISCUSSION_TURNS - st.session_state.discussion_turn
            st.info(f"この日に残された議論ターン：{remaining_turns} / {MAX_DISCUSSION_TURNS}")

            # NPC発言 → プレイヤー発言 の1ターン
            if st.button("▶️ 1ターン進める（NPC発言 → あなたの発言）", use_container_width=True):
                # NPC発言
                npc_talks()
                st.session_state.discussion_turn += 1
                st.rerun()

            # 「ターン進める」ボタンが押された後に、プレイヤーの発言を受付
            # （UIとしては常に表示しておく）
            st.markdown("### あなたの立場表明")
            alive_names = [name for name, alive in st.session_state.alive.items() if alive]
            candidates = [n for n in alive_names if n != PLAYER_NAME]

            stance_options = []
            for name in candidates:
                stance_options.append(f"{name}を**疑う**")
                stance_options.append(f"{name}を**庇う**")

            stance = st.selectbox(
                "立場を表明：",
                options=["（まだ発言しない）"] + stance_options,
                key="stance_select",
            )

            if st.button("発言する", use_container_width=True):
                if stance != "（まだ発言しない）":
                    st.session_state.log.append(f"{PLAYER_NAME}：{stance}")
                    st.session_state.player_statement = stance
                    apply_player_statement(stance)
                    st.rerun()

            # 5ターン経過したら自動で投票フェーズへ
            if st.session_state.discussion_turn >= MAX_DISCUSSION_TURNS:
                st.warning("⏰ 規定の5ターンの議論が終了しました。投票フェーズに移ります。")
                st.session_state.phase = "vote"
                st.session_state.log.append("―― 議論終了。投票タイムへ移行 ――")
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
