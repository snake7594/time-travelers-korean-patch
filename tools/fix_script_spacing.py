"""Repair Korean spacing and source-aligned hard breaks in script_fix JSON.

This is intentionally a whitespace-only pass.  It preserves ids, ja, tags,
and the existing wording.  Kiwi is used as a local Korean spacing adviser;
only high-confidence space insertions are accepted, never word replacements
or deletions.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from kiwipiepy import Kiwi


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "script_fix"
REFERENCE = ROOT / "script_json"
MARK = "\\n"
TOKEN_RE = re.compile(r"(\\n|<[^>]*>)")
TIP_OPEN_RE = re.compile(r"<TIP\d+>")
TIP_CLOSE = "</TIP>"
HANGUL_MIN = 0xAC00
HANGUL_MAX = 0xD7A3


# Terms and names which must not be split by a general-purpose spacer.  The
# unflagged corpus below supplies most of the list; these are the domain and
# name compounds that occur rarely or only in flagged entries.
MANUAL_PROTECTED = {
    "그거",
    "그때그때",
    "그다음",
    "고중력장",
    "다세계",
    "중력장",
    "배전",
    "번치",
    "쌍소멸",
    "연쇄쌍소멸",
    "지수함수적",
    "아인슈타인",
    "전일본전력",
    "비디오테이프",
    "시간여행",
    "타임머신",
    "타임라인",
    "선진파",
    "자력선",
    "연예기획사",
    "여자아이",
    "여자애",
    "고등학생",
    "그만두다",
    "잃어버리다",
    "여러모로",
    "차례차례",
    "아무래도",
    "달각달각",
    "덜컹덜컹",
    "카타카타",
    "엔조",
    "이토야마",
    "하야미",
    "미코토",
    "히나",
    "신도",
    "유리카",
    "쿠라모토",
    "타다노",
    "타카이도",
    "사와키",
    "슌스케",
    "카이",
    "아키라",
    "나파",
    "루상치",
    "치짱",
    "요타",
    "하루미",
    "시라토",
    "카미야",
    "메자키",
    "후시미",
    "후카세",
    "시노하라",
    "이자와",
    "오캰",
    "여학원",
    "모멘트",
    "보도부",
    "제작부",
    "정보통",
    "신주쿠역",
    "통산성",
    "사무차관",
    "복수범",
    "라던데",
    "잃어버려",
    "잃어버려요",
}


# A few compounds are commonly spaced in general Korean text but are kept as
# one lexical item in this script's established terminology.
MANUAL_PROTECTED.update(
    {
        "고중력장",
        "소립자",
        "중성자",
        "반입자",
        "실린더",
        "연구소",
        "방송국",
        "비디오덱",
        "카메라맨",
        "뉴스캐스터",
        "아인슈타인",
        "전일본전력",
        # Terms which Kiwi tends to over-split in TIP explanations or
        # compact established wording.
        "경제통산성",
        "경제통산대신",
        "경제산업정책국",
        "크래킹",
        "쇼트케이크",
        "잘하",
        "클리어런스",
        "숄더",
        "출동반",
        "시부야역",
        "경부보",
        "경범죄처벌법",
        "중의원",
        "예산위원회",
        "전대물",
        "브레이크댄스",
        "아마돈",
        "야한",
        "유리빛",
        "프로급",
        "지정용품",
        "복숭아반",
        "학급위원",
        "무지개빛",
        "홍백",
        "인승",
        "양자역학",
        "마루보",
        "무승부여도",
        "와이드쇼",
        "퇴직서",
        "뒷사정",
        "한국말",
        "단것",
        "학생회장",
        "넘쳐나다",
        "간사이",
        "한눈팔다",
        "감시실",
        "말씀드리다",
        "머지않아",
        "수십",
        "끝내다",
        "강운",
        "저세상",
        "그만둬",
        "구속구",
        "러브맥스",
        "씨이",
        "충격받다",
        "않습니꺼",
        "않습니더",
        "습니꺼",
        "입니더",
        "사쿠라반",
        "매실반",
        "매그넘",
        "지원처",
        "악수회",
        "후하하하",
        "크헉",
        "화아아아아",
        "사부니임",
        "하루히사",
        "잖으냐",
        "넘길게",
        "발밑",
        "경계받다",
        "비웃음당하다",
        "본게임",
        "큰돈",
        "무능남",
        "신혼여행",
        "섬광탄",
        "눈치채",
        "살아남",
        "따라잡",
        "우선해",
        "전자화폐",
        "비밀번호",
        "밝혀내",
        "따내",
        "잘생겼다",
        "취재차",
        "그만둬어어어",
        "충격받",
        "자경수",
        "자폭단",
        "자찬단",
        "그럴듯",
        "리얼충",
        "슬쩍하다",
        "슬쩍하",
        "무릎차기",
        "거악",
        "경광등",
        "고정쇠",
        "광센서",
        "꼴사납",
        "꾸밈없",
        "내걸",
        "달랍니다",
        "물러터",
        "바보짓",
        "동정받",
        "방해받",
        "보호받",
        "부탁받",
        "구원받",
        "오해받",
        "평가받",
        "칭찬받",
        "수배범",
        "순정가련",
        "미목수려",
        "재색겸비",
        "진검승부",
        "징징대",
        "해내",
        "예금액",
        "초미래",
        "초록불",
        "출혈량",
        "특촬물",
        "밀리리터",
        "바람피우",
        "사이좋",
        "생각나",
        "그만둘",
        "끝내",
        "내걸",
        "넘쳐나",
        "셋입니더",
        "없습니더",
        "얼간아",
        "오래전",
        "경계받",
        "비웃음당",
        "무리입니더",
        "일게요",
        # Inflected forms and compounds which Kiwi otherwise splits after
        # the core term.  These are established names/terms in this script.
        "휴대전화",
        "전화번호",
        "희생양",
        "스카이트리",
        "파티시에",
        "버스데이",
        "취재팀",
        "경제산업대신",
        "경제산업위원장",
        "정무관",
        "그분",
        "생기발랄",
        "눈치챘",
        "치짱이라는",
        "아야링",
        "그다음엔",
        "말했잖나",
        "남자아이",
        "블랙커피",
        "외인부대",
        "있습니더",
        "괴롭힘당",
        "위로받다",
        "상관없다",
        "수제품",
        "우지직",
        "담배꽁초",
        "잖나",
        "상관없는",
        "잘못되다",
        "남자애",
        "등가속도",
        "지급받다",
        "육상자위대",
        "알아보다",
        "오른다잖아",
        "그만하라니까",
        "한자",
        "같이하다",
    }
)


# These are standard spaces the current compact text frequently lost, even
# when pair-level corpus evidence is sparse or ambiguous.
FORCED_SPACED_WORDS = {
    "남자친구": "남자 친구",
    "여자친구": "여자 친구",
    "성장을지켜보는": "성장을 지켜보는",
    "쉬었다가라고": "쉬었다 가라고",
    "건번치": "건 번치",
    "그때문에": "그 때문에",
    "그때마다남겨진": "그때마다 남겨진",
    "고등학생의연애": "고등학생의 연애",
    "시설안에서": "시설 안에서",
    "소중한가족": "소중한 가족",
    "방송해주세요": "방송해 주세요",
    "방송해뒀어야했다는": "방송해 뒀어야 했다는",
    "사와키도카미야": "사와키도 카미야",
    "모습이슈이치로답기도": "모습이 슈이치로답기도",
    "답장이도착했습니다": "답장이 도착했습니다",
    "그래서가져왔습니다": "그래서 가져왔습니다",
    "넘어뜨렸어야했는데": "넘어뜨렸어야 했는데",
    "슈이치로와마사토": "슈이치로와 마사토",
    "본바탕에는다정함": "본바탕에는 다정함",
    "휘둘리기만하는데도": "휘둘리기만 하는데도",
    "쿠라모토는미코토가": "쿠라모토는 미코토가",
    "소녀는사와키에게": "소녀는 사와키에게",
    "전원이도전": "전원이 도전",
    "소멸시키면히나도": "소멸시키면 히나도",
    "여자아나운서": "여자 아나운서",
    "카모시다하루히사": "카모시다 하루히사",
    "할아버지할머니": "할아버지 할머니",
    "타임트래블러즈": "타임 트래블러즈",
    "무슨일": "무슨 일",
    "할타입": "할 타입",
    "노린건이": "노린 건 이",
    "소속카미야": "소속 카미야",
    "평화롭게아미다쿠지로": "평화롭게 아미다쿠지로",
    "시청률이나오지": "시청률이 나오지",
    "소문만들려오는": "소문만 들려오는",
    "설득력이다르다": "설득력이 다르다",
    "최심부에도달할": "최심부에 도달할",
    "아니면이대로가": "아니면 이대로 가",
    "어른으로서해야": "어른으로서 해야",
    "사정이다르다고": "사정이 다르다고",
    "네가가장": "네가 가장",
    "이상황은": "이 상황은",
    "너는다르다": "너는 다르다",
    "걸이야기했다": "걸 이야기했다",
    "중심인물들은": "중심 인물들은",
    "우리방송인이": "우리 방송인이",
    "뉴스터미널로": "뉴스 터미널로",
    "잘못했으면접속": "잘못했으면 접속",
    "순간이가시화된": "순간이 가시화된",
    "그건물에는500명": "그 건물에는 500명",
    "그건물에는": "그 건물에는",
    "따른이유를": "따른 이유를",
    "내가신경": "내가 신경",
    "에너지정책": "에너지 정책",
    "보자달각달각": "보자 달각달각",
    "해야할지": "해야 할지",
    "받아쳐야하지": "받아쳐야 하지",
    "늘어져야해요": "늘어져야 해요",
    "눈치챘기": "눈치챘기",
    "그분을": "그분을",
    "너무나갔어": "너무 나갔어",
    "내 안에서두": "내 안에서 두",
    "전부정학이야": "전부 정학이야",
    "보내져왔어요": "보내져 왔어요",
    "자기의지로": "자기 의지로",
    "로A를": "로 A를",
    "걸포기": "걸 포기",
    "포기하지마": "포기하지 마",
    "실신하지않았습니꺼": "실신하지 않았습니꺼",
    "생각하면불안해서": "생각하면 불안해서",
    "마하군도": "마하 군도",
    "그만해하야미": "그만해 하야미",
    "연구원분이": "연구원 분이",
    "버려저를": "버려 저를",
    "버릴각오": "버릴 각오",
    "디지털화되어있습니더": "디지털화되어 있습니더",
    "것이상의": "것 이상의",
    "미래와는다른": "미래와는 다른",
    "답에도달": "답에 도달",
    "싶을게": "싶을 게",
    "위로 받지": "위로받지",
    "보내버리는": "보내 버리는",
    "함께 하지": "함께하지",
    "세계속에서": "세계 속에서",
    "해야하지": "해야 하지",
    "해야할": "해야 할",
    "오른다 잖아": "오른다잖아",
    "그만 하라니까": "그만하라니까",
    "한 자": "한자",
    "같이 하지": "같이하지",
    "웃는미코토": "웃는 미코토",
    "때의미코토": "때의 미코토",
    "듣기만하는": "듣기만 하는",
    "우지 직": "우지직",
    "해 결된": "해결된",
    "전일본 전력": "전일본전력",
    "타임 라인이": "타임라인이",
    "취재 팀": "취재팀",
    "경제 산업 대신": "경제산업대신",
    "경제 산업 위원장": "경제산업위원장",
    "정 무관": "정무관",
    "그렇잖아": "그렇잖아",
    "네가신경": "네가 신경",
    "탓에저는": "탓에 저는",
    "부디부탁": "부디 부탁",
    "무리입니더": "무리입니더",
    "저희에게는다른": "저희에게는 다른",
    "슌스케씨": "슌스케 씨",
    "할일": "할 일",
    "위해내가": "위해 내가",
    "이기도하고": "이기도 하고",
    "URL보낼": "URL 보낼",
    "테니까읽어": "테니까 읽어",
    "놓인가방": "놓인 가방",
    "가야한다": "가야 한다",
    "반복하리라고생각": "반복하리라고 생각",
    "바쳐서라도도쿄": "바쳐서라도 도쿄",
    "점심도시락": "점심 도시락",
    "마음이가득": "마음이 가득",
    "일이기다리고": "일이 기다리고",
    "치짱에게다른": "치짱에게 다른",
    "카미야에게다가와": "카미야에게 다가와",
    "아니라모두": "아니라 모두",
    "육상자위대의훈련": "육상자위대의 훈련",
    "데 나": "데나",
    "치짱에게가야": "치짱에게 가야",
    "받아야해": "받아야 해",
    "다고나도": "다고 나도",
    "하야미군이": "하야미 군이",
    "혼자가겠습니다": "혼자 가겠습니다",
    "뒤로미룰게": "뒤로 미룰게",
    "가야할지": "가야 할지",
    "담배 꽁초": "담배꽁초",
    "가야해": "가야 해",
    "거짓말 하고": "거짓말하고",
    "망가뜨려가고": "망가뜨려 가고",
    "왜냐하면이": "왜냐하면 이",
    "풀어가면": "풀어 가면",
        "2인승인이상": "2인승인 이상",
        "그러니쿠라모토": "그러니 쿠라모토",
        "알아 볼": "알아볼",
}


def is_hangul(ch: str) -> bool:
    return bool(ch) and HANGUL_MIN <= ord(ch) <= HANGUL_MAX


def hangul_runs(text: str):
    i = 0
    while i < len(text):
        if not is_hangul(text[i]):
            i += 1
            continue
        j = i + 1
        while j < len(text) and is_hangul(text[j]):
            j += 1
        yield i, j, text[i:j]
        i = j


def plain_parts(text: str):
    for part in TOKEN_RE.split(text):
        if not part or TOKEN_RE.fullmatch(part):
            continue
        yield part


def collect_protected(entries, kiwi: Kiwi):
    """Learn stable no-space words from entries without priority flags."""

    freq = Counter()
    for entry in entries:
        if entry.get("flags"):
            continue
        for part in plain_parts(entry["ko"]):
            for _, _, word in hangul_runs(part):
                if 2 <= len(word) <= 12:
                    freq[word] += 1
    protected = set(MANUAL_PROTECTED)
    # Do not learn an entire glued run such as "그런건" as a word merely
    # because it repeats in the compact source.  Only learn repeated runs
    # that Kiwi itself regards as a single lexical item.
    protected.update(
        word
        for word, count in freq.items()
        if count >= 3 and kiwi.space(word) == word
    )
    return protected


def collect_boundary_stats(entries):
    """Count spaces/no-spaces for adjacent Hangul syllables in clean entries."""

    stats = defaultdict(Counter)
    for entry in entries:
        if entry.get("flags"):
            continue
        for part in plain_parts(entry["ko"]):
            for i in range(len(part) - 1):
                if is_hangul(part[i]) and is_hangul(part[i + 1]):
                    stats[part[i : i + 2]]["nospace"] += 1
            for i in range(len(part) - 2):
                if is_hangul(part[i]) and part[i + 1] == " " and is_hangul(part[i + 2]):
                    stats[part[i] + part[i + 2]]["space"] += 1
    return stats


def inside_protected(text: str, index: int, protected: set[str]) -> bool:
    for word in protected:
        start = max(0, index - len(word) + 1)
        end = min(index, len(text))
        pos = text.find(word, start, min(len(text), index + len(word)))
        while pos >= 0:
            if pos < index < pos + len(word):
                return True
            pos = text.find(word, pos + 1, min(len(text), index + len(word)))
    return False


def repeated_unit_split(text: str, index: int) -> bool:
    """Reject Kiwi's occasional split of onomatopoeia/reduplicated words."""

    for size in (2, 3, 4):
        left = text[index - size : index]
        right = text[index : index + size]
        if left and left == right:
            return True
    return False


