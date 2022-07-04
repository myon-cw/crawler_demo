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
import logging
import multiprocessing as mp
import slackweb
from dotenv import load_dotenv


current_dir = pathlib.Path(__file__).parent
temp_dir = current_dir / "../temp"
temp_dir.mkdir(exist_ok=True, parents=True)
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "\
    + "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
headers = {
    "User-Agent": user_agent, 
}
load_dotenv(current_dir / "../.env")
JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")


def get_jst_time():
    return datetime.datetime.now(JST)


def get_jst_time_str():
    return get_jst_time().strftime("%Y-%m-%d-%H-%M-%S")


class Logger(object):
    @staticmethod
    def setup_logger(
        logger_name="default",
        level=logging.INFO,
        log_dir=None
        ):
        logging.basicConfig(stream=sys.stderr)
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

        sh = logging.StreamHandler()
        sh.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s[%(levelname)s/%(processName)s]%(filename)s(%(lineno)d): %(message)s"
        )
        sh.setFormatter(formatter)
        logger.addHandler(sh)
        logger.propagate = False

        if log_dir is not None:
            pathlib.Path(log_dir).mkdir(exist_ok=True, parents=True)
            logger = Logger.add_file_handler(logger, log_dir)

        return logger


    @staticmethod
    def add_file_handler(logger, log_dir, level=logging.DEBUG):
        log_file_name = f"{get_jst_time_str()}.log"
        log_file_path = pathlib.Path(log_dir) / log_file_name
        fh = logging.FileHandler(log_file_path)
        fh.setLevel(level)
        fh_formatter = logging.Formatter(
            "%(asctime)s[%(levelname)s/%(processName)s]%(filename)s(%(lineno)d): %(message)s"
        )
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)

        return logger


    @staticmethod
    def multiline_log_text(text):
        sep_str = "-" * 15
        formatted = f"{sep_str} LOG START {sep_str}\n" +\
            f"{text}\n" +\
            f"{sep_str} LOG END {sep_str}\n"

        return formatted


logger = Logger.setup_logger()


def post_msg_to_slack(text="", attachments=[]):
    url = os.environ.get("SLACK_WEBHOOK_URL", None)
    if url is None:
        logger.error("Failed to get SLACK_WEBHOOK_URL from .env")
        return False

    slack = slackweb.Slack(url=url)

    if len(text) > 0:
        slack.notify(text=text)

    if len(attachments) > 0:
        slack.notify(attachments=attachments)
    
    return True


def post_error_to_slack(msg, error_msg=""):
    msg = f"<!channel> :warning::warning:  {msg}  :warning::warning:"

    attachments = [{
        "pretext": msg, 
        "text": error_msg, 
        "color": "danger", 
    }]

    return post_msg_to_slack(attachments=attachments)


def interval(interval_sec):
    def __interval(func):
        def __interval__wrapper(*args, **kwargs):
            base_time = time.time()
            result = func(*args, **kwargs)
            elapsed_sec = time.time() - base_time
            
            if elapsed_sec < interval_sec:
                time.sleep(interval_sec - elapsed_sec)

            return result
        
        return __interval__wrapper
    return __interval


def get_url(url, headers=None, num_retry=2, retry_interval=5):
    for i in range(num_retry+1):
        if i > 0:
            time.sleep(retry_interval)
            logger.info("Retrying...")

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response
        
        elif response.status_code == 404:
            logger.warning(f"The page not found: '{url}'")

        else:
            logger.warning(
                f"The page returns response code {response.status_code}: '{url}'"
            )
 
    logger.error(
        f"Failed to access the page in {num_retry+1} times: '{url}'"
    )

    return None


def download_file(url, output_path, **kwargs):
    response = get_url(url, **kwargs)
    download_success = False

    if response is not None:
        try:
            with open(output_path, "w") as f:
                f.write(response.text)

            logger.info(f"Successfully downloaded: '{url}'")
            download_success = True
        
        except Exception as e:
            logger.error(
                f"An error occurred while saving: '{url}'.\n"\
                + f"{traceback.format_exc()}" 
            )
    
    else:
        logger.error(f"Failed to download: '{url}'")

    return download_success


def s3_upload_file(s3_bucket, local_path, s3_path):
    local_path = str(local_path)
    s3_path = str(s3_path)
    upload_success = False
    logger.debug(f"Uploading '{local_path}' to s3: '{s3_path}'")

    try:
        s3_bucket.upload_file(local_path, Key=s3_path)
        logger.info(f"Successfully uploaded: '{s3_path}'")
        upload_success = True
    
    except Exception as e:
        logger.error(
            f"Failed to upload: '{s3_path}'\n{traceback.format_exc()}"
        )

    return upload_success


