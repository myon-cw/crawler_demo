# Crawler Demo

## 環境構築

- Pythonをインストール
- venvで仮想環境を作成( https://docs.python.org/ja/3/library/venv.html )
- `source venv/bin/activate` をして、仮想環境を立ち上げ
- `requirements.txt` にあるライブラリをインストール
  - `pip3 install -r requirements.txt`
- Google Chromeがインストールされていない場合は、インストール
- Chromeのバージョンを確認し、それに対応するchromedriverをダウンロード（ https://chromedriver.chromium.org/downloads )して、`util/webdriver/chromedriver` として保存

## テスト

`script/test.sh` が実行できれば成功。

### input
```
platform,url
mercari,https://jp.mercari.com/search?keyword=PS5&order=desc&sort=created_time&price_min=30000&t2_category_id=76&t1_category_id=5&category_id=701&t3_category_id=701
mercari,https://jp.mercari.com/search?keyword=Switch&order=desc&sort=created_time&price_min=20000&t2_category_id=76&t1_category_id=5&category_id=701&t3_category_id=701
```

### output
```
html,item_id,URL,item_name,last_updated,price,is_soldout,category_1,category_2,category_3,brand,quality,shipping_cost,shipping_pattern,shipping_from,shipping_days,parse_success
m79660349119_2022-07-04-11-09-07.html,m79660349119,https://jp.mercari.com/item/m79660349119,プレイステーション5 PS5 本体 中古,プレイステーション5,71000,False,本・音楽・ゲーム,テレビゲーム,家庭用ゲーム本体,本・音楽・ゲーム,目立った傷や汚れなし,着払い(購入者負担),未定,熊本県,2~3日で発送,True
m32188466366_2022-07-04-11-09-02.html,m32188466366,https://jp.mercari.com/item/m32188466366,PS5 プレイステーション5 本体 CFI-1000A01,プレイステーション5,74000,False,本・音楽・ゲーム,テレビゲーム,家庭用ゲーム本体,本・音楽・ゲーム,目立った傷や汚れなし,送料込み(出品者負担),梱包・発送たのメル便,岐阜県,2~3日で発送,True
m80256323412_2022-07-04-11-09-09.html,m80256323412,https://jp.mercari.com/item/m80256323412,プレイステーション5 PS5 本体,プレイステーション5,72555,False,本・音楽・ゲーム,テレビゲーム,家庭用ゲーム本体,本・音楽・ゲーム,目立った傷や汚れなし,着払い(購入者負担),未定,埼玉県,1~2日で発送,True
m82916920036_2022-07-04-11-09-04.html,m82916920036,https://jp.mercari.com/item/m82916920036,プレイステーション5,プレイステーション5,100000,False,本・音楽・ゲーム,テレビゲーム,家庭用ゲーム本体,本・音楽・ゲーム,未使用に近い,送料込み(出品者負担),クロネコヤマト,東京都,1~2日で発送,True
m94678949868_2022-07-04-11-08-50.html,m94678949868,https://jp.mercari.com/item/m94678949868,PS5 プレイステーション5 デジタルエディション,ソニー,60000,False,本・音楽・ゲーム,テレビゲーム,家庭用ゲーム本体,本・音楽・ゲーム,目立った傷や汚れなし,送料込み(出品者負担),ゆうゆうメルカリ便,神奈川県,2~3日で発送,True
```