# Japanese Zipcode

There are four files of zip code in Japan from the Japan Post.
Three of them are named *ken_all* for nation wide zip codes with different writing systems of Oogaki, Kogaki, and Roman.
Another file is for specific companies, organizations, or locations.

-----

日本郵便株式会社からは４種類のファイルをダウンロードできます。

読み仮名データに関して３種類の記法があります。

* 大書き: 読み仮名データの促音・拗音を小書きで表記しないもの
* 小書き: 読み仮名データの促音・拗音を小書きで表記するもの
* ローマ字

その他に、大口事業所個別番号があります。

それぞれのデータは `scripts/pulldata.py` を使ってダウンロードできます。
ダウンロードしたデータは文字エンコーディングが cp932 から utf8 に変換され、
半角カタカナは全角カタカナに変換されます。
それぞれのCSVファイルは `data` ディレクトリに配置されます。

データ確認や変換に関する追加作業は `notebook` ディレクトリで管理します。

日本郵便株式会社: http://www.post.japanpost.jp

## How to use

You can run `pulldata.py` in order to download data files under `data/` directory from the Japan Post site.
This script converts encodings from "*cp932*" to "*utf8*" and normalizes characters from half-width Katakana to full-width.

```bash
$ python3 scripts/pulldata.py
```

To make a zip package, use *zipfile* module in Python.

```bash
$ python3 -m zipfile -c datapackage.zip datapackage.json data
```

`datapackage.yml` is a source file for manual editing, and `datapackage.json` is converted from YAML format.

## LICENSE

[郵便番号データの説明 - 日本郵便](http://www.post.japanpost.jp/zipcode/dl/readme.html)

    郵便番号データに限っては日本郵便株式会社は著作権を主張しません。自由に配布していただいて結構です。

Others:

- MIT license for scripts.
- [Open Data Commons Public Domain Dedication and License (PDDL)](https://opendatacommons.org/licenses/pddl/) for package definition.
