# ─── 공통 상수 ───────────────────────────────────────────────
# 이 파일 한 곳만 수정하면 모든 페이지에 반영됩니다.

FACTORIES = ["광명A", "광명B", "광명C", "광명D", "화성A", "화성B", "화성C"]

# 보전내역 관련
MAINTENANCE_STATUS_LIST = ["진행 중", "완료", "팬딩", "고장", "취소"]
SHIFT_LIST              = ["주간", "야간", "상시"]
RECV_TYPE_LIST          = ["생산 설비", "유틸리티", "건물/시설", "기타"]
CONTRACTOR_LIST         = ["자체", "외주"]

# 설비 관련
EQUIPMENT_STATUS_LIST = ["정상", "점검중", "팬딩", "고장", "폐기"]
CATEGORY_LIST = [
    "애벌기", "불림수조", "플라이트", "포장기", "라벨분리기", "라벨부착기",
    "자동애벌기", "자동투입기", "C-Line", "린서", "건조기", "컨베이어",
    "펌프", "판넬", "유틸리티", "기타",
]

# ─── 슬랙 연동 ───
# 메시지 텍스트에 이 단어 중 하나라도 포함되면 완료로 판단
SLACK_COMPLETION_KEYWORDS = ["완료"]

# 이 이모티콘(reaction name)이 달리면 완료로 전환
SLACK_COMPLETION_REACTIONS = {
    "white_check_mark",   # ✅
    "heavy_check_mark",   # ✔️
    "done",
    "완료",               # 커스텀 이모티콘
    "check",
}

# 본문에 이 키워드가 2개 이상 포함되면 워크플로우(보전요청) 메시지로 판단
SLACK_WORKFLOW_KEYWORDS = ["팩토리", "설비명", "증상", "점검"]
