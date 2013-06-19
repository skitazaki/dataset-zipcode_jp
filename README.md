# Japanese Zipcode

There are four files from Japan Postal.

Three types of different writing systems for Japanese yomi-gana:

* Oogaki
* Kogaki
* Roman

And, another file is different code structure for facilities.

You can download all files using `scripts/pulldata.py`.
Each downloaded data is converted its encoding from 'cp932' to 'utf8',
and saved under `data` directory.

-----

日本郵便株式会社からは４種類のファイルをダウンロードできます。

読み仮名データに関して３種類の記法があります。

* 大書き: 読み仮名データの促音・拗音を小書きで表記しないもの
* 小書き: 読み仮名データの促音・拗音を小書きで表記するもの
* ローマ字

その他に、大口事業所個別番号があります。

それぞれのデータは `scripts/pulldata.py` でダウンロードできます。
ダウンロードしたデータは文字エンコーディングが cp932 から utf8 に変換され、
`data` ディレクトリに配置されます。

