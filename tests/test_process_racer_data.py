"""単体テスト: process_racer_data.py（UT-001〜UT-011）"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from layout import MIN_RECORD_LENGTH
from process_racer_data import (
    convert_birthdate,
    convert_yyyymmdd,
    extract_field,
    save_csv,
)


# ── UT-001〜004: convert_birthdate ──────────────────────────────────────────

def test_convert_birthdate_heisei():
    """UT-001: 平成（H）の日付変換"""
    assert convert_birthdate("H310101") == "2019-01-01"


def test_convert_birthdate_showa():
    """UT-002: 昭和（S）の日付変換"""
    assert convert_birthdate("S441111") == "1969-11-11"


def test_convert_birthdate_reiwa():
    """UT-003: 令和（R）の日付変換"""
    assert convert_birthdate("R060501") == "2024-05-01"


def test_convert_birthdate_invalid():
    """UT-004: 未定義の元号コードは ValueError"""
    with pytest.raises(ValueError):
        convert_birthdate("X000101")


# ── UT-005〜007: extract_field ───────────────────────────────────────────────

def _make_line(content: bytes, total_length: int = MIN_RECORD_LENGTH) -> bytes:
    """指定バイト列を先頭に配置し、残りをスペースで埋めた行を作る。"""
    padded = content + b' ' * (total_length - len(content))
    return padded[:total_length]


def test_extract_field_integer():
    """UT-005: 4バイト整数フィールドの抽出"""
    line = _make_line(b'1234')
    result = extract_field(line, 0, 4, 'int')
    assert result == 1234


def test_extract_field_string_sjis():
    """UT-006: Shift-JIS 文字列フィールドの抽出（文字化けなし）"""
    sjis_str = 'テスト'.encode('cp932')
    padded = sjis_str + b' ' * (15 - len(sjis_str))
    line = b' ' * 20 + padded + b' ' * (MIN_RECORD_LENGTH - 20 - 15)
    result = extract_field(line, 20, 15, 'str')
    assert result == 'テスト'


def test_extract_field_short_line():
    """UT-007: 行が短すぎる場合は IndexError"""
    line = b'abc'
    with pytest.raises(IndexError):
        extract_field(line, 0, 20, 'str')


# ── UT-008〜011: save_csv ────────────────────────────────────────────────────

def test_csv_utf8_bom(tmp_path):
    """UT-008: CSV先頭にUTF-8 BOMが付与されること"""
    df = pd.DataFrame({'a': [1], 'b': ['テスト']})
    filepath = str(tmp_path / "test.csv")
    save_csv(df, filepath)
    with open(filepath, 'rb') as f:
        raw = f.read()
    assert raw[:3] == b'\xef\xbb\xbf', "UTF-8 BOM が先頭に存在しない"


def test_csv_crlf(tmp_path):
    """UT-009: CSV の改行コードが CRLF であること"""
    df = pd.DataFrame({'a': [1, 2]})
    filepath = str(tmp_path / "test.csv")
    save_csv(df, filepath)
    with open(filepath, 'rb') as f:
        raw = f.read()
    assert b'\r\n' in raw, "CRLF 改行が含まれていない"


def test_csv_header(tmp_path):
    """UT-010: CSV 1行目にフィールド名が出力されること"""
    df = pd.DataFrame({'racer_id': [1], 'year': [2024]})
    filepath = str(tmp_path / "test.csv")
    save_csv(df, filepath)
    with open(filepath, encoding='utf-8-sig') as f:
        first_line = f.readline().rstrip('\r\n')
    assert first_line == 'racer_id,year'


def test_csv_missing_values(tmp_path):
    """UT-011: 欠損値（NaN/None）が空文字列として出力されること"""
    df = pd.DataFrame({'a': [1, np.nan], 'b': [None, 'x']})
    filepath = str(tmp_path / "test.csv")
    save_csv(df, filepath)
    with open(filepath, encoding='utf-8-sig') as f:
        content = f.read()
    assert 'nan' not in content.lower(), "欠損値が 'nan' として出力されている"
