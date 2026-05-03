# ボートレーサーデータ（fan*.txt）バイトレイアウト定義
#
# 公式サイト（https://www.boatrace.jp/owpc/pc/extra/data/layout.html）の
# フィールド定義を実データ（fan2404.txt）で検証・確定したオフセット。
# 実データでズレが見つかった場合はこのファイルのみ修正すればよい（NF-07）。
#
# レコード構造（0始まりオフセット）:
#   個人属性      0〜 81バイト（計 82バイト）
#   コースA集計  82〜159バイト（13バイト×6コース）
#   期別属性    160〜197バイト（計 38バイト）
#   コースB明細 198〜401バイト（34バイト×6コース）
#   コースなし  402〜409バイト（計  8バイト）
#   出身地      410〜415バイト（計  6バイト、Shift-JIS）
#   MIN_RECORD_LENGTH = 416

# タプル形式: (field_name, offset, length, type_str, divisor)
# type_str : 'int' | 'float' | 'str' | 'birthdate' | 'yyyymmdd'
# divisor  : 数値フィールドの除数（None なら除算なし）
#            整数文字列として格納された小数値を変換するために使用:
#              win_rate ÷100, place_rate ÷10, avg_start_time ÷100,
#              ability_index ÷100, course place_rate ÷10, course avg_* ÷100

PERSONAL_LAYOUT = [
    ('racer_id',            0,   4, 'int',       None),
    ('name',                4,  16, 'str',       None),
    ('name_kana',          20,  15, 'str',       None),
    ('branch',             35,   4, 'str',       None),
    ('grade',              39,   2, 'str',       None),
    ('birthdate',          41,   7, 'birthdate', None),
    ('gender',             48,   1, 'int',       None),
    ('age',                49,   2, 'int',       None),
    ('height',             51,   3, 'int',       None),
    ('weight',             54,   2, 'int',       None),
    ('blood_type',         56,   2, 'str',       None),
    ('win_rate',           58,   4, 'int',       100),
    ('place_rate',         62,   4, 'int',       10),
    ('first_count',        66,   3, 'int',       None),
    ('second_count',       69,   3, 'int',       None),
    ('race_count',         72,   3, 'int',       None),
    ('finalist_count',     75,   2, 'int',       None),
    ('championship_count', 77,   2, 'int',       None),
    ('avg_start_time',     79,   3, 'int',       100),
]

# コースA集計（コースNの絶対オフセット = COURSE_A_START + (N-1) * COURSE_A_BLOCK_SIZE + rel_offset）
# (field_suffix, rel_offset, length, type_str, divisor)
COURSE_A_LAYOUT = [
    ('entry_count',      0,  3, 'int',  None),
    ('place_rate',       3,  4, 'int',  10),
    ('avg_start_time',   7,  3, 'int',  100),
    ('avg_start_order', 10,  3, 'int',  100),
]

TERM_LAYOUT = [
    ('prev_grade',              160,  2, 'str',      None),
    ('prev2_grade',             162,  2, 'str',      None),
    ('prev3_grade',             164,  2, 'str',      None),
    ('prev_ability_index',      166,  4, 'int',      100),
    ('current_ability_index',   170,  4, 'int',      100),
    ('year_in_file',            174,  4, 'int',      None),
    ('period_in_file',          178,  1, 'int',      None),
    ('calc_period_from',        179,  8, 'yyyymmdd', None),
    ('calc_period_to',          187,  8, 'yyyymmdd', None),
    ('training_term',           195,  3, 'int',      None),
    ('birthplace',              410,  6, 'str',      None),  # Shift-JIS、レコード末尾
]

# コースB明細（コースNの絶対オフセット = COURSE_B_START + (N-1) * COURSE_B_BLOCK_SIZE + rel_offset）
# (field_suffix, rel_offset, length, type_str, divisor)
COURSE_B_LAYOUT = [
    ('1st_count',   0,  3, 'int', None),
    ('2nd_count',   3,  3, 'int', None),
    ('3rd_count',   6,  3, 'int', None),
    ('4th_count',   9,  3, 'int', None),
    ('5th_count',  12,  3, 'int', None),
    ('6th_count',  15,  3, 'int', None),
    ('F_count',    18,  2, 'int', None),
    ('L0_count',   20,  2, 'int', None),
    ('L1_count',   22,  2, 'int', None),
    ('K0_count',   24,  2, 'int', None),
    ('K1_count',   26,  2, 'int', None),
    ('S0_count',   28,  2, 'int', None),
    ('S1_count',   30,  2, 'int', None),
    ('S2_count',   32,  2, 'int', None),
]

NO_COURSE_LAYOUT = [
    ('no_course_L0_count', 402, 2, 'int', None),
    ('no_course_L1_count', 404, 2, 'int', None),
    ('no_course_K0_count', 406, 2, 'int', None),
    ('no_course_K1_count', 408, 2, 'int', None),
]

COURSE_COUNT = 6
COURSE_A_BLOCK_SIZE = 13
COURSE_A_START_OFFSET = 82
COURSE_B_BLOCK_SIZE = 34
COURSE_B_START_OFFSET = 198
MIN_RECORD_LENGTH = 416
