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


class MercariCrawler(cb.SeleniumCralwer):
    """
    メルカリの検索URLを指定し、1ページ目から順にクロールしてアイテムID等をparse、csvとして出力するクローラ

    """
    platform = "mercari"
    local_output_dir = current_dir / f"../output/crawler/{platform}"
    s3_output_dir = pathlib.Path(f"crawler/{platform}")


    def __init__(self, is_test=False, wait_sec=1.0, headless=True, save_to_s3=False):
        super().__init__(
            is_test=is_test, 
            wait_sec=wait_sec,
            headless=headless,
            save_to_s3=save_to_s3,
        )
        self.max_wait_sec = 20

        if save_to_s3:
            bucket_name = os.environ.get("BUCKET_NAME", None)
            self.s3_session = boto3.Session(profile_name="crawling")
            self.s3_bucket = s3_session.resource("s3").Bucket(bucket_name)
            

    def crawl_url(self, start_url):
        items = []
        next_url = start_url
        current_page = 0

        self.logger.info(f"Start crawling: {start_url}")
        while True:
            self.get_url(next_url)

            # wait until the item area is loaded
            try:
                WebDriverWait(self.driver, self.max_wait_sec).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.ID, "item-grid")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "p[slot='title']"))
                    )
                )

            except Exception as e:
                self.logger.error("Timeout occurred while loading the page.")
                self.logger.error(traceback.format_exc())
                break

            page_source = self.get_page_source()
            if page_source is None:
                self.logger.error(f"Failed to access the next page: {next_url}")
                break

            new_items = self.parse_items(page_source)
            if len(new_items) == 0:
                self.logger.warning(f"No items found: {next_url}")
                break
            
            items += new_items

            next_url = self.get_next_url(start_url, current_page)
            if next_url is None:
                break

            if self.is_test and current_page >= 2:
                break

            current_page += 1

        self.logger.info(f"Finish crawling: {start_url}")
        new_df = pd.DataFrame(items)

        return new_df


    def parse_items(self, html):
        items = []
        try:
            soup = BeautifulSoup(html, "lxml")
            item_area = soup.select("#item-grid")
            if len(item_area) == 0:
                return items

            li_list = item_area[0].select("li")

            for li in li_list:
                items.append(self.parse_item_info(li))

        except Exception as e:
            self.logger.error(f"An error occurred while parsing items.")
            self.logger.error(traceback.format_exc())

        return items


    def parse_item_info(self, item):
        item_info = {}

        try:
            # item id
            url = item.select("a")[0]["href"]
            item_info["item_id"] = url.split("/")[-1]

            # parse datetime
            item_info["crawl_date"] = util.get_jst_time()

        except Exception as e:
            self.logger.error(f"Failed to parse an item.")
            self.logger.error(traceback.format_exc())

        return item_info


    def get_next_url(self, start_url, current_page):
        try:
            q = urllib.parse.urlparse(start_url)
            qs_d = urllib.parse.parse_qs(q.query)
            qs_d["page_token"] = f"v1:{current_page+1}"

        except Exception as e:
            return None

        return urllib.parse.urlunparse(
            q._replace(query=urllib.parse.urlencode(qs_d, doseq=True))
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("urls")
    parser.add_argument("--is_test", action="store_true")
    parser.add_argument("--s3", action="store_true")
    args, leftovers = parser.parse_known_args()

    url_df = pd.read_csv(current_dir / args.urls)
    crawler = MercariCrawler(
        is_test=args.is_test, 
        headless=(not args.is_test),
        save_to_s3=args.s3
    )
    crawler.run_crawler(url_df["url"])
