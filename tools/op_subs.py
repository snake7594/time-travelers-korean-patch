# -*- coding: utf-8 -*-
"""What the movies say, and where it is written on the picture.

Frames are 29.97 fps and inclusive. Two kinds of cue:

  'black'  the narration cards -- white lettering on a frame that is otherwise
           pure black, set vertically right to left. Korean is written across
           instead, so the card is wiped and the lines are stacked centred.
  'over'   lettering laid over the film. The area is painted out from its own
           surroundings and the Korean goes back on the rows it came from.

`box` is (x0, y0, x1, y1): what gets cleared, and what the lines are centred
in. `rows` on an 'over' cue is the top of each text row the original used.
"""

A01A = [
    dict(a=467, b=551, style='black', box=(0, 40, 480, 224),
         ja='空に穴が開いた日。',
         ko=['하늘에 구멍이 뚫린 날．']),
    dict(a=572, b=686, style='black', box=(0, 40, 480, 224),
         ja='この現象は後に／「ロストホール」と／名付けられる。',
         ko=['이 현상은 훗날',
             '「로스트 홀」이라',
             '이름 붙여진다．']),
    dict(a=707, b=861, style='black', box=(0, 40, 480, 224),
         ja='自然災害、爆発事故、／そしてテロとも／噂されたが、'
            '／原因は今もって／謎とされている。',
         ko=['자연재해, 폭발 사고,',
             '그리고 테러라는',
             '소문도 돌았지만',
             '원인은 지금도',
             '수수께끼로 남아 있다．']),
    dict(a=1043, b=1128, style='over', box=(146, 222, 336, 260), rows=(232,),
         ja='―１８年後―',
         ko=['―１８년 후―']),
]

# The demo film. One line sits on the lower row, two use both; the small rows
# above each are furigana, which Korean does not need and which go with them.
TTP = [
    dict(a=3, b=148, style='over', box=(60, 190, 420, 250), rows=(229,),
         ja='それは、あるSNSの書き込みから始まった。',
         ko=['그것은 어느 SNS의 글에서 시작되었다．']),
    dict(a=212, b=387, style='over', box=(60, 190, 420, 250), rows=(200, 229),
         ja='『空に光が見える』／近くに住む友人が書き込んだものだ。',
         ko=['『하늘에 빛이 보인다』',
             '근처에 사는 친구가 올린 글이었다．']),
    dict(a=694, b=774, style='over', box=(60, 190, 420, 250), rows=(229,),
         ja='ん？', ko=['응？']),
    dict(a=779, b=894, style='over', box=(60, 190, 420, 250), rows=(229,),
         ja='……近い？', ko=['……가깝다？']),
    dict(a=964, b=1077, style='over', box=(60, 190, 420, 250), rows=(229,),
         ja='メモリーカード？　まさか、これが空から？',
         ko=['메모리 카드？　설마 이게 하늘에서？']),
    dict(a=1083, b=1196, style='over', box=(60, 190, 420, 250), rows=(200, 229),
         ja='いや、あんなに光を放って、／バラバラになっていたんだ。',
         ko=['아니, 그렇게 빛을 내뿜으며',
             '산산조각이 나 있었어．']),
    dict(a=1204, b=1316, style='over', box=(60, 190, 420, 250), rows=(200, 229),
         ja='これだけが壊れもせずに、／地上までたどり着けるか？',
         ko=['이것만 부서지지도 않고',
             '지상까지 닿을 수 있을까？']),
    dict(a=1473, b=1586, style='over', box=(60, 190, 420, 250), rows=(200, 229),
         ja='大気圏突入した人工衛星の／パーツなんだろうか？',
         ko=['대기권에 돌입한 인공위성의',
             '부품인 걸까？']),
    dict(a=1593, b=1706, style='over', box=(60, 190, 420, 250), rows=(200, 229),
         ja='……カードの中身を確認するくらい……／いいよな？',
         ko=['……카드 내용을 확인하는 정도는……',
             '괜찮겠지？']),
]

# The card that opens the game, set vertically on black.
A01A_0000 = [
    dict(a=43, b=270, style='black', box=(0, 40, 480, 232),
         ja='ひとが、この世界の、本当の姿を知ったとき、'
            'それは、ひとにとって、幸福なのだろうか？',
         ko=['사람이 이 세계의 진짜 모습을 알았을 때,',
             '그것은 사람에게 행복일까？']),
]