def boundary_is_high_confidence(text: str, index: int, stats, protected) -> bool:
    if index <= 0 or index >= len(text):
        return False
    left, right = text[index - 1], text[index]
    if not (is_hangul(left) and is_hangul(right)):
        return False
    if inside_protected(text, index, protected) or repeated_unit_split(text, index):
        return False

    pair = text[index - 1 : index + 1]
    count = stats[pair]
    spaces = count["space"]
    nospaces = count["nospace"]
    total = spaces + nospaces

    # A stable no-space pair is almost always a name/compound/ending.
    if nospaces >= 3 and spaces == 0:
        return False
    if total >= 4 and spaces / total < 0.35:
        return False

    # Strong corpus evidence or no contrary evidence: accept Kiwi's insertion.
    if spaces >= 2 and spaces / max(1, total) >= 0.65:
        return True
    if total == 0 or nospaces <= 1:
        return True
    if spaces > nospaces and spaces >= 2:
        return True
    return False


def kiwi_insertions(text: str, kiwi: Kiwi, stats, protected):
    positions = []
    for part in plain_parts_with_offsets(text):
        raw, offset = part
        spaced = kiwi.space(raw)
        matcher = difflib.SequenceMatcher(None, raw, spaced, autojunk=False)
        opcodes = matcher.get_opcodes()
        for op, i1, i2, j1, j2 in opcodes:
            if op != "insert" or spaced[j1:j2].strip():
                continue
            for index in range(i1, max(i2, i1 + 1)):
                absolute = offset + index
                if boundary_is_high_confidence(raw, index, stats, protected):
                    positions.append(absolute)
    return sorted(set(positions))


