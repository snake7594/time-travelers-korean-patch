# 타임 트래블러즈 한글 패치 (PSP / NPJH50597)

레벨파이브 『타임 트래블러즈(TIME TRAVELERS)』 PSP판의 비공식 한국어 번역 패치입니다.

배포물은 **xdelta 바이너리 패치 한 개**입니다. 게임 데이터는 일절 포함하지 않으며,
적용하려면 본인이 소유한 정품 UMD에서 직접 만든 ISO가 필요합니다.

---

## 1. 준비물

| 항목 | 내용 |
|---|---|
| 원본 ISO | `Time Travelers.iso` — 아래 해시와 **정확히 일치**해야 합니다 |
| 패치 파일 | `Time Travelers (KR).xdelta` (릴리스에서 내려받기) |
| 적용 도구 | [xdelta3](https://github.com/jmacd/xdelta-gpl/releases) 또는 xdeltaUI |

### 원본 ISO 해시 (반드시 확인)

```
파일명 : Time Travelers.iso
크기   : 1,176,698,880 바이트
MD5    : ff66a1628385c829812983d319c5c92b
SHA-1  : e8b6a6fdab73b50948c57818b127cb9b36b87caa
```

해시가 다르면 패치가 적용되지 않거나, 적용되더라도 게임이 정상 동작하지 않습니다.
재압축(CSO/ZSO)하거나 다른 툴로 리마스터한 ISO는 사용할 수 없습니다.

**해시 확인 방법**

Windows PowerShell:
```powershell
Get-FileHash "Time Travelers.iso" -Algorithm MD5
```

macOS / Linux:
```bash
md5sum "Time Travelers.iso"
```

### 패치 적용 후 결과물 해시

```
파일명 : Time Travelers (KR).iso
크기   : 1,176,698,880 바이트
MD5    : 49ebf5a7a7392cdec83063c564e50046
SHA-1  : f98dce608c99567382aec194d82239a50154a16f
```

이 값과 일치하면 정상적으로 적용된 것입니다.

---

## 2. 패치 방법

### 방법 A — 명령줄 (권장)

원본 ISO와 `.xdelta` 파일을 같은 폴더에 두고:

```bash
xdelta3 -d -f -s "Time Travelers.iso" "Time Travelers (KR).xdelta" "Time Travelers (KR).iso"
```

* `-d` 디코드(적용) · `-f` 출력 파일 덮어쓰기 허용 · `-s` 원본(소스) 지정
* 1분 이내에 끝납니다.
* 파일명에 공백이 있으므로 **따옴표를 반드시** 넣으세요.

Windows에서 `xdelta3.exe` 대신 `xdelta.exe`로 배포된 빌드를 쓴다면 명령 이름만 바꾸면 됩니다.

### 방법 B — xdeltaUI (그래픽)

1. `xdeltaUI.exe` 실행 → **Apply Patch** 탭
2. **Patch** — 내려받은 `Time Travelers (KR).xdelta`
3. **Source File** — 원본 `Time Travelers.iso`
4. **Output File** — 만들 파일 이름 (예: `Time Travelers (KR).iso`)
5. **Apply** 클릭

### 적용 후

위의 결과물 해시를 확인한 뒤, 평소 쓰시는 방법대로 실행하세요.

* **PPSSPP** — ISO를 그대로 열면 됩니다.
* **실기 PSP / PS Vita(Adrenaline)** — ISO를 `ms0:/ISO/` (Vita는 `ux0:/pspemu/ISO/`)에 넣습니다.

---

## 3. 번역 범위

| 대상 | 분량 |
|---|---|
| 본편 대사 | 8,691줄 |
| 선택지 | 325개 |
| TIPS · 튜토리얼 · 도움말 · 줄거리 | 1,460개 문자열 / 997개 파일 |
| 타임 트래블 차트 | 391개 |
| 메뉴·시스템 메시지 (Lua) | 129개 |
| 실행 파일 내 메시지 (EBOOT) | 52개 |
| 메뉴 이미지 라벨 (버튼·제목 등) | 158개 |
| 동영상 자막 | 5개 영상 |

한글 글꼴은 게임 폰트 아틀라스를 다시 그려 넣었습니다. 대사·TIPS용 폰트는 14×14 픽셀로
원본보다 크게 키웠고, 문장부호는 전각으로 통일했습니다.

---

## 4. 알려진 제한

* 동영상 자막은 **화면 상단**에 표시되며, 영상에 원래 새겨진 일본어 자막은 그대로 남습니다.
  일본어를 지우려면 자막 구간의 화면 아래쪽을 통째로 다시 그려야 하는데, 그러면 해당
  프레임의 부호화 비용이 급증해 재생이 끊깁니다(자세한 이유는 `docs/TECHNICAL.md`).
* `avant_title.pmf`(아방 타이틀, 8분 20초)의 자막 대사는 일부만 번역돼 있습니다.
  자막 구간 추출은 완료됐고(`tools/cues/`), 원문 판독·번역이 진행 중입니다.
* 오프닝 무비 자막의 표시 구간이 원본과 어긋나는 경우가 있습니다.

---

## 5. 직접 빌드하기

패치를 직접 만들고 싶거나 번역을 수정하고 싶다면.

### 필요한 것

* Python 3.11 이상
* `pip install numpy opencv-python pillow imageio-ffmpeg`
* 원본 `Time Travelers.iso` (위 해시와 일치)
* 한글 글꼴 — [나눔스퀘어 네오](https://hangeul.naver.com/font) `NanumSquareNeo-cBd.ttf`

### 경로 설정

`tools/pack_korean.py` 상단의 상수를 자기 환경에 맞게 고칩니다.

```python
SRC       = r'...\Time Travelers.iso'          # 원본
DST       = r'...\Time Travelers (KR).iso'     # 출력
JSON_DIR  = r'...\translation\script_fix'      # 대사 번역
UI_DIR    = r'...\translation\ui_json'         # UI 번역
GLYPH_MAP = r'...\translation\_glyph_map.json' # 글자 배정표
TTF       = r'...\NanumSquareNeo-cBd.ttf'      # 한글 글꼴
MOVIE_DIR = r'...\movie'                       # 자막 입힌 .pmf
```

### 빌드

```bash
python tools/op_build.py      # 동영상 자막 (선택, 오래 걸림)
python tools/pack_korean.py   # 본 빌드
python tools/verify_all.py    # 검증 — 누락 글리프 0 이어야 정상
```

`op_build.py`는 원본 ISO에서 영상을 꺼내 자막을 얹고 다시 인코딩합니다.
`avant_title.pmf`는 14,916프레임이라 디코딩에 6 GB 정도의 디스크를 씁니다.

### xdelta 만들기

```bash
xdelta3 -e -1 -f -s "Time Travelers.iso" "Time Travelers (KR).iso" "Time Travelers (KR).xdelta"
```

---

## 6. 저장소 구성

```
tools/          빌드·추출·검증 도구 (Python)
  pack_korean.py    본 빌더 — 텍스트·폰트·메뉴 이미지·동영상을 ISO에 반영
  op_build.py       동영상 자막 빌드
  op_mux.py         PSMF 다중화 — 실기 재생의 핵심
  op_render.py      자막 그리기
  op_subs.py        자막 대사표
  op_band.py        영상에서 자막 구간 추출
  cfgbin.py         Level-5 .cfg.bin 읽기/쓰기
  menu_tex.py       메뉴 이미지 라벨 다시 그리기
  verify_all.py     전체 검증
  cues/             영상별 자막 구간표 (JSON)
translation/    번역 데이터 (JSON)
docs/           기술 문서
```

게임에서 추출한 데이터(폰트 아틀라스, 영상, 스크립트 바이너리)는 포함하지 않습니다.
모두 원본 ISO에서 도구가 직접 뽑아냅니다.

---

## 7. 법적 고지

* 이 저장소는 번역 데이터와 도구만 배포합니다. 게임 데이터는 포함하지 않습니다.
* 패치를 적용하려면 **정품을 소유**하고 본인이 직접 덤프한 ISO가 있어야 합니다.
* 『TIME TRAVELERS』의 모든 권리는 LEVEL-5 Inc. 에 있습니다.
* 비영리 팬 번역이며, 판매·재배포로 이익을 취하지 마세요.
