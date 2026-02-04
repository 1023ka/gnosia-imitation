# app.py
# グノーシア風・一人用人狼っぽいミニゲーム
# 6NPC + グノーシア1〜2人ランダム + 夜の「消す」処理付き
# 実行: streamlit run app.py

import random
import streamlit as st

# ---------------------------------------
# 基本設定
# ---------------------------------------
PLAYER_NAME = "あなた"
NPC_NAMES = ["セツ", "ラキオ", "SQ", "ジナ", "ステラ", "しげみち"]
ROLES = ["人間", "グノーシア"]
MAX_DISCUSSION_TURNS = 5  # 1日あたり議論ターン数

LIKE_DELTA_UP = 1     # 庇われたときの好感度上昇
LIKE_DELTA_DOWN = -1  # 疑われたときの好感度下降

# ---------------------------------------
# 好感度ユーティリティ
# ---------------------------------------
def init_like_map(names):
    """全キャラ間の好感度を0で初期化"""
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

    # グノーシア人数を 1〜2 でランダム決定
    gn_count = random.choice([1, 2])
    roles = {name: "人間" for name in all_names}
    gnosias = random.sample(all_names, gn_count)
    for g in gnosias:
        roles[g] = "グノーシア"

    st.session_state.roles = roles
    st.session_state.alive = {name: True for name in all_names}
    st.session_state.day = 1
    st.session_state.phase = "discussion"  # discussion → vote → night → result
    st.session_state.log = []
    st.session_state.vote_target = None
    st.session_state.npc_votes = {}
    st.session_state.game_over = False
    st.session_state.win = None
    st.session_state.player_statement = None
    st.session_state.discussion_turn = 0
    st.session_state.like_map = init_like_map(all_names)

    st.session_state.log.append("🌌 **ゲーム開始！** あなたを含む7人の中に、グノーシアが1〜2人います。")
    st.session_state.log.append("あなたの役職はサイドバーで確認してください。")
    st.session_state.log.append("議論→投票→夜の襲撃を繰り返し、勝利を目指しましょう！")
    st.session_state.log.append(f"※1日あたり議論はちょうど{MAX_DISCUSSION_TURNS}ターン行われます。")

# ---------------------------------------
# NPC発言（好感度反映）
# ---------------------------------------
def npc_talks():
    """NPCが順番に発言する（1ターン分）"""
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
        candidates = [n for n in alive_names if n != npc]
        if not candidates:
            continue

        likes = st.session_state.like_map[npc]
        like_values = [likes.get(c, 0) for c in candidates]

        def weight_from_like_for_suspicion(like_vals):
            # 好感度が低いほど重く
            weights = []
            for v in like_vals:
                w = 1.0 + max(0.0, -0.3 * v)
                weights.append(max(0.1, w))
            return weights

        def weight_from_like_for_trust(like_vals):
            # 好感度が高いほど重く
            weights = []
            for v in like_vals:
                w = 1.0 + 0.3 * v
                weights.append(max(0.1, w))
            return weights

        role = st.session_state.roles[npc]
        if role == "グノーシア":
            action = random.choices(["疑う", "庇う"], weights=[0.7, 0.3], k=1)[0]
        else:
            action = random.choices(["疑う", "庇う"], weights=[0.6, 0.4], k=1)[0]

        if action == "疑う":
            weights = weight_from_like_for_suspicion(like_values)
            target = random.choices(candidates, weights=weights, k=1)[0]
            msg = f"{npc}：{target}が怪しい気がする……。"
            st.session_state.log.append(msg)
            change_like(target, npc, LIKE_DELTA_DOWN)
        else:
            weights = weight_from_like_for_trust(like_values)
            target = random.choices(candidates, weights=weights, k=1)[0]
            msg = f"{npc}：{target}は信用してもよさそうだね。"
            st.session_state.log.append(msg)
            change_like(target, npc, LIKE_DELTA_UP)

# ---------------------------------------
# プレイヤー発言 → 好感度反映
# ---------------------------------------
def apply_player_statement(statement: str):
    """プレイヤーの『〜を疑う／〜を庇う』に応じて、対象NPC→プレイヤーの好感度を更新"""
    if not statement or statement == "（まだ発言しない）":
        return
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
        change_like(target, PLAYER_NAME, LIKE_DELTA_DOWN)
    elif action == "庇う":
        change_like(target, PLAYER_NAME, LIKE_DELTA_UP)

# ---------------------------------------
# 投票ロジック（好感度反映）
# ---------------------------------------
def npc_votes():
    """NPCの投票先を決定（好感度低い相手狙い＋プレイヤー少し狙われやすい）"""
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

        weights = []
        for c, v in zip(candidates, like_values):
            base = 1.0 + max(0.0, -0.3 * v)  # 好感度が低いほど重く
            if c == PLAYER_NAME:
                base += 0.3
            weights.append(max(0.1, base))

        target = random.choices(candidates, weights=weights, k=1)[0]
        votes[npc] = target

    st.session_state.npc_votes = votes
    return votes

