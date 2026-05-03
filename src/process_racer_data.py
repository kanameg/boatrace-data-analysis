#!/usr/bin/env python3
"""ボートレーサーデータ抽出・整形・保存スクリプト

使用方法:
  python src/process_racer_data.py <input_file> <year> <term> <output_dir>

終了コード:
  0: 正常終了
  4: データ処理エラー
"""

import logging
import os
import sys
from datetime import datetime

import pandas as pd

from layout import (
    COURSE_A_BLOCK_SIZE,
    COURSE_A_LAYOUT,
    COURSE_A_START_OFFSET,
    COURSE_B_BLOCK_SIZE,
    COURSE_B_LAYOUT,
    COURSE_B_START_OFFSET,
    COURSE_COUNT,
    MIN_RECORD_LENGTH,
    NO_COURSE_LAYOUT,
    PERSONAL_LAYOUT,
    TERM_LAYOUT,
)

EXIT_CODE_OK = 0
EXIT_CODE_ERROR = 4

ERA_MAP = {'S': 1925, 'H': 1988, 'R': 2018}

# racer_info.csv の列順（SRS 7.2）
RACER_INFO_COLUMNS = [
    'racer_id', 'year', 'period',
    'name', 'name_kana', 'branch', 'birthplace', 'birthdate',
    'gender', 'age', 'height', 'weight', 'blood_type',
    'training_term', 'grade', 'prev_grade', 'prev2_grade', 'prev3_grade',
    'current_ability_index', 'prev_ability_index',
    'calc_period_from', 'calc_period_to',
]

# racer_results.csv の列順（SRS 7.3）
_COURSE_A_SUFFIXES = [f[0] for f in COURSE_A_LAYOUT]
_COURSE_B_SUFFIXES = [f[0] for f in COURSE_B_LAYOUT]
_ALL_COURSE_SUFFIXES = _COURSE_A_SUFFIXES + _COURSE_B_SUFFIXES

_RACER_RESULTS_BASE_COLUMNS = [
    'racer_id', 'year', 'period',
    'race_count', 'first_count', 'second_count',
    'finalist_count', 'championship_count',
    'win_rate', 'place_rate', 'avg_start_time',
]
RACER_RESULTS_COLUMNS = (
    _RACER_RESULTS_BASE_COLUMNS
    + [f'course_{n}_{s}' for n in range(1, COURSE_COUNT + 1) for s in _ALL_COURSE_SUFFIXES]
    + [f[0] for f in NO_COURSE_LAYOUT]
)


def setup_logging(log_path: str) -> logging.Logger:
    """ファイルと標準エラー出力の両方にログを出力するロガーを設定する。"""
    os.makedirs(os.path.dirname(log_path) if os.path.dirname(log_path) else '.', exist_ok=True)
    logger = logging.getLogger('process_racer_data')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    file_handler = logging.FileHandler(log_path, encoding='utf-8', mode='a')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.INFO)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stderr_handler)
    return logger


def convert_birthdate(raw_str: str) -> str:
    """年号+YYMMDD形式の文字列をYYYY-MM-DD形式に変換する。

    例: 'H310101' → '2019-01-01', 'S441111' → '1969-11-11'
    """
    if not raw_str or len(raw_str) < 7:
        raise ValueError(f"不正な生年月日フォーマット: {raw_str!r}")
    era_code = raw_str[0].upper()
    if era_code not in ERA_MAP:
        raise ValueError(f"未定義の元号コード: {era_code!r}")
    yy = int(raw_str[1:3])
    mm = raw_str[3:5]
    dd = raw_str[5:7]
    year = ERA_MAP[era_code] + yy
    return f'{year:04d}-{mm}-{dd}'


def convert_yyyymmdd(raw_str: str) -> str | None:
    """YYYYMMDD形式の文字列をYYYY-MM-DD形式に変換する。空白は None を返す。"""
    stripped = raw_str.strip()
    if not stripped:
        return None
    if len(stripped) != 8:
        raise ValueError(f"不正なYYYYMMDDフォーマット: {raw_str!r}")
    return f'{stripped[:4]}-{stripped[4:6]}-{stripped[6:8]}'


def extract_field(line: bytes, offset: int, length: int, field_type: str) -> int | float | str | None:
    """固定バイト長のフィールドを抽出して型変換する。

    line が短すぎる場合は IndexError を発生させる。
    空白のみのフィールドは None を返す。
    """
    if offset + length > len(line):
        raise IndexError(
            f"行が短すぎます: offset={offset}, length={length}, line_length={len(line)}"
        )
    raw_bytes = line[offset:offset + length]
    decoded = raw_bytes.decode('cp932', errors='replace').strip()
    if not decoded:
        return None
    if field_type == 'int':
        return int(decoded)
    if field_type == 'float':
        return float(decoded)
    if field_type == 'str':
        return decoded
    if field_type == 'birthdate':
        return convert_birthdate(decoded)
    if field_type == 'yyyymmdd':
        return convert_yyyymmdd(decoded)
    raise ValueError(f"未知のフィールドタイプ: {field_type!r}")


def _extract(line: bytes, offset: int, length: int, field_type: str, divisor) -> int | float | str | None:
    """extract_field に除数適用を加えたラッパー。"""
    val = extract_field(line, offset, length, field_type)
    if val is not None and divisor is not None:
        return val / divisor
    return val