def s3_save_file(url, s3_bucket, s3_path, **kwargs):
    temp_path = temp_dir / f"{get_jst_time()}_s3_save_file"
    download_success = download_file(url, temp_path, **kwargs)
    if not download_success:
        return False

    upload_success = s3_upload_file(s3_bucket, temp_path, s3_path)
    temp_path.unlink()
    if not upload_success:
        return False

    return True


def s3_download_file(s3_bucket, s3_path, local_path=None):
    s3_path = str(s3_path)
    download_success = False
    logger.debug("Downloading file from s3: '{}'".format(s3_path))

    if local_path is None:
        local_path = str(temp_dir / f"temp_{get_jst_time_str()}")
    else:
        local_path = str(local_path)

    try:
        s3_bucket.download_file(s3_path, local_path)
        logger.info("Successfully downloaded: '{}'".format(s3_path))
        download_success = True
    
    except Exception as e:
        logger.error("Failed to download: '{}'. Error: {}, {}".format(s3_path, e, e.args))

    return download_success, local_path


def s3_download_files(s3_bucket, s3_paths, local_dir):
    local_dir = pathlib.Path(local_dir)

    global _s3_download_file
    def _s3_download_file(s3_path):
        local_path = local_dir / pathlib.Path(s3_path).name
        download_success, local_path = s3_download_file(
            s3_bucket, s3_path, local_path)

        return download_success
    
    with mp.Pool(mp.cpu_count()) as p:
        result = p.map(_s3_download_file, s3_paths)

    return result


def list_all_files(directory, extension=None, size=None, sort=False):
    if extension is not None and extension[0] != ".":
        extension = "." + extension

    directory = pathlib.Path(directory)

    if extension is None:
        logger.info(
            "Listing all files in the directory: '{}'".format(str(directory)))
    else:
        logger.info(
            "Listing all files in the directory: '{}' with extension: '{}'".format(
                str(directory), extension))

    path_list = []
    files = directory.glob("**/*")

    if size is None:
        for file in files:
            if file.is_file() and (extension is None or file.suffix == extension):
                path_list.append(str(file))
    else:
        for i, obj in enumerate(files):
            if len(path_list) >= size:
                break
            
            if file.is_file() and (extension is None or file.suffix == extension):
                path_list.append(str(file))

    if sort:
        path_list.sort()

    return path_list


def s3_list_all_files(s3_bucket, prefix="", extension=None, size=None, sort=False, filter_func=None):
    prefix = str(prefix)

    if size is None:
        size = float("inf")

    if extension is not None and extension[0] != ".":
        extension = "." + extension

    if extension is None:
        logger.debug(
            "Listing all files with prefix: '{}'".format(prefix))
    else:
        logger.debug(
            "Listing all files with prefix: '{}' and extension: '{}'".format(prefix, extension))

    path_list = []
    objects = s3_bucket.objects.filter(Prefix=prefix)

    for i, obj in enumerate(objects):
        if len(path_list) >= size:
            break
        
        path = pathlib.Path(obj.key)
        if extension is None or path.suffix == extension:
            if filter_func is None or filter_func(path):
                path_list.append(obj.key)

    if sort:
        path_list.sort()

    return path_list


def read_html(html_path):
    try:
        with open(html_path, "r") as f:
            content = f.read()

        return content
    
    except Exception as e:
        logger.error(
            f"An error occurred while reading: '{html_path}'.\n"\
            + f"{traceback.format_exc()}" 
        )

    return None


def s3_read_html(s3_bucket, s3_html_path):
    s3_html_path = pathlib.Path(s3_html_path)
    temp_path = temp_dir / f"{get_jst_time()}_{s3_html_path.stem}.html"
    download_success, local_path = s3_download_file(s3_bucket, s3_html_path, temp_path)
    content = None

    if download_success:
        try:
            with open(temp_path, "r") as f:
                content = f.read()

        except Exception as e:
            logger.error(
                f"An error occurred while reading: '{html_path}'.\n"\
                + f"{traceback.format_exc()}" 
            )

        pathlib.Path(local_path, missing_ok=True).unlink()

    return content


def split_list(li, num_splits):
    splitted_list = [[] for i in range(num_splits)]
    for i, elem in enumerate(li):
        splitted_list[i % num_splits].append(elem)

    return splitted_list


if __name__ == "__main__":
    pass
