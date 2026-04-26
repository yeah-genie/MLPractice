"""
샘플 이용약관 데이터 생성
=========================
실제 이용약관 특성을 반영한 샘플 텍스트를 생성합니다.
(개발/테스트용 — 실제 분석 시 collect.py로 실제 텍스트 수집 필요)

각 앱의 실제 이용약관 특성 (2024년 기준 리서치 기반):
- 쿠팡: 업계 최장 (약 3만자), 법률 용어 밀도 높음
- 카카오: 약 2만자, 세분화된 조항
- 네이버: 약 1.5만자, 격식체
- 인스타그램: 약 1.8만자, 영문 번역체 (어색한 한국어)
- 유튜브: 약 2만자, 영문 번역체
- 틱톡: 약 1.6만자, 번역체
- 배달의민족: 약 1.2만자, 비교적 구어체
- 토스: 약 1만자, 금융 법률 용어 많음
- 당근마켓: 약 8천자, 가장 간결
- 라인: 약 1.4만자, 격식체
"""
from pathlib import Path

RAW_DIR = Path("data/raw/tos_readability")
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 법률 용어 풀
LEGAL = [
    "귀책사유", "손해배상", "불가항력", "준거법", "관할법원",
    "면책", "위탁", "이행", "소송", "중재",
    "명시적", "묵시적", "취소불가", "이하", "제3자",
    "포함하되 이에 한정하지 않는", "기재된 바에 따라",
    "이에 동의하는 것으로 간주", "전항", "본조",
]

# 구어체/친절한 표현
FRIENDLY = [
    "회원님", "알려드립니다", "도움이 필요하시면", "편리하게",
    "쉽게", "간단히", "바로", "쉽고 빠르게",
]

# 앱별 이용약관 특성 파라미터
# (기본 조항 반복수, 법률 용어 빈도, 문장 길이 스타일, 번역체 여부)
APPS = {
    "쿠팡": {
        "size": "large",       # 약 30,000자
        "legal_density": "high",
        "sentence_style": "long",
        "translated": False,
        "description": "전자상거래 플랫폼 특성상 반품/환불/배송 조항이 많고 법률 용어 밀도가 업계 최고 수준",
    },
    "카카오": {
        "size": "large",
        "legal_density": "high",
        "sentence_style": "long",
        "translated": False,
        "description": "메신저·결제·쇼핑 등 다양한 서비스가 통합되어 조항 수가 많고 복잡함",
    },
    "유튜브": {
        "size": "large",
        "legal_density": "medium",
        "sentence_style": "very_long",
        "translated": True,
        "description": "영어 원문을 기계 번역한 흔적이 강해 자연스럽지 않은 문장이 많음",
    },
    "인스타그램": {
        "size": "medium_large",
        "legal_density": "medium",
        "sentence_style": "very_long",
        "translated": True,
        "description": "Meta 계열 약관 특성상 광고/데이터 활용 조항이 길고 번역체",
    },
    "네이버": {
        "size": "medium_large",
        "legal_density": "high",
        "sentence_style": "long",
        "translated": False,
        "description": "포털 서비스 특성상 다양한 부가 서비스 조항이 있고 격식체가 강함",
    },
    "틱톡": {
        "size": "medium",
        "legal_density": "medium",
        "sentence_style": "very_long",
        "translated": True,
        "description": "중국 원문 또는 영어에서 번역, 문장이 길고 어색한 표현 다수",
    },
    "라인": {
        "size": "medium",
        "legal_density": "medium",
        "sentence_style": "long",
        "translated": True,
        "description": "일본 원문 번역체, 격식체와 번역 어투 혼재",
    },
    "배달의민족": {
        "size": "medium_small",
        "legal_density": "low",
        "sentence_style": "medium",
        "translated": False,
        "description": "O2O 플랫폼으로 소비자 친화적 표현 노력, 비교적 읽기 쉬운 편",
    },
    "토스": {
        "size": "small",
        "legal_density": "high",
        "sentence_style": "medium",
        "translated": False,
        "description": "금융 서비스 특성상 법률·금융 용어는 많지만 전체 분량은 짧음",
    },
    "당근마켓": {
        "size": "small",
        "legal_density": "low",
        "sentence_style": "short",
        "translated": False,
        "description": "C2C 중고거래 플랫폼, 간결하고 구어체 친화적",
    },
}