# The chapter seven trailer. Its lettering is larger than the films' and sits
# on its own dark band, two rows of it.
YOKOKU07 = [
    dict(a=20, b=80, style='over', box=(40, 105, 440, 165), rows=(123,), h=21,
         ja='僕はこの子を守らなきゃいけない',
         ko=['나는 이 아이를 지켜야만 해']),
    dict(a=135, b=195, style='over', box=(40, 105, 440, 165), rows=(112, 140),
         h=21, ja='君とは昔からの／知り合いだったような気がする',
         ko=['너와는 오래전부터', '알던 사이였던 기분이 들어']),
    dict(a=250, b=316, style='over', box=(40, 105, 440, 165), rows=(112, 140),
         h=21, ja='もう鉄仮面じゃないぜ／みことのお陰だ',
         ko=['이제 철가면이 아니야', '미코토 덕분이지']),
    dict(a=365, b=425, style='over', box=(40, 105, 440, 165), rows=(112, 140),
         h=21, ja='こんな俺のことを／父親として愛してくれた',
         ko=['이런 나를', '아버지로서 사랑해 줬어']),
    dict(a=479, b=540, style='over', box=(40, 105, 440, 165), rows=(112, 140),
         h=21, ja='あの子を見ていると／なんだか気持ちがかきむしられる',
         ko=['그 아이를 보고 있으면', '어쩐지 마음이 헤집어져']),
    dict(a=600, b=661, style='over', box=(40, 105, 440, 165), rows=(112, 140),
         h=21, ja='お前の顔をずっと見続けていたい／そう思っているんだ',
         ko=['네 얼굴을 계속 보고 싶어', '그렇게 생각하고 있어']),
]


