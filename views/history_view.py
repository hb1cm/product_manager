import streamlit as st
import pandas as pd

from datetime import datetime
from zoneinfo import ZoneInfo

from database import (
    get_active_shops,
    get_registration_history
)


def show_history_page():

    st.subheader("登録履歴")

    jan_search = st.text_input(
        "JANコード検索",
        placeholder="JANコードを入力"
    )

    st.divider()

    history = get_registration_history()

    if not history:
        st.info("登録履歴はまだありません。")
        return

    shops = get_active_shops()

    shop_codes = [
        shop["code"]
        for shop in shops
    ]

    products = {}

    jst = ZoneInfo("Asia/Tokyo")

    for item in history:

        jan = item["jan"]
        shop = item["shop_code"]

        # 登録日時を日本時間に変換
        registered_at = datetime.fromisoformat(
            item["registered_at"].replace(
                "Z",
                "+00:00"
            )
        ).astimezone(jst)

        if jan not in products:

            products[jan] = {
                "最終登録日": registered_at,
                "JANコード": jan
            }

            for code in shop_codes:
                products[jan][code] = False

        # より新しい登録日時があれば更新
        if registered_at > products[jan]["最終登録日"]:
            products[jan]["最終登録日"] = registered_at

        if shop in shop_codes:
            products[jan][shop] = True

    # 表示用の日付に変換
    for product in products.values():

        product["最終登録日"] = (
            product["最終登録日"]
            .strftime("%Y/%m/%d")
        )

    df = pd.DataFrame(
        list(products.values())
    )

    # JAN検索
    if jan_search:

        df = df[
            df["JANコード"]
            .astype(str)
            .str.contains(
                jan_search.strip(),
                na=False
            )
        ]

    if df.empty:
        st.info(
            "条件に一致する商品はありません。"
        )
        return

    # 新しい登録日を上に表示
    df = df.sort_values(
        "最終登録日",
        ascending=False
    )

    st.metric(
        "登録済み商品",
        f"{len(df)} 件"
    )

    column_config = {
        "最終登録日": st.column_config.TextColumn(
            "最終登録日",
            width="small"
        ),

        "JANコード": st.column_config.TextColumn(
            "JANコード",
            width="medium"
        )
    }

    for code in shop_codes:

        column_config[code] = (
            st.column_config.CheckboxColumn(
                code,
                disabled=True,
                width="small"
            )
        )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )