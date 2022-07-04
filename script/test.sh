#!/bin/bash
function test () {
  source ../venv/bin/activate

  python3 ../mercari/crawler.py "../util/test/test_mercari_urls.csv" --is_test
  python3 ../mercari/downloader.py --is_test
  python3 ../mercari/parser.py --is_test

  echo $?
}

DATETIME="$(date +%Y-%m-%d-%H-%M-%S)" 
LOG_DIR="logs/mercari/test"

LOCAL_LOG_DIR="../$LOG_DIR"
LOG_FILE_NAME="$DATETIME.log"

source ~/.bashrc
#cd `dirname $0`
#mkdir -p "$LOCAL_LOG_DIR"
#result=$(test 2>&1 | tee $LOCAL_LOG_DIR/$LOG_FILE_NAME)
#result_flag=$"${result: -1}"
test