# The avant-title reel: the opening card, the staff credits (already roman, so
# untouched), the laboratory scene the game opens on, and the three narration
# cards it ends with. Dialogue sits on two rows at the foot of the picture with
# furigana above each, all of which is painted out.
DLG = (0, 216, 480, 272)
ROWS = (228, 253)
AVANT = [
    dict(a=43, b=270, style='black', box=(0, 40, 480, 232),
         ja='ひとが、この世界の、本当の姿を知ったとき、'
            'それは、ひとにとって、幸福なのだろうか？不幸なのだろうか？',
         ko=['사람이 이 세계의 진짜 모습을 알았을 때,',
             '그것은 사람에게 행복한 것일까? 불행한 것일까?']),
    dict(a=4458, b=4512, style='over', box=DLG, rows=ROWS,
         ja='予備試験のパンチ注入に対して予測値を超える／エネルギーが発生している',
         ko=['예비 시험 펀치 주입에 대해 예측값을 넘는',
             '에너지가 발생하고 있어']),
    dict(a=4546, b=4582, style='over', box=DLG, rows=ROWS,
         ja='数値から見ても、反粒子の対消滅によるものだ。',
         ko=['수치로 봐도 반입자의 쌍소멸에 의한 거다．']),
    dict(a=4707, b=4751, style='over', box=DLG, rows=ROWS,
         ja='発生原因は不明だ。しかし、反粒子の発生は、／指数関数的に増大している。',
         ko=['발생 원인은 불명이다． 하지만 반입자의 발생은',
             '지수함수적으로 증대하고 있다．']),
    dict(a=4910, b=4938, style='over', box=DLG, rows=ROWS,
         ja='連鎖対消滅が始まれば、その爆発規模は……',
         ko=['연쇄 쌍소멸이 시작되면 그 폭발 규모는……']),
    dict(a=5303, b=5432, style='over', box=DLG, rows=ROWS,
         ja='停止スイッチを押しても、電源管理システムが／反応しない。',
         ko=['정지 스위치를 눌러도 전원 관리 시스템이',
             '반응하지 않아．']),
    dict(a=5515, b=5530, style='over', box=DLG, rows=ROWS,
         ja='時間順序保護仮説……', ko=['시간 순서 보호 가설……']),
    dict(a=5706, b=5802, style='over', box=DLG, rows=ROWS,
         ja='新道さん、何が起こってるんですか？',
         ko=['신도 씨, 무슨 일이 일어나고 있는 건가요？']),
    dict(a=5826, b=5874, style='over', box=DLG, rows=ROWS,
         ja='博士、新道博士。', ko=['박사님, 신도 박사님．']),
    dict(a=6146, b=6158, style='over', box=DLG, rows=ROWS,
         ja='大丈夫。お前の彼氏を信じろ。あいつはアイン／シュタインの後継者と言われる天才だ',
         ko=['괜찮아． 네 남자친구를 믿어． 저 녀석은',
             '아인슈타인의 후계자라 불리는 천재다']),
    dict(a=6372, b=6414, style='over', box=DLG, rows=ROWS,
         ja='緊急強制遮断。', ko=['긴급 강제 차단．']),
    dict(a=6439, b=6469, style='over', box=DLG, rows=ROWS,
         ja='３、２、１。', ko=['３, ２, １．']),
    dict(a=6523, b=6543, style='over', box=DLG, rows=ROWS,
         ja='駿介さん', ko=['슌스케 씨']),
    dict(a=6659, b=6697, style='over', box=DLG, rows=ROWS,
         ja='ここは、いったん逃げた方が良くないか',
         ko=['여긴 일단 피하는 게 낫지 않겠어']),
    dict(a=6860, b=6900, style='over', box=DLG, rows=ROWS,
         ja='そりゃそうだが……。', ko=['그야 그렇지만……．']),
    dict(a=7044, b=7061, style='over', box=DLG, rows=ROWS,
         ja='心配するな、俺が', ko=['걱정 마, 내가']),
    dict(a=7185, b=7290, style='over', box=DLG, rows=ROWS,
         ja='物理的に破壊して強制遮断する。',
         ko=['물리적으로 파괴해서 강제 차단한다．']),
    dict(a=7589, b=7605, style='over', box=DLG, rows=ROWS,
         ja='それに、分解と言っても因果律の外郭に取り',
         ko=['게다가 분해라고 해봤자 인과율의 외곽에 손대는']),
    dict(a=8280, b=8291, style='over', box=DLG, rows=ROWS,
         ja='駿介さん、も', ko=['슌스케 씨, 저']),
    dict(a=8423, b=8435, style='over', box=DLG, rows=ROWS,
         ja='馬鹿な。危険だ', ko=['말도 안 돼． 위험해']),
    dict(a=8955, b=8970, style='over', box=DLG, rows=ROWS,
         ja='駿介さん、も……。', ko=['슌스케 씨, 저……．']),
    dict(a=9088, b=9188, style='over', box=DLG, rows=ROWS,
         ja='じっとしてろ！　今、そっちに行く！',
         ko=['가만히 있어！　지금 그쪽으로 갈게！']),
    dict(a=9316, b=9357, style='over', box=DLG, rows=ROWS,
         ja='大丈夫、私が守ってあげる', ko=['괜찮아, 내가 지켜 줄게']),
    dict(a=10637, b=10656, style='over', box=DLG, rows=ROWS,
         ja='なぜだ！', ko=['어째서냐！']),
    dict(a=11577, b=11596, style='over', box=DLG, rows=ROWS,
         ja='……なんで、こんな無茶を……。',
         ko=['……어째서 이런 무모한 짓을……．']),
    dict(a=11621, b=11667, style='over', box=DLG, rows=ROWS,
         ja='私、信じています', ko=['저, 믿고 있어요']),
    dict(a=11990, b=12020, style='over', box=DLG, rows=ROWS,
         ja='雛ーーっ！！', ko=['히나!!']),
    dict(a=12447, b=12546, style='over', box=DLG, rows=ROWS,
         ja='あいつが犠牲になったのか……。',
         ko=['그 녀석이 희생된 건가……．']),
    dict(a=12573, b=12604, style='over', box=DLG, rows=ROWS,
         ja='……甲妻、すまない。', ko=['……코즈마, 미안하다．']),
    dict(a=12652, b=12669, style='over', box=DLG, rows=ROWS,
         ja='……本当にすまない。', ko=['……정말 미안하다．']),
    dict(a=12985, b=12997, style='over', box=DLG, rows=ROWS,
         ja='……そんな……間に合わなかった……の',
         ko=['……그럴 리가…… 늦어 버린 건가……']),
    dict(a=13522, b=13597, style='black', box=(0, 40, 480, 224),
         ja='空に穴が開いた日。', ko=['하늘에 구멍이 뚫린 날．']),
    dict(a=13627, b=13733, style='black', box=(0, 40, 480, 224),
         ja='この現象は後に／「ロストホール」と／名付けられる。',
         ko=['이 현상은 훗날', '「로스트 홀」이라', '이름 붙여진다．']),
    dict(a=13762, b=13908, style='black', box=(0, 40, 480, 224),
         ja='自然災害、爆発事故、／そしてテロとも／噂されたが、'
            '／原因は今もって／謎とされている。',
         ko=['자연재해, 폭발 사고,', '그리고 테러라는', '소문도 돌았지만',
             '원인은 지금도', '수수께끼로 남아 있다．']),
    dict(a=13986, b=14170, style='over', box=(146, 222, 336, 260), rows=(232,),
         ja='―１８年後―', ko=['―１８년 후―']),
]

MOVIES = {'A01A_0040.pmf': A01A, 'avant_title.pmf': AVANT, 'TTP_Opening.pmf': TTP,
          'A01A_0000_0010.pmf': A01A_0000, 'yokoku_chapter07.pmf': YOKOKU07}

HEIGHT = 14        # cap height the films letter at
LEAD = 25          # baseline to baseline when a cue sets its own lines
PAD = 26           # frames either side, to cover the fade in and out
