import streamlit as st

from database import (
    get_pending_requests,
    complete_request_items
)


def show_work_page():

    st.subheader("登録作業")

    requests = get_pending_requests()

    if not requests:
        st.success("現在、登録待ちの商品はありません。")
        return

    urgent_count = sum(
        1 for request in requests
        if request["priority"] == "urgent"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "登録待ち",
            f"{len(requests)} 件"
        )

    with col2:
        st.metric(
            "🔴 至急",
            f"{urgent_count} 件"
        )

    st.divider()

    for request in requests:

        product = request.get("products") or {}
        jan = product.get("jan", "")

        items = request.get("request_items") or []

        with st.container(border=True):

            # ==============================
            # 商品信息
            # ==============================

            col1, col2 = st.columns([3, 1])

            with col1:

                if request["priority"] == "urgent":
                    st.markdown(
                        f"### 🔴 至急　`{jan}`"
                    )
                else:
                    st.markdown(
                        f"### `{jan}`"
                    )

            with col2:
                st.caption(
                    f"Request ID: {request['id']}"
                )

            if request["memo"]:
                st.info(
                    f"備考：{request['memo']}"
                )

            st.markdown("#### 登録店舗")

            selected_ids = []

            # ==============================
            # 店铺任务
            # ==============================

            columns_per_row = 3

            for start in range(
                0,
                len(items),
                columns_per_row
            ):

                cols = st.columns(columns_per_row)

                row_items = items[
                    start:start + columns_per_row
                ]

                for index, item in enumerate(row_items):

                    with cols[index]:

                        shop = item["shop_code"]
                        price = item["price"]

                        if price is not None:
                            label = (
                                f"{shop}　¥{price:,}"
                            )
                        else:
                            label = shop

                        # 已完成的显示为锁定状态
                        if item["completed"]:

                            st.checkbox(
                                f"✅ {label}",
                                value=True,
                                disabled=True,
                                key=f"done_{item['id']}"
                            )

                        else:

                            checked = st.checkbox(
                                label,
                                key=f"work_{item['id']}"
                            )

                            if checked:
                                selected_ids.append(
                                    item["id"]
                                )

            st.write("")

            # ==============================
            # 完成按钮
            # ==============================

            if st.button(
                "チェックした店舗を登録完了にする",
                key=f"complete_request_{request['id']}",
                type="primary"
            ):

                if not selected_ids:

                    st.warning(
                        "完了した店舗を選択してください。"
                    )

                else:

                    try:

                        complete_request_items(
                            request["id"],
                            selected_ids
                        )

                        st.success(
                            "登録完了として保存しました。"
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"保存に失敗しました：{e}"
                        )