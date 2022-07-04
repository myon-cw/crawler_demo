import sys
import os
import time
import datetime
import traceback
import boto3
import pathlib
import pandas as pd
import urllib.parse
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
current_dir = pathlib.Path(__file__).parent
sys.path.append("../util")
import util
import crawler_base as cb


class MercariDownloader(cb.SeleniumDownloader):
    """
    メルカリのitem idのリストをinputとして与え、各idの商品ページに順番にアクセスし、HTMLをダウンロードする

    """
    platform = "mercari"
    base_url = "https://jp.mercari.com/item/"
    local_output_dir = current_dir / f"../output/downloader/{platform}"
    s3_output_dir = pathlib.Path(f"downloader/{platform}")
    max_wait_sec = 10.0
    """
    bucket_name = os.environ.get("BUCKET_NAME", None)
    self.s3_session = boto3.Session(profile_name="crawling")
    self.s3_bucket = s3_session.resource("s3").Bucket(bucket_name)
    """
    logger = util.Logger.setup_logger(
        logger_name=__name__, 
        log_dir=current_dir / f"../logs/{platform}/downloader"
    )


    def __init__(self, is_test=False, save_to_s3=False):
        super().__init__(is_test=is_test, save_to_s3=save_to_s3)


    @classmethod
    def get_item_url(cls, item_id):
        return urllib.parse.urljoin(cls.base_url, item_id)


    @classmethod
    def wait_func(cls, driver, max_wait_sec):
        # wait until the item area is loaded
        try:
            WebDriverWait(driver, max_wait_sec).until(
                EC.any_of(
                    EC.presence_of_element_located((By.ID, "item-info")),
                )
            )

        except Exception as e:
            cls.logger.error("Timeout occurred while loading the page.")
            cls.logger.error(traceback.format_exc())
            return False
        
        return True


    @classmethod
    def get_latest_crawler_result(cls, from_s3=False):
        if from_s3:
            s3_crawler_output_dir = pathlib.Path(f"crawler/{cls.platform}")
            raise NotImplementedError

        else:
            local_crawler_output_dir = current_dir / f"../output/crawler/{cls.platform}"
            paths = util.list_all_files(local_crawler_output_dir, ".csv")

        if paths is None or len(paths) == 0:
            return None

        return paths[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", default=None)
    parser.add_argument("--is_test", action="store_true")
    parser.add_argument("--s3", action="store_true")
    args, leftovers = parser.parse_known_args()

    if args.items is None:
        args.items = MercariDownloader.get_latest_crawler_result(from_s3=args.s3)

    if args.s3:
        bucket_name = os.environ.get("BUCKET_NAME", None)
        s3_bucket = s3_session.resource("s3").Bucket(bucket_name)
        _, local_url_path = util.s3_download_file(s3_bucket, args.items)
        item_id_df = pd.read_csv(local_url_path)
    else:
        item_id_df = pd.read_csv(args.items)
    

    downloader = MercariDownloader(
        is_test=args.is_test,
        save_to_s3=args.s3
    )
    downloader.run_downloader(item_id_df["item_id"])
