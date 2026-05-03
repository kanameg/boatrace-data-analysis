#!/usr/bin/env bash
# ボートレーサーデータ収集スクリプト
#
# 使用方法:
#   ./collect_racer_data.sh <year> <term>
#
# 引数:
#   year  : 収集対象の西暦年（4桁整数、例: 2025）
#   term  : 収集対象の期（1=前期, 2=後期）
#
# 終了コード:
#   0 : 正常終了
#   1 : 引数エラー
#   2 : ダウンロードエラー
#   3 : 解凍エラー
#   4 : データ処理エラー

set -uo pipefail

# === 定数 ===
readonly BASE_URL="https://www.boatrace.jp/static_extra/pc_static/download/data/kibetsu/"
readonly LHASA_CMD="/usr/bin/lhasa"
readonly RETRY_MAX=3
readonly RETRY_INTERVAL=3

# === ログ設定 ===
mkdir -p logs
DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="logs/collect_${DATETIME}.log"
export COLLECT_LOG_PATH="${LOG_FILE}"
touch "${LOG_FILE}"

log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local entry="[${timestamp}] [${level}] ${message}"
    echo "${entry}" >> "${LOG_FILE}"
    echo "${entry}" >&2
}

# === クリーンアップ ===
FILENAME=""
cleanup() {
    if [ -n "${FILENAME}" ]; then
        local yy="${FILENAME:3:2}"
        local mm="${FILENAME:5:2}"
        rm -f "tmp/${FILENAME}" "tmp/fan${yy}${mm}.txt" 2>/dev/null || true
        log "INFO" "一時ファイルを削除しました"
    fi
}
trap cleanup EXIT

# === 引数チェック（終了コード 1）===
if [ "$#" -ne 2 ]; then
    log "ERROR" "引数の数が不正です。使用方法: $0 <year> <term>"
    exit 1
fi

YEAR="$1"
TERM="$2"

if ! [[ "${YEAR}" =~ ^[0-9]{4}$ ]]; then
    log "ERROR" "年の形式が不正です: ${YEAR} (西暦4桁整数を指定してください)"
    exit 1
fi

if [ "${TERM}" != "1" ] && [ "${TERM}" != "2" ]; then
    log "ERROR" "期の値が不正です: ${TERM} (1=前期 または 2=後期 を指定してください)"
    exit 1
fi

# === 年範囲チェック（終了コード 1）===
CURRENT_YEAR=$(date '+%Y')
if [ "${YEAR}" -lt 1990 ] || [ "${YEAR}" -gt "${CURRENT_YEAR}" ]; then
    log "ERROR" "年の範囲が不正です: ${YEAR} (有効範囲: 1990〜${CURRENT_YEAR})"
    exit 1
fi

# === 未公開期チェック（警告のみ、処理継続）===
CURRENT_MONTH=$(date '+%-m')
if [ "${YEAR}" -eq "${CURRENT_YEAR}" ]; then
    if [ "${TERM}" -eq 1 ] && [ "${CURRENT_MONTH}" -le 10 ]; then
        log "WARNING" "指定した年・期（${YEAR}年前期）のデータはまだ公開されていない可能性があります（終了月: 10月）"
    elif [ "${TERM}" -eq 2 ] && [ "${CURRENT_MONTH}" -le 4 ]; then
        log "WARNING" "指定した年・期（${YEAR}年後期）のデータはまだ公開されていない可能性があります（終了月: 翌年4月）"
    fi
fi
# 前年後期で翌年4月が未来の場合（例: 現在2025年2月で2024年後期を指定）
PREV_YEAR=$((YEAR - 1))
if [ "${TERM}" -eq 2 ] && [ "${YEAR}" -eq "${PREV_YEAR}" ]; then
    : # 到達しない（上記条件でカバー）
fi

log "INFO" "収集開始: year=${YEAR}, term=${TERM}"

# === URL・ファイル名生成 ===
if [ "${TERM}" -eq 1 ]; then
    # 前期: (year-1)年10月のデータ
    FILE_YEAR=$((YEAR - 1))
    YY=$(printf '%02d' $((FILE_YEAR % 100)))
    MM="10"
else
    # 後期: year年4月のデータ
    YY=$(printf '%02d' $((YEAR % 100)))
    MM="04"
fi

FILENAME="fan${YY}${MM}.lzh"
TXT_FILE="fan${YY}${MM}.txt"
URL="${BASE_URL}${FILENAME}"
OUTPUT_DIR="data/${YEAR}_${TERM}"

log "INFO" "ダウンロードURL: ${URL}"

# === ダウンロード（リトライ付き、終了コード 2）===
mkdir -p tmp

download_success=false
for attempt in $(seq 1 ${RETRY_MAX}); do
    log "INFO" "ダウンロード試行 ${attempt}/${RETRY_MAX}: ${URL}"

    http_code=$(curl --silent --write-out "%{http_code}" \
        --output "tmp/${FILENAME}" \
        --connect-timeout 30 \
        --max-time 120 \
        "${URL}" 2>"tmp/curl_err.txt") || {
        # 接続エラー・タイムアウト
        err_msg=$(cat "tmp/curl_err.txt" 2>/dev/null || echo "不明なエラー")
        log "ERROR" "接続エラー (試行 ${attempt}/${RETRY_MAX}): ${err_msg}"
        if [ "${attempt}" -lt "${RETRY_MAX}" ]; then
            log "INFO" "${RETRY_INTERVAL}秒後にリトライします"
            sleep "${RETRY_INTERVAL}"
        fi
        continue
    }

    if [ "${http_code}" -eq 404 ]; then
        log "ERROR" "指定した年・期のデータは公式サイトに存在しません (HTTP 404): ${URL}"
        exit 2
    elif [ "${http_code}" -ge 400 ]; then
        log "ERROR" "HTTPエラー: ${http_code}: ${URL}"
        exit 2
    fi

    download_success=true
    break
done

if [ "${download_success}" = false ]; then
    log "ERROR" "ダウンロード失敗: ${RETRY_MAX}回試行しましたが接続できませんでした"
    exit 2
fi

log "INFO" "ダウンロード完了: tmp/${FILENAME}"

# === 解凍（終了コード 3）===
log "INFO" "ファイル解凍開始: tmp/${FILENAME}"
if ! "${LHASA_CMD}" efw=tmp/ "tmp/${FILENAME}" >> "${LOG_FILE}" 2>&1; then
    log "ERROR" "解凍失敗: tmp/${FILENAME}"
    exit 3
fi

if [ ! -f "tmp/${TXT_FILE}" ]; then
    log "ERROR" "解凍後のテキストファイルが見つかりません: tmp/${TXT_FILE}"
    exit 3
fi

log "INFO" "解凍完了: tmp/${TXT_FILE}"

# === Python でデータ処理（終了コード 4）===
log "INFO" "データ処理開始: python src/process_racer_data.py tmp/${TXT_FILE} ${YEAR} ${TERM} ${OUTPUT_DIR}"
if ! python src/process_racer_data.py "tmp/${TXT_FILE}" "${YEAR}" "${TERM}" "${OUTPUT_DIR}"; then
    log "ERROR" "データ処理失敗"
    exit 4
fi

log "INFO" "処理正常完了: ${OUTPUT_DIR}/racer_info.csv, ${OUTPUT_DIR}/racer_results.csv"
exit 0
