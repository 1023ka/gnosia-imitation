# app.py
# グノーシア風・一人用人狼っぽいミニゲーム（学習用サンプル）
# 実行方法（例）:
#   streamlit run app.py

import random
import streamlit as st

# ---------------------------------------
# 基本設定
# ---------------------------------------

# プレイヤーとNPCの名前
PLAYER_NAME = "あなた"
NPC_NAMES = ["シグマ", "レムナ", "ジョナス"]

# 役職の定義
ROLES = ["人間", "グノーシア"]  # 今回はシンプルにこの2種類だけ


# ---------------------------------------
# ゲーム状態の初期化
# ---------------------------------------
def init_game():
    """ゲーム開始時に一度だけ呼び出して状態を初期化する。"""
    # プレイヤー + NPC で4人分の役職を決める
    # 例: グノーシア1人、残りは人間
    all_names = [PLAYER_NAME] + NPC_NAMES
    roles = {name: "人間" for name in all_names}
    gnosia = random.choice(all_names)
    roles[gnosia] = "グノーシア"

    # セッション状態に保存
    st.session_state.roles = roles                 # 各キャラの役職
    st.session_state.alive = {name: True for name in all_names}  # 生存フラグ
    st.session_state.day = 1                       # 日数
    st.session_state.phase = "discussion"          # "discussion" or "vote" or "result"
    st.session_state.log = []                      # 画面に表示するテキストログ
    st.session_state.vote_target = None            # プレイヤーの投票先
    st.session_state.npc_votes = {}                # NPCの投票内訳
    st.session_state.game_over = False             # 終了フラグ
    st.session_state.win = None                    # True:勝ち, False:負け, None:未決着

    # 冒頭メッセージをログに追加
    st.session_state.log.append("ゲーム開始！ あなたを含む4人の中に、グノーシアが1人います。")
    st.session_state.log.append("議論を通して怪しい人物を見つけ、投票で排除してください。")


# ---------------------------------------
# NPC発言ロジック（超シンプル）
# ---------------------------------------
def npc_talks():
    """
    議論フェーズでNPCが順番に一言ずつ話す。
    ここではあくまで「それっぽく見せる」ための簡易ロジック。
    """
    alive_names = [name for name, alive in st.session_state.alive.items() if alive]
    # プレイヤー以外
    current_npcs = [n for n in NPC_NAMES if st.session_state.alive[n]]

    # 生存者が少なすぎる場合は発言しない
    if len(alive_names) <= 2:
        return

    # 各NPCがランダムに一人を「怪しい」「信用できる」とコメント
    for npc in current_npcs:
        # 自分以外の生存者から対象を選ぶ
        candidates = [n for n in alive_names if n != npc]
        if not candidates:
            continue
        target = random.choice(candidates)

        # 役職や適当な確率を使って、ちょっとだけそれっぽく
        # （グノーシアは他人を疑いやすい、など）
        role = st.session_state.roles[npc]
        if role == "グノーシア":
            # グノーシアは比較的「人間」を疑うふりをする
            if st.session_state.roles[target] == "人間":
                sentence_type = "suspicious"
            else:
                sentence_type = random.choice(["suspicious", "trust"])
        else:
            # 人間は完全ランダム
            sentence_type = random.choice(["suspicious", "trust"])

        if sentence_type == "suspicious":
            msg = f"{npc}：{target}が怪しい気がする……。"
        else:
            msg = f"{npc}：{target}は信用してもよさそうだね。"

        st.session_state.log.append(msg)


# ---------------------------------------
# 投票ロジック
# ---------------------------------------
def npc_votes():
    """
    NPCが誰に投票するかを決める。
    非常にシンプルなルール：
      - ランダムだが、たまに特定の人物を集中して疑う
    """
    alive_names = [name for name, alive in st.session_state.alive.items() if alive]
    current_npcs = [n for n in NPC_NAMES if st.session_state.alive[n]]

    votes = {}
    if len(alive_names) <= 1:
        return votes

    for npc in current_npcs:
        candidates = [n for n in alive_names if n != npc]
        if not candidates:
            continue

        # 少しだけ「プレイヤーを狙いやすい」ようにバイアスをかけてみる
        # （理不尽さもゲーム性の一部…というイメージ）
        weights = []
        for c in candidates:
            if c == PLAYER_NAME:
                # プレイヤーは少し狙われやすい
                weights.append(1.5)
            else:
                weights.append(1.0)
        target = random.choices(candidates, weights=weights, k=1)[0]
        votes[npc] = target

    st.session_state.npc_votes = votes
    return votes


def apply_vote():
    """
    プレイヤーとNPCの投票を集計して、最多得票者を排除する。
    同票の場合はランダムで一人を選ぶ。
    """
    alive_names = [name for name, alive in st.session_state.alive.items() if alive]
    votes = {}

    # NPCの投票
    votes.update(st.session_state.npc_votes)

    # プレイヤーの投票
    if st.session_state.vote_target is not None:
        votes[PLAYER_NAME] = st.session_state.vote_target
    else:
        # プレイヤーが投票しなかった場合、ランダムに投票したとみなす
        candidates = [n for n in alive_names if n != PLAYER_NAME]
        if candidates:
            votes[PLAYER_NAME] = random.choice(candidates)

    # 集計
    counter = {}
    for v in votes.values():
        if v not in counter:
            counter[v] = 0
        counter[v] += 1

    # ログに投票内訳を表示
    st.session_state.log.append("―― 投票結果 ――")
    for voter, target in votes.items():
        st.session_state.log.append(f"{voter} → {target}")

    # 最多得票者を決定
    max_votes = max(counter.values())
    top_candidates = [name for name, cnt in counter.items() if cnt == max_votes]
    eliminated = random.choice(top_candidates)

    # 排除
    st.session_state.alive[eliminated] = False
    role = st.session_state.roles[eliminated]
    st.session_state.log.append(f"【{eliminated}】が排除されました。（正体：{role}）")

    # 勝敗判定
    check_win_condition()