def plain_parts_with_offsets(text: str):
    cursor = 0
    for part in TOKEN_RE.split(text):
        if not part:
            continue
        if TOKEN_RE.fullmatch(part):
            cursor += len(part)
            continue
        yield part, cursor
        cursor += len(part)


def apply_positions(text: str, positions):
    for index in sorted(set(positions), reverse=True):
        text = text[:index] + " " + text[index:]
    return text


def repair_existing_break_boundaries(text: str):
    """Keep source breaks, but do not leave them inside an obvious word.

    The imported scripts contain several source markers that landed in the
    middle of a Korean inflected form.  Move those markers to the end of the
    form (or, for 어려운, to the actual word boundary) while retaining the
    same marker count.
    """

    # Kiwi may add a normal separator immediately after a source marker when
    # it sees the marker as a token boundary.  Normalize that first so the
    # joined-form repairs below can match the actual syllable sequence.
    text = text.replace(" " + MARK, MARK).replace(MARK + " ", MARK)
    # Use a callable replacement: ``re.sub`` interprets the literal ``\\n``
    # in a replacement string as a real newline, which the game format does
    # not use.
    text = re.sub(
        "제" + re.escape(MARK) + r"거 ?할",
        lambda _match: "제거할" + MARK,
        text,
    )

    joins = {
        "부서" + MARK + "졌어요": "부서졌어요" + MARK,
        "확실" + MARK + "히": "확실히" + MARK,
        "말했" + MARK + "거든": "말했거든" + MARK,
        "제" + MARK + "가": "제가" + MARK,
        "줬다" + MARK + "면서": "줬다면서" + MARK,
        "부끄러워하겠" + MARK + "어": "부끄러워하겠어" + MARK,
        "뜻" + MARK + "이야": "뜻이야" + MARK,
        "끊겼" + MARK + "다": "끊겼다" + MARK,
        "말하" + MARK + "지": "말하지" + MARK,
        "있" + MARK + "고": "있고" + MARK,
        "돈" + MARK + "입니다": "돈입니다" + MARK,
        "끼치겠" + MARK + "지만": "끼치겠지만" + MARK,
        "않" + MARK + "아서": "않아서" + MARK,
        "잡지" + MARK + "를": "잡지를" + MARK,
        "매니저로" + MARK + "서": "매니저로서" + MARK,
        "거슬" + MARK + "러": "거슬러" + MARK,
        "어울리겠" + MARK + "지": "어울리겠지" + MARK,
        "정도" + MARK + "는": "정도는" + MARK,
        "번" + MARK + "이고": "번이고" + MARK,
        "때문이" + MARK + "다": "때문이다" + MARK,
        "습니" + MARK + "다": "습니다" + MARK,
        "않았다" + MARK + "면": "않았다면" + MARK,
        "만신창이잖" + MARK + "아요": "만신창이잖아요" + MARK,
        "훔쳐보겠" + MARK + "지": "훔쳐보겠지" + MARK,
        "않았" + MARK + "어요": "않았어요" + MARK,
        "했" + MARK + "지": "했지" + MARK,
        "타입" + MARK + "이었지": "타입이었지" + MARK,
        "제" + MARK + "거": "제거" + MARK,
        "제거" + MARK + "할": "제거할" + MARK,
        "이해하기어" + MARK + "려운": "이해하기" + MARK + "어려운",
        "타임" + MARK + "라인": "타임라인" + MARK,
        "나이" + MARK + "런": "나" + MARK + "이런",
        "거 슬" + MARK + "러": "거슬러" + MARK,
        "한다" + MARK + "고": "한다고" + MARK,
        "마음" + MARK + "은": "마음은" + MARK,
        "허명" + MARK + "이": "허명이" + MARK,
        "아니" + MARK + "라": "아니라" + MARK,
        "어울리" + MARK + "겠지": "어울리겠지" + MARK,
        "정" + MARK + "도는": "정도는" + MARK,
        "타임라인" + MARK + "으로": "타임라인으로" + MARK,
    }
    for old, new in joins.items():
        text = text.replace(old, new)
    # A marker replaces the surrounding ordinary separator.  It should not
    # strand a space after itself or split off sentence punctuation.
    text = re.sub(
        re.escape(MARK) + r"([。！？?!…,.，、]+)",
        lambda match: match.group(1) + MARK,
        text,
    )
    text = text.replace(" " + MARK, MARK).replace(MARK + " ", MARK)
    text = re.sub(r"(?<=[\uAC00-\uD7A3]) +(?=습니다)", "", text)
    return text


