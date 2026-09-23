import streamlit as st
import pandas as pd

from database import (
    get_active_shops,
    get_or_create_product,
    create_registration_request
)


def show_request_page():

    st.subheader("新規登録依頼")

    # 登録成功後にJAN入力欄をリセットするため
    if "jan_input_version" not in st.session_state:
        st.session_state["jan_input_version"] = 0

    if "shop_input_version" not in st.session_state:
        st.session_state["shop_input_version"] = 0

    if "memo_input_version" not in st.session_state:
        st.session_state["memo_input_version"] = 0

    if "urgent_input_version" not in st.session_state:
        st.session_state["urgent_input_version"] = 0

    # 登録成功メッセージ
    if "request_success_count" in st.session_state:
        st.success(
            f"{st.session_state['request_success_count']} 件の登録依頼を追加しました！"
        )
        del st.session_state["request_success_count"]

    # ==========================================
    # JAN入力
    # ==========================================

    jan_text = st.text_area(
        "JANコード *",
        placeholder=(
            "JANコードを一行に1つ入力してください\n"
            "例：\n"
            "4904810080626\n"
            "4962886010442"
        ),
        height=150,
        key=f"jan_input_{st.session_state['jan_input_version']}"
    )

    # JANを整理
    jans = []

    for line in jan_text.splitlines():

        jan = line.strip()

        if jan and jan not in jans:
            jans.append(jan)

    if jans:
        st.caption(f"{len(jans)} 件のJANコード")

    # ==========================================
    # 備考・至急
    # ==========================================

    memo = st.text_area(
        "備考",
        placeholder="必要に応じて備考を入力してください",
        height=80,
        key=f"memo_input_{st.session_state['memo_input_version']}"
    )

    urgent = st.checkbox(
        "🔴 至急",
        help="優先的に登録する必要がある商品",
        key=f"urgent_input_{st.session_state['urgent_input_version']}"
    )

    st.divider()

    # ==========================================
    # 店舗選択
    # ==========================================

    st.subheader("登録店舗")

    shops = get_active_shops()

    selected_shops = []

    columns_per_row = 3

    for start in range(
        0,
        len(shops),
        columns_per_row
    ):

        cols = st.columns(columns_per_row)

        row_shops = shops[
            start:start + columns_per_row
        ]

        for index, shop in enumerate(row_shops):

            with cols[index]:

                selected = st.checkbox(
                    shop["name"],
                    key=(
                        f"shop_{shop['code']}_"
                        f"{st.session_state['shop_input_version']}"
                    )
                )

                if selected:
                    selected_shops.append(shop)

    # ==========================================
    # 价格输入
    # ==========================================

    price_shops = [
        shop
        for shop in selected_shops
        if shop["requires_price"]
    ]

    price_df = None

    if price_shops and jans:

        st.divider()

        st.subheader("売価入力")

        st.caption(
            "Amazon・Qoo10など、売価が必要な店舗は"
            "JANごとに入力してください。"
        )

        price_data = {
            "JANコード": jans
        }

        for shop in price_shops:
            price_data[shop["code"]] = [None] * len(jans)

        base_df = pd.DataFrame(price_data)

        # JANや選択店舗が変わった場合に
        # 古い入力状態を残さないためのkey
        price_key = (
            "price_editor_"
            + "_".join(jans)
            + "_"
            + "_".join(
                shop["code"]
                for shop in price_shops
            )
        )

        column_config = {
            "JANコード": st.column_config.TextColumn(
                "JANコード",
                disabled=True,
                width="medium"
            )
        }

        for shop in price_shops:

            column_config[shop["code"]] = (
                st.column_config.NumberColumn(
                    f"{shop['name']} 売価",
                    min_value=0,
                    step=1,
                    format="%d 円",
                    required=True
                )
            )

        price_df = st.data_editor(
            base_df,
            use_container_width=True,
            hide_index=True,
            disabled=["JANコード"],
            column_config=column_config,
            key=price_key
        )

    st.divider()

    # ==========================================
    # 登録
    # ==========================================

    if st.button(
        "登録依頼を追加",
        type="primary",
        use_container_width=True
    ):

        errors = []

        memo = memo.strip()

        # JANなし
        if not jans:
            errors.append(
                "JANコードを入力してください。"
            )

        # JAN形式チェック
        invalid_jans = [
            jan
            for jan in jans
            if not jan.isdigit()
        ]

        if invalid_jans:
            errors.append(
                "JANコードは数字のみ入力してください："
                + ", ".join(invalid_jans)
            )

        # 店舗なし
        if not selected_shops:
            errors.append(
                "登録店舗を1つ以上選択してください。"
            )

        # ======================================
        # 価格チェック
        # ======================================

        price_map = {}

        if price_shops and jans and price_df is not None:

            for _, row in price_df.iterrows():

                jan = str(row["JANコード"])

                price_map[jan] = {}

                for shop in price_shops:

                    code = shop["code"]
                    value = row[code]

                    if pd.isna(value):

                        errors.append(
                            f"{jan} の {code} 売価を"
                            "入力してください。"
                        )

                    else:

                        price_map[jan][code] = int(value)

        # ======================================
        # エラー表示
        # ======================================

        if errors:

            for error in errors:
                st.error(error)

            return

        # ======================================
        # DB登録
        # ======================================

        priority = (
            "urgent"
            if urgent
            else "normal"
        )

        success_jans = []

        try:

            for jan in jans:

                product = get_or_create_product(jan)

                shop_items = []

                for shop in selected_shops:

                    code = shop["code"]

                    price = None

                    if shop["requires_price"]:
                        price = price_map[jan][code]

                    shop_items.append({
                        "shop_code": code,
                        "price": price
                    })

                create_registration_request(
                    product_id=product["id"],
                    memo=memo,
                    priority=priority,
                    shop_items=shop_items
                )

                success_jans.append(jan)

            st.session_state["request_success_count"] = len(success_jans)

            # JANをリセット
            st.session_state["jan_input_version"] += 1

            # 店舗チェックをリセット
            st.session_state["shop_input_version"] += 1

            # 備考をリセット
            st.session_state["memo_input_version"] += 1

            # 至急をリセット
            st.session_state["urgent_input_version"] += 1

            st.rerun()

        except Exception as e:

            st.error(
                f"登録中にエラーが発生しました：{e}"
            )

            if success_jans:

                st.warning(
                    f"{len(success_jans)} 件は登録済みです。"
                )