def check_win_condition():
    """
    生存者の状況から勝敗を判定する。
    今回のルール：
      - グノーシアが全員排除されたら人間側の勝ち
      - 人間の数 <= グノーシアの数 になったらグノーシア勝ち
    """
    alive_roles = [
        st.session_state.roles[name]
        for name, alive in st.session_state.alive.items()
        if alive
    ]
    human_count = alive_roles.count("人間")
    gn_count = alive_roles.count("グノーシア")

    if gn_count == 0:
        st.session_state.game_over = True
        st.session_state.win = True
        st.session_state.phase = "result"
        st.session_state.log.append("グノーシアはすべて排除されました！人間の勝利です。")
        return

    if human_count <= gn_count:
        st.session_state.game_over = True
        st.session_state.win = False
        st.session_state.phase = "result"
        st.session_state.log.append("人間よりグノーシアの数が多く（または同数に）なってしまった……。グノーシアの勝利です。")
        return

    # まだ続行
    st.session_state.game_over = False
    st.session_state.win = None
    st.session_state.phase = "discussion"
    st.session_state.day += 1
    st.session_state.log.append("")
    st.session_state.log.append(f"―― 第{st.session_state.day}日 朝 ――")
    st.session_state.log.append("再び議論が始まった。")


# ---------------------------------------
# Streamlit UI 部分
# ---------------------------------------
def main():
    st.set_page_config(page_title="グノーシア風ミニゲーム", page_icon="🛰")
    st.title("一人用・グノーシア風ミニゲーム（サンプル）")

    # セッション状態がなければ初期化
    if "roles" not in st.session_state:
        init_game()

    # サイドバーに基本情報を表示
    with st.sidebar:
        st.header("ゲーム情報")
        st.markdown(f"**日数**: 第 {st.session_state.day} 日")
        alive_list = [name for name, alive in st.session_state.alive.items() if alive]
        st.markdown("**生存者**:")
        for name in alive_list:
            if name == PLAYER_NAME:
                st.write(f"- {name}（あなた）")
            else:
                st.write(f"- {name}")

        st.markdown("---")
        st.markdown("※ あなたの役職はゲーム終了後に表示されます。")

        if st.button("ゲームを最初からやり直す"):
            init_game()
            st.rerun()

    # メインエリア：ログ表示
    st.subheader("議論ログ")

    # ここで st.session_state.log をすべて表示することで、「履歴が残っている」ように見せる
    for line in st.session_state.log:
        st.write(line)

    st.markdown("---")

    # ゲームがまだ続いている場合
    if not st.session_state.game_over:
        # 議論フェーズ
        if st.session_state.phase == "discussion":
            st.subheader("議論フェーズ")

            st.write("NPCたちが話し始めます。")

            # 「議論を進める」ボタン
            if st.button("議論を進める（NPCが発言）"):
                npc_talks()
                st.rerun()

            st.markdown("プレイヤーとして、感想やメモを残してもOKです。")
            user_comment = st.text_input("（任意）一言コメント：", key="discussion_comment")
            if st.button("コメントをログに追加する"):
                if user_comment.strip():
                    st.session_state.log.append(f"{PLAYER_NAME}（あなた）：{user_comment}")
                    st.session_state.discussion_comment = ""  # 入力欄をクリアしたい場合
                    st.rerun()

            st.markdown("---")
            st.write("議論が終わったら、投票フェーズに進みます。")
            if st.button("投票フェーズへ進む"):
                st.session_state.phase = "vote"
                st.session_state.log.append("")
                st.session_state.log.append("―― 投票タイム ――")
                st.rerun()

        # 投票フェーズ
        elif st.session_state.phase == "vote":
            st.subheader("投票フェーズ")

            alive_names = [name for name, alive in st.session_state.alive.items() if alive]
            # プレイヤー本人は投票対象から除外
            candidates = [n for n in alive_names if n != PLAYER_NAME]

            st.write("怪しいと思う人物を1人選んでください。")

            # ラジオボタンで投票先を選ぶ
            vote_choice = st.radio(
                "投票先を選択：",
                options=candidates,
                index=0 if candidates else None,
            )

            # 「投票する」ボタン
            if st.button("投票する"):
                st.session_state.vote_target = vote_choice
                # NPCの投票を決める
                npc_votes()
                # 投票を適用
                apply_vote()
                st.rerun()

    # 結果フェーズ
    if st.session_state.game_over and st.session_state.phase == "result":
        st.subheader("ゲーム結果")

        # プレイヤーの役職を公開
        your_role = st.session_state.roles[PLAYER_NAME]
        st.write(f"あなたの役職：**{your_role}**")

        if st.session_state.win:
            st.success("おめでとうございます！ あなたの陣営の勝利です。")
        else:
            st.error("残念……あなたの陣営は敗北しました。")

        # 最終的な役職一覧を表示（学習用）
        with st.expander("全員の役職を確認する"):
            for name, role in st.session_state.roles.items():
                if name == PLAYER_NAME:
                    st.write(f"- {name}（あなた）：{role}")
                else:
                    st.write(f"- {name}：{role}")

        st.markdown("---")
        if st.button("もう一度遊ぶ"):
            init_game()
            st.rerun()


if __name__ == "__main__":
    main()