# 샘플 텍스트 조각들
CLAUSES = {
    "header": "이용약관\n\n제1조 (목적)\n본 약관은 {app} 서비스 이용과 관련하여 {app}(이하 '회사')와 이용자 간의 권리·의무 및 책임사항, 기타 필요한 사항을 규정함을 목적으로 합니다.\n\n",
    "long_sentence": "회사는 이용자가 본 약관, 개인정보처리방침, 운영정책(이하 '이용약관 등')을 충분히 이해하고 이에 동의한 후 서비스를 이용하도록 함으로써 이용자의 권익을 보호하고자 하며, 이용자는 본 서비스에 가입하거나 이를 이용함으로써 본 약관에 동의하는 것으로 간주하고, 이에 따라 이용자는 회사가 제공하는 서비스를 이용함에 있어 본 약관 및 관련 법령의 규정을 준수하여야 하고, 이용자가 이를 위반할 경우 귀책사유에 따라 손해배상 책임이 발생할 수 있으며, 이 경우 회사는 면책되지 아니합니다.\n",
    "very_long_sentence": "본 서비스를 이용함으로써 귀하는 (1) 귀하가 서비스 이용 자격이 있는 연령임을 확인하고, (2) 귀하가 개인으로서 서비스를 이용하는 경우 귀하 개인을 대리하여 계약을 체결함을 확인하며, (3) 귀하가 사업체 또는 기타 법인을 대리하여 서비스를 이용하는 경우 해당 법인을 대리하여 계약을 체결할 권한이 있음을 확인하고, (4) 귀하는 본 약관에 대한 귀하의 동의를 통해 회사와 법적 구속력 있는 계약을 체결하며 이에 동의하는 것으로 간주하고, 이를 위반할 경우 관할법원에 소송이 제기될 수 있으며, 준거법은 대한민국 법률로 함을 이해하고 동의합니다.\n",
    "medium_sentence": "서비스 이용 중 발생한 문제는 고객센터를 통해 문의해 주세요. 회사는 이용자의 문의에 성실히 답변할 의무가 있습니다. 이용자는 타인의 개인정보를 무단으로 수집·이용해서는 안 됩니다.\n",
    "short_sentence": "서비스는 무료로 이용할 수 있어요. 문제가 생기면 바로 알려주세요. 회원 탈퇴는 언제든지 가능합니다.\n",
    "legal_dense": "본 약관에서 정하지 아니한 사항과 본 약관의 해석에 관하여는 대한민국의 관련 법령 또는 상관례에 따르며, 귀책사유로 인한 손해배상은 불가항력적 사유를 제외하고 실손 범위 내에서 이루어지며, 제3자에 대한 위탁 관계에서 발생하는 손해에 대해서는 면책 조항이 적용되고, 소송 또는 중재 시 관할법원은 서울중앙지방법원으로 하며 준거법은 대한민국 법으로 합니다. 이에 동의하는 것으로 간주합니다.\n",
    "translation_awkward": "귀하는 당사의 서비스를 이용함으로써 본 약관에 포함하되 이에 한정하지 않는 모든 조건에 동의하는 것으로 간주되며, 당사는 귀하에게 개인적, 비독점적, 양도 불가능한, 취소불가 라이선스를 부여하는 바이며, 기재된 바에 따라 귀하는 서비스를 이용할 수 있는 권리를 갖습니다.\n",
    "article": "제{n}조 ({title})\n",
}

ARTICLE_TITLES = [
    "정의", "서비스의 제공 및 변경", "서비스의 중단", "이용계약의 체결",
    "회원가입", "개인정보의 보호", "이용자의 의무", "회사의 의무",
    "저작권 및 지식재산권", "손해배상", "분쟁 해결", "약관의 개정",
    "서비스 이용 제한", "계약 해지", "면책조항", "준거법 및 재판관할",
    "이용요금", "포인트 및 쿠폰", "환불 정책", "배송 및 반품",
]


def build_text(app: str, params: dict) -> str:
    size          = params["size"]
    legal_density = params["legal_density"]
    sentence_style = params["sentence_style"]
    translated    = params["translated"]

    # 반복 횟수 결정
    size_map = {
        "large":        (25, 18),
        "medium_large": (18, 13),
        "medium":       (12, 9),
        "medium_small": (9,  6),
        "small":        (6,  4),
    }
    article_count, repeat_legal = size_map[size]

    text = CLAUSES["header"].format(app=app)

    for i, title in enumerate(ARTICLE_TITLES[:article_count], start=2):
        text += CLAUSES["article"].format(n=i, title=title)

        # 문장 길이 스타일 적용
        if sentence_style == "very_long":
            text += CLAUSES["very_long_sentence"] * 2
            if translated:
                text += CLAUSES["translation_awkward"]
        elif sentence_style == "long":
            text += CLAUSES["long_sentence"] * 2
        elif sentence_style == "medium":
            text += CLAUSES["medium_sentence"] * 3
        else:  # short
            text += CLAUSES["short_sentence"] * 3

        # 법률 용어 밀도 조정
        if legal_density == "high":
            text += CLAUSES["legal_dense"] * (repeat_legal // article_count + 1)
        elif legal_density == "medium" and i % 2 == 0:
            text += CLAUSES["legal_dense"]

        text += "\n"

    return text


def main():
    print("샘플 이용약관 데이터 생성")
    print("─" * 50)

    for app, params in APPS.items():
        text = build_text(app, params)
        out  = RAW_DIR / f"{app}.txt"
        out.write_text(text, encoding="utf-8")
        chars = len(text.replace(" ", "").replace("\n", ""))
        print(f"  {app:10s}: {chars:>7,}자 — {params['description'][:30]}...")

    print(f"\n저장 완료: {RAW_DIR.resolve()}")
    print("※ 실제 분석 시 collect.py 또는 수동 복사로 실제 텍스트로 교체하세요")


if __name__ == "__main__":
    main()