def repair_forced_spaces(text: str):
    for old, new in FORCED_SPACED_WORDS.items():
        text = text.replace(old, new)
    return text


def repair_wrong_spaces(text: str):
    """Remove a small set of unambiguously inserted mid-word spaces.

    ``script_json`` contains a few non-source break markers which were already
    converted to ordinary spaces.  Kiwi can also split dialect endings after
    the general spacing pass.  Only forms with an unambiguous joined spelling
    are handled here; this is deliberately not a general whitespace
    normalizer.
    """

    replacements = {
        "어떠 한": "어떠한",
        "저널리즘 이란": "저널리즘이란",
        "장애 가": "장애가",
        "생겨나 고": "생겨나고",
        "접속 했는데": "접속했는데",
        "있답 니다": "있답니다",
        "받았 습니다": "받았습니다",
        "감속 하여": "감속하여",
        "못 해도": "못해도",
        "경우에 는": "경우에는",
        "</TIP>님 도": "</TIP>님도",
        "지급 받았어요": "지급받았어요",
        "눈치 챘기": "눈치챘기",
        "생각하 지": "생각하지",
        "막을 수": "막을 수",
        "있 습니더": "있습니더",
        "괜찮 습니꺼": "괜찮습니꺼",
        "어땠 습니꺼": "어땠습니꺼",
        "하겠 습니더": "하겠습니더",
        "가겠 습니더": "가겠습니더",
        "있답 니다": "있답니다",
        "에게 다": "에게다",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Dialectal and formal endings are suffixes, including forms whose stem
    # varies before the ending.
    text = re.sub(r"(?<=[\uAC00-\uD7A3]) +(?=(?:습니다|습니꺼|습니더))", "", text)
    return text


def repair_punctuation_spaces(text: str):
    """Restore an ordinary separator after sentence punctuation.

    Skip the deliberately comma-separated stutter forms (그,래,도 and
    similar), which are dialogue styling rather than missing spaces.
    """

    stutter_spans = [
        match.span()
        for match in re.finditer(r"(?:[\uAC00-\uD7A3],){3,}[\uAC00-\uD7A3]", text)
    ]

    def repl(match: re.Match[str]) -> str:
        if any(start < match.start() < end for start, end in stutter_spans):
            return match.group(0)
        return match.group(1) + " " + match.group(2)

    return re.sub(r"([。！？?!,.，、])([\uAC00-\uD7A3])", repl, text)


def collapse_protected_splits(text: str, protected: set[str]):
    """Undo only splits that cut a known lexical/name item in two."""

    # Learned entries are used for candidate filtering.  Collapse only the
    # explicitly curated list so an ordinary phrase is never over-normalized.
    for word in MANUAL_PROTECTED:
        for split in range(1, len(word)):
            text = re.sub(
                r"(?<![\uAC00-\uD7A3])"
                + re.escape(word[:split])
                + r" +"
                + re.escape(word[split:])
                + r"(?![\uAC00-\uD7A3])",
                word,
                text,
            )
    return text


def repair_tip_adjacency(text: str):
    # A TIP body is visible text.  A Korean syllable directly before its
    # opening tag therefore needs the same separator as an ordinary word.
    text = re.sub(r"(?<=[\uAC00-\uD7A3])(?=<TIP\d+>)", " ", text)

    # In these two entries the tag wraps the second half of a lexical
    # compound (이메일, 탈인형), so the visible word must remain joined.
    text = text.replace("이 <TIP445>메일</TIP>", "이<TIP445>메일</TIP>")
    text = text.replace("탈 <TIP343>인형</TIP>", "탈<TIP343>인형</TIP>")

    # After </TIP>, keep particles/endings attached, but separate a following
    # lexical word.  If the attached form is immediately followed by another
    # Hangul syllable, the form must be a multi-syllable grammatical suffix;
    # otherwise it is a missing word boundary.
    attached = (
        "으로부터",
        "에서부터",
        "까지의",
        "까지는",
        "까지도",
        "에게는",
        "에게도",
        "으로는",
        "으로도",
        "로서는",
        "로서",
        "처럼은",
        "이라고",
        "이라는",
        "이란",
        "이라",
        "이다",
        "이라도",
        "이라서",
        "이어서",
        "이었으",
        "였다",
        "이었다",
        "이에요",
        "예요",
        "인가요",
        "이야",
        "이네",
        "이니까",
        "이잖아",
        "이고",
        "이며",
        "지만",
        "라고",
        "라는",
        "라서",
        "라도",
        "라며",
        "라니",
        "로서",
        "에게",
        "으로",
        "에서",
        "까지",
        "부터",
        "처럼",
        "으니",
        "으니까",
        "해도",
        "니까",
        "용",
        "님",
        "였거든",
        "입니다",
        "였으니까",
        "였어요",
        "이어요",
        "이었어요",
        "이었거든",
        "입니까",
        "인데",
        "이면",
        "인",
        "잖아",
        "잖아요",
        "겠지",
        "겠죠",
        "겠어요",
        "겠네",
        "겠군",
        "겠지만",
        "한",
        "해",
        "다오",
    )
    attached_one = {"이", "가", "을", "를", "은", "는", "의", "에", "로", "와", "과", "도", "만", "야", "다", "요", "라", "니", "네", "까"}
    pattern = re.compile(r"</TIP>(?P<tail>[\uAC00-\uD7A3]+)")

    def repl(match: re.Match[str]) -> str:
        tail = match.group("tail")
        # Attach a grammatical suffix to the tagged word, then separate any
        # following lexical material.  The previous implementation treated
        # the whole tail as lexical text (e.g. '</TIP>에위탁'), which put a
        # space before the particle instead of after it.
        for suffix in sorted(attached, key=len, reverse=True):
            if tail.startswith(suffix):
                rest = tail[len(suffix) :]
                return "</TIP>" + suffix + (" " + rest if rest else "")
        if tail[:1] in attached_one:
            rest = tail[1:]
            return "</TIP>" + tail[:1] + (" " + rest if rest else "")
        return "</TIP> " + tail

    return pattern.sub(repl, text)


def strip_ruby_and_tags(text: str) -> str:
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"\[([^/\]]+)/[^\]]+\]", r"\1", text)
    return text