def apply_vote():
    """昼の投票結果を適用（追放）"""
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
    st.session_state.log.append(f"【{eliminated}】が追放されました。（正体：{role}）")

    # 追放後に即勝敗がつくかチェック（グノーシア全滅 or 人間≦グノ）
    if check_win_condition():
        return
    # まだ続く場合は夜フェーズへ
    st.session_state.phase = "night"
    st.session_state.log.append("")
    st.session_state.log.append("―― 夜がやってきた……グノーシアが誰かを『消す』 ――")

# ---------------------------------------
# 夜フェーズ：グノーシアによる襲撃
# ---------------------------------------
def gn_kill_target_for_npc():
    """NPCグノーシアたちが協議したことにして、人間1人を好感度をもとに選んで『消す』"""
    alive_names = [n for n, a in st.session_state.alive.items() if a]
    # 生存しているグノーシア
    gn_list = [n for n in alive_names if st.session_state.roles[n] == "グノーシア"]
    # 生存している人間
    human_list = [n for n in alive_names if st.session_state.roles[n] == "人間"]

    if not gn_list or not human_list:
        return None

    # 各グノーシアの「好感度の低い人間」を重ね合わせるイメージで重みをつける
    weight_map = {h: 0.0 for h in human_list}
    for gn in gn_list:
        likes = st.session_state.like_map[gn]
        for h in human_list:
            v = likes.get(h, 0)
            # 好感度が低いほど加点（狙われやすい）
            weight_map[h] += max(0.1, 1.0 + -0.3 * v)

    targets = list(weight_map.keys())
    weights = list(weight_map.values())
    if not targets or sum(weights) == 0:
        return random.choice(human_list)

    target = random.choices(targets, weights=weights, k=1)[0]
    return target

def apply_night_kill(target):
    """夜に対象を『消す』処理"""
    if target is None:
        return
    if not st.session_state.alive.get(target, False):
        return
    st.session_state.alive[target] = False
    role = st.session_state.roles[target]
    st.session_state.log.append(f"【{target}】が夜の間に『消されて』しまった……。（正体：{role}）")
    check_win_condition()

# ---------------------------------------
# 勝敗判定
# ---------------------------------------
def check_win_condition():
    """勝敗判定。決着したら True を返す。"""
    alive_roles = [
        st.session_state.roles[name]
        for name, alive in st.session_state.alive.items()
        if alive
    ]
    human_count = alive_roles.count("人間")
    gn_count = alive_roles.count("グノーシア")

    your_role = st.session_state.roles[PLAYER_NAME]

    # グノーシア全滅 → 人間陣営勝ち
    if gn_count == 0:
        st.session_state.game_over = True
        st.session_state.win = (your_role == "人間")
        st.session_state.phase = "result"
        st.session_state.log.append("グノーシアはすべて排除されました！")
        return True

    # 人間数 <= グノーシア数 → グノーシア陣営勝ち
    if human_count <= gn_count:
        st.session_state.game_over = True
        st.session_state.win = (your_role == "グノーシア")
        st.session_state.phase = "result"
        st.session_state.log.append("人間よりグノーシアの数が多くなってしまった……。")
        return True

    # 続行
    st.session_state.game_over = False
    st.session_state.win = None
    return False

