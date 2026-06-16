"""
Slack 보전요청 채널 동기화 유틸리티

규칙:
  1. 채널명에 '보전요청' 포함된 채널만 대상
  2. 메인 메시지(워크플로우)만 처리 — 스레드/일반 메시지 무시
  3. '완료' 문구 없으면 진행 중, 있으면 완료
  4. 완료 이모티콘(리액션)이 달리면 완료로 전환
  5. 사진(파일) 기록 안 함
  6. 팩토리/설비명이 기존 데이터와 매칭 안 되면 slack_unmatched 별도 저장
"""

import re
from datetime import datetime, timezone

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from utils.constants import FACTORIES
from utils.database import (
    get_conn,
    upsert_slack_request,
    save_slack_unmatched,
    get_slack_last_ts,
    save_slack_last_ts,
)

# ─── 완료 판단 기준 ───────────────────────────────────────────────
# 메시지 텍스트에 이 단어 중 하나라도 포함되면 완료
COMPLETION_KEYWORDS = ["완료"]

# 이 이모티콘(reaction name)이 달리면 완료
COMPLETION_REACTIONS = {
    "white_check_mark",   # ✅
    "heavy_check_mark",   # ✔️
    "done",
    "완료",               # 커스텀 이모티콘
    "check",
}

# 워크플로우 봇 메시지를 구분하는 키워드 (본문에 포함된 경우 워크플로우로 판단)
WORKFLOW_KEYWORDS = ["팩토리", "설비명", "증상", "점검"]


# ─── 메시지 파싱 ─────────────────────────────────────────────────
def _clean_mentions(text: str) -> str:
    """슬랙 멘션(<@U...>) 제거하고 사람이 읽기 좋은 형태로 정리."""
    text = re.sub(r"<@[A-Z0-9]+>", "", text)
    text = re.sub(r"<#[A-Z0-9]+\|([^>]+)>", r"#\1", text)  # 채널 멘션
    text = re.sub(r"<([^|>]+)\|([^>]+)>", r"\2", text)      # 링크 레이블
    text = re.sub(r"<([^>]+)>", r"\1", text)                 # 그 외 <URL>
    return text.strip()


def parse_workflow_message(text: str) -> dict:
    """
    워크플로우 메시지 텍스트에서 보전 요청 정보를 파싱합니다.
    반환 형식:
        {
            "factory": str | None,
            "equipment": str | None,
            "symptom": str | None,
            "inspection": str | None,
            "assignee": str | None,
        }
    """
    text = _clean_mentions(text)

    patterns = {
        "factory":    r"팩토리\s*[:：]\s*(.+)",
        "equipment":  r"설비명\s*(?:or\s*위치)?\s*[:：]\s*(.+)",
        "symptom":    r"증상\s*[:：]\s*(.+)",
        "inspection": r"점검\s*사\s*항\s*[:：]\s*(.+)",  # '점검사항' / '점검 사항' 모두 허용
        "assignee":   r"담당자\s*[:：]\s*(.+)",
    }

    result = {}
    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            val = m.group(1).strip()
            # 다음 줄 필드 레이블이 붙어 있으면 잘라냄
            val = re.split(r"\n[가-힣a-zA-Z ]+\s*[:：]", val)[0].strip()
            result[key] = val if val else None
        else:
            result[key] = None

    return result


def is_workflow_message(text: str) -> bool:
    """워크플로우로 생성된 보전요청 메시지인지 확인."""
    if not text:
        return False
    matched = sum(1 for kw in WORKFLOW_KEYWORDS if kw in text)
    return matched >= 2


def check_completed(text: str, reactions: list) -> bool:
    """완료 여부 판단 (텍스트 키워드 or 완료 이모티콘)."""
    # 텍스트에 완료 문구
    for kw in COMPLETION_KEYWORDS:
        if kw in text:
            return True
    # 이모티콘 중 완료 관련
    for r in reactions:
        name = r.get("name", "").lower()
        if name in COMPLETION_REACTIONS or "완료" in name:
            return True
    return False


# ─── 팩토리 / 설비 매칭 ──────────────────────────────────────────
def match_factory(factory_text: str | None) -> bool:
    """슬랙 메시지의 팩토리명이 기존 FACTORIES 목록에 있는지 확인."""
    if not factory_text:
        return False
    for f in FACTORIES:
        if f in factory_text or factory_text in f:
            return True
    return False


def match_equipment(equipment_text: str | None) -> bool:
    """슬랙 메시지의 설비명이 equipment 테이블에 있는지 확인."""
    if not equipment_text:
        return False
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM equipment WHERE equipment_name ILIKE %s OR equipment_code ILIKE %s",
            (f"%{equipment_text}%", f"%{equipment_text}%"),
        )
        count = c.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


# ─── 슬랙 API 래퍼 ───────────────────────────────────────────────
def get_maintenance_channels(client: WebClient) -> list[dict]:
    """
    워크스페이스의 채널 중 이름에 '보전요청'이 포함된 채널 목록 반환.
    (공개 + 봇이 초대된 비공개 채널 모두 조회)
    """
    channels = []
    cursor = None
    while True:
        try:
            resp = client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True,
                limit=200,
                cursor=cursor,
            )
        except SlackApiError as e:
            raise RuntimeError(f"채널 목록 조회 실패: {e.response['error']}") from e

        for ch in resp.get("channels", []):
            if "보전요청" in ch.get("name", ""):
                channels.append({"id": ch["id"], "name": ch["name"]})

        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return channels


