import streamlit as st

from views.request_view import show_request_page
from views.work_view import show_work_page
from views.search_view import show_search_page
from views.history_view import show_history_page


st.set_page_config(
    page_title="商品登録管理",
    page_icon="📝",
    layout="wide"
)

st.title("📝 商品登録管理")

page = st.segmented_control(
    "ページ",
    [
        "📝 登録依頼",
        "✅ 登録作業",
        "🔍 JAN検索",
        "📚 登録履歴"
    ],
    default="📝 登録依頼",
    label_visibility="collapsed"
)

st.divider()

if page == "📝 登録依頼":
    show_request_page()

elif page == "✅ 登録作業":
    show_work_page()

elif page == "🔍 JAN検索":
    show_search_page()

elif page == "📚 登録履歴":
    show_history_page()