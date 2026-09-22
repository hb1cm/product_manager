import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def get_active_shops():
    """获取启用中的店铺"""
    supabase = get_supabase()

    result = (
        supabase
        .table("shops")
        .select("*")
        .eq("active", True)
        .order("sort_order")
        .execute()
    )

    return result.data


def get_or_create_product(jan):
    """JAN存在就返回，不存在则新建"""
    supabase = get_supabase()

    result = (
        supabase
        .table("products")
        .select("*")
        .eq("jan", jan)
        .execute()
    )

    if result.data:
        return result.data[0]

    result = (
        supabase
        .table("products")
        .insert({
            "jan": jan
        })
        .execute()
    )

    return result.data[0]


def create_registration_request(
    product_id,
    memo,
    priority,
    shop_items
):
    supabase = get_supabase()

    request_result = (
        supabase
        .table("requests")
        .insert({
            "product_id": product_id,
            "memo": memo,
            "priority": priority,
            "status": "pending"
        })
        .execute()
    )

    request_id = request_result.data[0]["id"]

    try:
        rows = []

        for item in shop_items:
            rows.append({
                "request_id": request_id,
                "shop_code": item["shop_code"],
                "price": item["price"],
                "completed": False
            })

        (
            supabase
            .table("request_items")
            .insert(rows)
            .execute()
        )

    except Exception:
        (
            supabase
            .table("requests")
            .delete()
            .eq("id", request_id)
            .execute()
        )

        raise

    return request_id

def get_pending_requests():
    """获取所有还没有完全结束的登录任务"""
    supabase = get_supabase()

    result = (
        supabase
        .table("requests")
        .select(
            """
            id,
            product_id,
            memo,
            priority,
            status,
            created_at,
            products(jan),
            request_items(
                id,
                shop_code,
                price,
                completed
            )
            """
        )
        .eq("status", "pending")
        .execute()
    )

    data = result.data

    # 至急排最上面，同优先级按提交时间排序
    data.sort(
        key=lambda x: (
            0 if x["priority"] == "urgent" else 1,
            x["created_at"]
        )
    )

    return data


def complete_request_items(request_id, item_ids):
    """把指定店铺标记为登录完成，并写入永久 registrations"""

    if not item_ids:
        return

    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    # 找到这个请求对应的商品
    request_result = (
        supabase
        .table("requests")
        .select("product_id")
        .eq("id", request_id)
        .execute()
    )

    product_id = request_result.data[0]["product_id"]

    # 找到这次勾选完成的店铺
    item_result = (
        supabase
        .table("request_items")
        .select("*")
        .eq("request_id", request_id)
        .in_("id", item_ids)
        .execute()
    )

    for item in item_result.data:

        if item["completed"]:
            continue

        # 1. 更新任务状态
        (
            supabase
            .table("request_items")
            .update({
                "completed": True,
                "completed_at": now
            })
            .eq("id", item["id"])
            .execute()
        )

        # 2. 写进永久登录记录
        (
            supabase
            .table("registrations")
            .upsert(
                {
                    "product_id": product_id,
                    "shop_code": item["shop_code"],
                    "price": item["price"]
                },
                on_conflict="product_id,shop_code"
            )
            .execute()
        )

    # 检查这个商品是不是已经全部登录完
    all_items_result = (
        supabase
        .table("request_items")
        .select("completed")
        .eq("request_id", request_id)
        .execute()
    )

    all_completed = all(
        item["completed"]
        for item in all_items_result.data
    )

    if all_completed:
        (
            supabase
            .table("requests")
            .update({
                "status": "completed",
                "completed_at": now
            })
            .eq("id", request_id)
            .execute()
        )

def get_registration_history(
    jan=None,
    shop_code=None,
    start_date=None,
    end_date=None
):
    """获取商品登录履历"""

    from datetime import datetime, time, timedelta
    from zoneinfo import ZoneInfo

    supabase = get_supabase()

    query = (
        supabase
        .table("registration_history_view")
        .select("*")
        .order("registered_at", desc=True)
    )

    # JAN
    if jan:
        query = query.eq("jan", jan.strip())

    # 店铺
    if shop_code and shop_code != "すべて":
        query = query.eq("shop_code", shop_code)

    # 日本时间日期范围
    jst = ZoneInfo("Asia/Tokyo")

    if start_date:
        start_dt = datetime.combine(
            start_date,
            time.min,
            tzinfo=jst
        )

        query = query.gte(
            "registered_at",
            start_dt.isoformat()
        )

    if end_date:
        end_dt = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=jst
        )

        query = query.lt(
            "registered_at",
            end_dt.isoformat()
        )

    result = query.execute()

    return result.data