def parse_record(line: bytes) -> tuple[dict, dict] | None:
    """1行のバイト列からレーサー情報と成績情報を抽出する。

    MIN_RECORD_LENGTH 未満の行はヘッダ/フッタとみなし None を返す。
    フィールド単位のパースエラーは None を格納してスキップする。
    """
    if len(line) < MIN_RECORD_LENGTH:
        return None

    logger = logging.getLogger('process_racer_data')
    info: dict = {}
    results: dict = {}

    # 個人属性
    for field_name, offset, length, field_type, divisor in PERSONAL_LAYOUT:
        try:
            val = _extract(line, offset, length, field_type, divisor)
        except (ValueError, IndexError) as e:
            logger.debug(f"フィールド抽出エラー [{field_name}]: {e}")
            val = None
        if field_name in (
            'win_rate', 'place_rate', 'first_count', 'second_count',
            'race_count', 'finalist_count', 'championship_count', 'avg_start_time',
        ):
            results[field_name] = val
        else:
            info[field_name] = val

    # コースA集計（entry_count, place_rate, avg_start_time, avg_start_order）
    for course_num in range(1, COURSE_COUNT + 1):
        base = COURSE_A_START_OFFSET + (course_num - 1) * COURSE_A_BLOCK_SIZE
        for suffix, rel_offset, length, field_type, divisor in COURSE_A_LAYOUT:
            col = f'course_{course_num}_{suffix}'
            try:
                val = _extract(line, base + rel_offset, length, field_type, divisor)
            except (ValueError, IndexError) as e:
                logger.debug(f"フィールド抽出エラー [{col}]: {e}")
                val = None
            results[col] = val

    # 期別属性
    for field_name, offset, length, field_type, divisor in TERM_LAYOUT:
        try:
            val = _extract(line, offset, length, field_type, divisor)
        except (ValueError, IndexError) as e:
            logger.debug(f"フィールド抽出エラー [{field_name}]: {e}")
            val = None
        if field_name in ('year_in_file', 'period_in_file'):
            continue
        info[field_name] = val

    # コースB明細（1st〜6th, F, L0-L1, K0-K1, S0-S2）
    for course_num in range(1, COURSE_COUNT + 1):
        base = COURSE_B_START_OFFSET + (course_num - 1) * COURSE_B_BLOCK_SIZE
        for suffix, rel_offset, length, field_type, divisor in COURSE_B_LAYOUT:
            col = f'course_{course_num}_{suffix}'
            try:
                val = _extract(line, base + rel_offset, length, field_type, divisor)
            except (ValueError, IndexError) as e:
                logger.debug(f"フィールド抽出エラー [{col}]: {e}")
                val = None
            results[col] = val

    # コースなし脱落
    for field_name, offset, length, field_type, divisor in NO_COURSE_LAYOUT:
        try:
            val = _extract(line, offset, length, field_type, divisor)
        except (ValueError, IndexError) as e:
            logger.debug(f"フィールド抽出エラー [{field_name}]: {e}")
            val = None
        results[field_name] = val

    results['racer_id'] = info.get('racer_id')
    return info, results


def build_dataframes(
    records: list[tuple[dict, dict]],
    year: int,
    term: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """パース済みレコードリストから2つのDataFrameを構築する。"""
    info_rows = []
    results_rows = []
    for info, results in records:
        info['year'] = year
        info['period'] = term
        results['year'] = year
        results['period'] = term
        info_rows.append(info)
        results_rows.append(results)

    info_df = pd.DataFrame(info_rows, columns=RACER_INFO_COLUMNS)
    results_df = pd.DataFrame(results_rows, columns=RACER_RESULTS_COLUMNS)
    return info_df, results_df


def save_csv(df: pd.DataFrame, filepath: str) -> None:
    """DataFrameをUTF-8 BOM付き、CRLF改行のCSVとして保存する。"""
    dir_path = os.path.dirname(filepath)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    df.to_csv(
        filepath,
        index=False,
        encoding='utf-8-sig',
        lineterminator='\r\n',
        na_rep='',
    )


def main(input_file: str, year: int, term: int, output_dir: str) -> None:
    """メイン処理。"""
    log_path = os.environ.get('COLLECT_LOG_PATH')
    if not log_path:
        os.makedirs('logs', exist_ok=True)
        log_path = f'logs/collect_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    logger = setup_logging(log_path)

    try:
        logger.info(
            f"データ処理開始: input_file={input_file}, year={year}, term={term}, output_dir={output_dir}"
        )

        with open(input_file, 'rb') as f:
            raw = f.read()

        lines = [line.rstrip(b'\r') for line in raw.split(b'\n')]

        records = []
        skip_count = 0
        error_count = 0

        for line_num, line in enumerate(lines, start=1):
            if len(line) < MIN_RECORD_LENGTH:
                skip_count += 1
                continue
            try:
                result = parse_record(line)
                if result is None:
                    skip_count += 1
                    continue
                records.append(result)
            except Exception as e:
                error_count += 1
                logger.error(f"行 {line_num} のパース失敗（スキップ）: {e}")

        logger.info(f"有効レコード数: {len(records)}, スキップ行数: {skip_count}, エラー行数: {error_count}")

        if not records:
            logger.error("有効なレコードが1件も見つかりませんでした")
            sys.exit(EXIT_CODE_ERROR)

        info_df, results_df = build_dataframes(records, year, term)

        info_path = os.path.join(output_dir, 'racer_info.csv')
        results_path = os.path.join(output_dir, 'racer_results.csv')

        logger.info(f"選手情報CSV保存: {info_path}")
        save_csv(info_df, info_path)

        logger.info(f"成績情報CSV保存: {results_path}")
        save_csv(results_df, results_path)

        logger.info("データ処理完了")

    except Exception as e:
        logger.error(f"データ処理エラー: {e}", exc_info=True)
        sys.exit(EXIT_CODE_ERROR)


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print(
            f"使用方法: python {sys.argv[0]} <input_file> <year> <term> <output_dir>",
            file=sys.stderr,
        )
        sys.exit(EXIT_CODE_ERROR)
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