def visible_boundaries(text: str):
    """Return actual string indices at visible-character boundaries."""

    out = []
    i = 0
    while i < len(text):
        if text.startswith(MARK, i):
            i += len(MARK)
            continue
        tag = re.match(r"<[^>]*>", text[i:])
        if tag:
            i += len(tag.group(0))
            continue
        out.append(i)
        i += 1
    out.append(len(text))
    return out


def source_segment_lengths(ja: str):
    return [len(strip_ruby_and_tags(part)) for part in ja.split(MARK)]


def insert_missing_source_breaks(ja: str, ko: str):
    source_lengths = source_segment_lengths(ja)
    target_count = ko.count(MARK)
    required = len(source_lengths) - 1
    if required <= target_count:
        return ko, 0

    target_visible = len(strip_ruby_and_tags(ko.replace(MARK, "")))
    if target_visible <= 1:
        return ko, required - target_count

    # Source breaks are retained in order.  Existing target breaks are left in
    # place; missing ones are placed at the proportional visible position and
    # snapped to the nearest ordinary word boundary.
    source_total = max(1, sum(source_lengths))
    wanted = []
    running = 0
    for length in source_lengths[:-1]:
        running += length
        wanted.append(round(target_visible * running / source_total))

    boundaries = visible_boundaries(ko)
    # A forced break is a layout marker, not part of the visible TIP text.
    # Never manufacture one inside a TIP body while aligning source breaks.
    tip_ranges = [
        (match.start(), match.end())
        for match in re.finditer(r"<TIP\d+>.*?</TIP>", ko, flags=re.DOTALL)
    ]
    existing_visible = []
    visible_index = 0
    i = 0
    while i < len(ko):
        if ko.startswith(MARK, i):
            existing_visible.append(visible_index)
            i += len(MARK)
            continue
        tag = re.match(r"<[^>]*>", ko[i:])
        if tag:
            i += len(tag.group(0))
            continue
        visible_index += 1
        i += 1

    missing = max(0, required - target_count)
    positions = []
    # Existing target markers usually correspond to one of the source
    # markers, even when the translated wording makes their visible offsets
    # differ.  Match them to the nearest source boundary first; otherwise a
    # missing marker at the end can be incorrectly inserted before an
    # already-correct marker near the beginning.
    matched_wanted = set()
    for existing in existing_visible:
        available = [
            (abs(existing - target), index)
            for index, target in enumerate(wanted)
            if index not in matched_wanted
        ]
        if available:
            _, index = min(available)
            matched_wanted.add(index)

    missing_targets = [
        target for index, target in enumerate(wanted) if index not in matched_wanted
    ][:missing]
    occupied = list(existing_visible)
    for target in missing_targets:
        if any(abs(target - x) <= 1 for x in occupied):
            continue
        candidates = []
        for pos in boundaries:
            # Do not split tags or put a break at the very ends.
            if any(start < pos < end for start, end in tip_ranges):
                continue
            before = ko[:pos]
            after = ko[pos:]
            if not before or not after or before.endswith(MARK) or after.startswith(MARK):
                continue
            if before.endswith(" "):
                candidates.append((abs(target - len(strip_ruby_and_tags(before))), pos, True))
            elif after.startswith(" "):
                candidates.append((abs(target - len(strip_ruby_and_tags(before))), pos, True))
            elif before[-1] in "。！？?!…,.、，：:;；" or after[0] in "。！？?!…,.、，：:;；":
                candidates.append((abs(target - len(strip_ruby_and_tags(before))), pos, False))
        if not candidates:
            continue
        _, pos, has_space = min(candidates, key=lambda item: (not item[2], item[0]))
        positions.append((pos, has_space))
        occupied.append(target)

    for pos, has_space in sorted(positions, reverse=True):
        if has_space and ko[pos - 1 : pos + 1] == "  ":
            ko = ko[: pos - 1] + MARK + ko[pos + 1 :]
        elif has_space and ko[pos : pos + 1] == " ":
            ko = ko[:pos] + MARK + ko[pos + 1 :]
        elif has_space and ko[pos - 1 : pos] == " ":
            ko = ko[: pos - 1] + MARK + ko[pos:]
        else:
            ko = ko[:pos] + MARK + ko[pos:]
    return ko, len(positions)


