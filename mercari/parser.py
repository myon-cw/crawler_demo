import sys
import os
import time
import datetime
import traceback
import boto3
import pathlib
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import requests
import urllib.parse
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
current_dir = pathlib.Path(__file__).parent
sys.path.append("../util")
import util
import crawler_base as cb


class MercariParser(cb.ParserBase):
    """
    商品ページのHTMLから、商品名、価格、出品者、商品の情報の各項目をパースし、
    CSVに出力する

    """
    platform = "mercari"
    local_output_dir = current_dir / f"../output/parser/{platform}"
    s3_output_dir = pathlib.Path(f"parser/{platform}")
    """
    bucket_name = os.environ.get("BUCKET_NAME", None)
    self.s3_session = boto3.Session(profile_name="crawling")
    self.s3_bucket = s3_session.resource("s3").Bucket(bucket_name)
    """
    logger = util.Logger.setup_logger(
        logger_name=__name__, 
        log_dir=current_dir / f"../logs/{platform}/parser"
    )


    def __init__(self, is_test=False, save_to_s3=False):
        super().__init__(
            is_test=is_test, 
            save_to_s3=save_to_s3,
        )


    @classmethod
    def parse_html(cls, html_path):
        html_path = pathlib.Path(html_path)
        result = {
            "html": html_path.name
        }

        try:
            content = util.read_html(html_path)
            all_soup = BeautifulSoup(content, "lxml")

            # item id, URL
            url = all_soup.select('meta[property="og:url"]')[0].attrs["content"]
            result["item_id"] = url.split("/")[-1]
            result["URL"] = url

            soup = all_soup.select("#item-info")[0]

            # 商品名
            result["item_name"] = soup.select("mer-heading")[0].attrs["title-label"]

            # 最終アップデート
            result["last_updated"] = soup.select('section.aITlH mer-text[color="secondary"]')[0].text
            
            # 価格
            price = soup.select("mer-price")[0].attrs["value"]
            result["price"] = int(price)

            # 売り切れか
            button_text = all_soup.select('mer-button[data-testid="checkout-button"]')[0].text
            result["is_soldout"] = "売り切れ" in button_text

            # カテゴリ
            categories = soup.select("mer-breadcrumb-list mer-breadcrumb-item")
            for i, c in enumerate(categories):
                result[f"category_{i+1}"] = c.text

            # ブランド
            result["brand"] = soup.select("mer-text-link.jskyke")[0].text

            # 商品の状態
            result["quality"] = soup.select('span[data-testid="商品の状態"]')[0].text

            # 配送料の負担
            result["shipping_cost"] = soup.select('span[data-testid="配送料の負担"]')[0].text

            # 配送の方法
            result["shipping_pattern"] = soup.select('span[data-testid="配送の方法"]')[0].text

            # 発送元の地域
            result["shipping_from"] = soup.select('span[data-testid="発送元の地域"]')[0].text

            # 発送までの日数
            result["shipping_days"] = soup.select('span[data-testid="発送までの日数"]')[0].text

            # 説明
            description = soup.select('section.aITlH mer-text[data-testid="description"]')[0].text
            #result["description"] = description

            result["parse_success"] = True
        
        except Exception as e:
            cls.logger.warning(f"Failed to parse html: {html_path}")
            cls.logger.warning(traceback.format_exc())
            result["parse_success"] = False

        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--html_dir", default=None)
    parser.add_argument("--is_test", action="store_true")
    parser.add_argument("--s3", action="store_true")
    args, leftovers = parser.parse_known_args()

    if args.html_dir is None:
        args.html_dir = current_dir / f"../output/downloader/mercari"

    if args.s3:
        bucket_name = os.environ.get("BUCKET_NAME", None)
        s3_bucket = s3_session.resource("s3").Bucket(bucket_name)
        local_dir = current_dir / f"../temp/{util.get_jst_time_str()}"
        local_dir.mkdir(exist_ok=True, parents=True)
        s3_paths = util.s3_list_all_files(s3_bucket, args.html_dir, extension=".html")
        util.s3_download_files(s3_bucket, s3_paths, local_dir)
    else:
        local_dir = args.html_dir

    parser = MercariParser(
        is_test=args.is_test, 
        save_to_s3=args.s3
    )
    parser.run_parser(local_dir)