def get_message_reactions(client: WebClient, channel_id: str, ts: str) -> list:
    """메시지에 달린 이모티콘 목록 반환."""
    try:
        resp = client.reactions_get(channel=channel_id, timestamp=ts, full=True)
        msg = resp.get("message", {})
        return msg.get("reactions", [])
    except SlackApiError:
        return []


def fetch_channel_messages(client: WebClient, channel_id: str, oldest: str = "0") -> list:
    """
    채널의 메인 메시지(thread_ts == ts 이거나 없는 것)만 가져옴.
    스레드 답글(thread_ts != ts)은 제외.
    """
    messages = []
    cursor = None
    while True:
        try:
            resp = client.conversations_history(
                channel=channel_id,
                oldest=oldest,
                limit=200,
                cursor=cursor,
            )
        except SlackApiError as e:
            raise RuntimeError(f"메시지 조회 실패 ({channel_id}): {e.response['error']}") from e

        for msg in resp.get("messages", []):
            # 스레드 답글 제외 (thread_ts가 있고, thread_ts != ts 이면 답글)
            ts = msg.get("ts", "")
            thread_ts = msg.get("thread_ts")
            if thread_ts and thread_ts != ts:
                continue
            # 파일만 있는 메시지 제외 (사진 등)
            if msg.get("subtype") == "file_share":
                continue
            messages.append(msg)

        if not resp.get("has_more"):
            break
        cursor = resp.get("response_metadata", {}).get("next_cursor")

    return messages


# ─── 동기화 핵심 로직 ─────────────────────────────────────────────
def sync_channel(client: WebClient, channel_id: str, channel_name: str,
                 oldest: str = "auto") -> dict:
    """
    단일 채널의 보전요청 메시지를 DB에 동기화합니다.
    oldest='auto': 마지막 동기화 이후 메시지만 가져옴 (증분)
    oldest='0'   : 전체 재수집
    반환: {"processed": int, "skipped": int, "unmatched": int}
    """
    stats = {"processed": 0, "skipped": 0, "unmatched": 0}

    # 증분 동기화: 'auto'면 마지막 저장된 ts 이후만 가져옴
    if oldest == "auto":
        oldest = get_slack_last_ts(channel_id)

    messages = fetch_channel_messages(client, channel_id, oldest=oldest)
    if not messages:
        return stats

    latest_ts = oldest  # 이번 배치에서 가장 최신 ts 추적

    for msg in messages:
        text = msg.get("text", "") or ""

        # 워크플로우 메시지가 아니면 무시 (조건 4: 일반 메시지 무시)
        if not is_workflow_message(text):
            stats["skipped"] += 1
            continue

        ts = msg["ts"]
        if ts > latest_ts:
            latest_ts = ts

        # Unix timestamp → 날짜 문자열
        recv_date = datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")

        # 파싱
        parsed = parse_workflow_message(text)

        # 이모티콘 확인
        reactions = get_message_reactions(client, channel_id, ts)

        # 완료 여부 (조건 2, 3)
        completed = check_completed(text, reactions)
        status = "완료" if completed else "진행 중"

        # 팩토리 / 설비 매칭 여부 (조건 6)
        fac_matched = match_factory(parsed.get("factory"))
        eq_matched = match_equipment(parsed.get("equipment"))
        is_matched = fac_matched and eq_matched

        # DB 저장 (raw_text 없음 — 저장 공간 절약)
        req_id = upsert_slack_request({
            "channel_id": channel_id,
            "channel_name": channel_name,
            "message_ts": ts,
            "factory": parsed.get("factory"),
            "equipment": parsed.get("equipment"),
            "symptom": parsed.get("symptom"),
            "inspection": parsed.get("inspection"),
            "assignee": parsed.get("assignee"),
            "status": status,
            "is_matched": is_matched,
            "recv_date": recv_date,
        })

        # 미매칭 저장 (조건 6)
        if not is_matched and req_id:
            save_slack_unmatched(
                slack_request_id=req_id,
                factory_raw=parsed.get("factory") or "",
                equipment_raw=parsed.get("equipment") or "",
                channel_name=channel_name,
                recv_date=recv_date,
            )
            stats["unmatched"] += 1

        stats["processed"] += 1

    # 다음 동기화 시 증분 시작점으로 사용하도록 최신 ts 저장
    if latest_ts and latest_ts != "0" and latest_ts != oldest:
        save_slack_last_ts(channel_id, channel_name, latest_ts)

    return stats


def run_full_sync(bot_token: str, oldest: str = "auto") -> dict:
    """
    모든 보전요청 채널을 동기화합니다.
    oldest='auto': 채널별 마지막 ts 이후만 가져옴 (증분, 기본값)
    oldest='0'   : 전체 재수집
    반환: {channel_name: stats, ...}
    """
    client = WebClient(token=bot_token)
    channels = get_maintenance_channels(client)
    results = {}
    for ch in channels:
        try:
            stats = sync_channel(client, ch["id"], ch["name"], oldest=oldest)
        except Exception as e:
            stats = {"error": str(e)}
        results[ch["name"]] = stats
    return results