def process_entry(entry, base_by_id, kiwi, stats, protected):
    original = entry["ko"]
    text = original
    flags = set(entry.get("flags", []))
    if "added_break" in flags:
        base = base_by_id.get(entry["id"])
        if base is not None and base.get("ko", "").count(MARK):
            # script_fix was prepared from script_json by removing these
            # non-source breaks without restoring the separator space.
            text = base["ko"].replace(MARK, " ")

    text = text.replace("·", "・").replace("\u200b", "")
    text = repair_forced_spaces(text)
    text = repair_wrong_spaces(text)
    text = repair_punctuation_spaces(text)
    text = repair_tip_adjacency(text)
    text = apply_positions(text, kiwi_insertions(text, kiwi, stats, protected))
    text = repair_wrong_spaces(text)
    text = repair_existing_break_boundaries(text)
    text, inserted_breaks = insert_missing_source_breaks(entry["ja"], text)
    # A newly aligned source marker may replace an existing ordinary space;
    # normalize its immediate surroundings after insertion as well.
    text = repair_existing_break_boundaries(text)
    return text, inserted_breaks


def load_entries(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", data if isinstance(data, list) else [])
    return data, entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write corrected JSON in place")
    parser.add_argument("--examples", type=int, default=40)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    files = sorted(p for p in TARGET.glob("*.json") if p.name != "manifest.json")
    all_entries = []
    docs = {}
    for path in files:
        data, entries = load_entries(path)
        docs[path] = (data, entries)
        all_entries.extend(entries)

    kiwi = Kiwi()
    protected = collect_protected(all_entries, kiwi)
    stats = collect_boundary_stats(all_entries)

    base_by_id = {}
    for path in files:
        ref = REFERENCE / path.name
        if not ref.exists():
            continue
        _, entries = load_entries(ref)
        base_by_id.update({entry["id"]: entry for entry in entries})

    changed = 0
    changed_entries = 0
    added_break_restored = 0
    source_breaks_added = 0
    inserted_spaces = 0
    examples = []
    output = {}

    for path, (data, entries) in docs.items():
        new_entries = []
        for entry in entries:
            before = entry["ko"]
            after, breaks_added = process_entry(entry, base_by_id, kiwi, stats, protected)
            if after != before:
                changed_entries += 1
                inserted_spaces += max(0, after.count(" ") - before.count(" "))
                if len(examples) < args.examples:
                    examples.append((path.name, entry["id"], entry.get("flags", []), before, after))
            if "added_break" in entry.get("flags", []):
                added_break_restored += before != after and entry["id"] in base_by_id
            source_breaks_added += breaks_added
            changed += before != after
            new_entry = dict(entry)
            new_entry["ko"] = after
            new_entries.append(new_entry)
        new_data = dict(data) if isinstance(data, dict) else new_entries
        if isinstance(data, dict):
            new_data["entries"] = new_entries
        output[path] = new_data

    print(f"files={len(files)} entries={len(all_entries)}")
    print(f"changed_entries={changed_entries} inserted_spaces~={inserted_spaces}")
    print(f"added_break_entries_repaired={added_break_restored} source_breaks_added={source_breaks_added}")
    print("examples:")
    for path, entry_id, flags, before, after in examples:
        print(f"\n{path} {entry_id} {flags}\n- {before}\n+ {after}")

    if args.write:
        for path, data in output.items():
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("wrote script_fix JSON files; manifest.json was not touched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