# ---------------------------------------
# Streamlit UI
# ---------------------------------------
def main():
    st.set_page_config(page_title="グノーシア風ミニゲーム", page_icon="🛰")
    st.title("🛰 一人用・グノーシア風ミニゲーム（6NPC＋夜フェーズ）")

    if "roles" not in st.session_state:
        init_game()

    # サイドバー
    with st.sidebar:
        st.header("📊 ゲーム情報")
        st.markdown(f"**日数**: 第 {st.session_state.day} 日")
        st.markdown(f"**フェーズ**: {st.session_state.phase}")
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
    st.subheader("📜 ログ")
    for line in st.session_state.log:
        st.write(line)
    st.markdown("---")

    # ゲーム中
    if not st.session_state.game_over:
        # ---------------- discussion ----------------
        if st.session_state.phase == "discussion":
            st.subheader("💬 議論フェーズ")

            remaining_turns = MAX_DISCUSSION_TURNS - st.session_state.discussion_turn
            st.info(f"この日に残された議論ターン：{remaining_turns} / {MAX_DISCUSSION_TURNS}")

            if st.session_state.discussion_turn < MAX_DISCUSSION_TURNS:
                if st.button("▶️ 1ターン進める（NPC発言 → あなたの発言）", use_container_width=True):
                    npc_talks()
                    st.session_state.discussion_turn += 1
                    st.rerun()
            else:
                st.warning("⏰ 規定の5ターンの議論が終了しました。自動で投票フェーズに移行します。")
                st.session_state.phase = "vote"
                st.session_state.log.append("―― 議論終了。投票タイムへ移行 ――")
                st.rerun()

            # プレイヤーの発言
            st.markdown("### あなたの立場表明")
            alive_names = [name for name, alive in st.session_state.alive.items() if alive]
            candidates = [n for n in alive_names if n != PLAYER_NAME]

            stance_options = ["（まだ発言しない）"]
            for name in candidates:
                stance_options.append(f"{name}を**疑う**")
                stance_options.append(f"{name}を**庇う**")

            stance = st.selectbox("立場を表明：", options=stance_options, key="stance_select")

            if st.button("発言する", use_container_width=True):
                if stance != "（まだ発言しない）":
                    st.session_state.log.append(f"{PLAYER_NAME}：{stance}")
                    st.session_state.player_statement = stance
                    apply_player_statement(stance)
                    st.rerun()

        # ---------------- vote ----------------
        elif st.session_state.phase == "vote":
            st.subheader("🗳️ 投票フェーズ")
            alive_names = [name for name, alive in st.session_state.alive.items() if alive]
            candidates = [n for n in alive_names if n != PLAYER_NAME]

            st.write("怪しいと思う人物に投票してください。")
            if not candidates:
                st.write("投票先候補がいません。")
            else:
                vote_choice = st.radio("投票先：", options=candidates)
                if st.button("投票する", use_container_width=True):
                    st.session_state.vote_target = vote_choice
                    npc_votes()
                    apply_vote()
                    st.rerun()

        # ---------------- night ----------------
        elif st.session_state.phase == "night":
            st.subheader("🌙 夜フェーズ（グノーシアの行動）")

            alive_names = [name for name, alive in st.session_state.alive.items() if alive]
            gn_list = [n for n in alive_names if st.session_state.roles[n] == "グノーシア"]
            human_list = [n for n in alive_names if st.session_state.roles[n] == "人間"]

            # すでに勝敗が決まっている場合は何もしない
            if st.session_state.game_over:
                st.stop()

            your_role = st.session_state.roles[PLAYER_NAME]

            # グノーシアがいない or 人間がいない → 夜に誰も消えない（ほぼ該当しないが安全策）
            if not gn_list or not human_list:
                st.session_state.log.append("この夜には誰も『消されなかった』ようだ……。")
                # 次の日の朝へ（勝敗チェック含む）
                if not check_win_condition():
                    st.session_state.phase = "discussion"
                    st.session_state.discussion_turn = 0
                    st.session_state.day += 1
                    st.session_state.log.append("")
                    st.session_state.log.append(f"―― 第{st.session_state.day}日 朝 ――")
                st.rerun()

            # プレイヤーがグノーシア → プレイヤーが消す相手を選ぶ
            if your_role == "グノーシア" and st.session_state.alive[PLAYER_NAME]:
                st.write("あなたはグノーシアです。今夜『消す』人間を1人選んでください。")
                kill_candidates = [h for h in human_list if h != PLAYER_NAME]
                # 念のため、自分は含めない（自殺防止）
                if not kill_candidates:
                    st.write("『消す』対象となる人間がいません。")
                    # 次の日へ
                    if not check_win_condition():
                        st.session_state.phase = "discussion"
                        st.session_state.discussion_turn = 0
                        st.session_state.day += 1
                        st.session_state.log.append("")
                        st.session_state.log.append(f"―― 第{st.session_state.day}日 朝 ――")
                    st.rerun()
                else:
                    target = st.radio("『消す』相手：", options=kill_candidates)
                    if st.button("この相手を『消す』", use_container_width=True):
                        apply_night_kill(target)
                        if not st.session_state.game_over:
                            st.session_state.phase = "discussion"
                            st.session_state.discussion_turn = 0
                            st.session_state.day += 1
                            st.session_state.log.append("")
                            st.session_state.log.append(f"―― 第{st.session_state.day}日 朝 ――")
                        st.rerun()
            else:
                # プレイヤーが人間 → グノーシア(NPC)が好感度を見て誰かを消す
                st.write("グノーシアたちが暗躍している……。")
                target = gn_kill_target_for_npc()
                apply_night_kill(target)
                if not st.session_state.game_over:
                    st.session_state.phase = "discussion"
                    st.session_state.discussion_turn = 0
                    st.session_state.day += 1
                    st.session_state.log.append("")
                    st.session_state.log.append(f"―― 第{st.session_state.day}日 朝 ――")
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
                alive_status = "☠️排除/消滅" if not st.session_state.alive[name] else "✅生存"
                st.write(f"- {name}：{role} ({alive_status})")

        if st.button("🔄 もう一度遊ぶ", use_container_width=True):
            init_game()
            st.rerun()

if __name__ == "__main__":
    main()
