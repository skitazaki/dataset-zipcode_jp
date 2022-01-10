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

データ項目の意味は[日本郵便のWebサイト](http://www.post.japanpost.jp)で確認してください。

## How to use

You need to deploy a serverless app on AWS in order to create a datapackage, since this repository provides only a package definition.
The serverless app downloads four csv files from the Japan Post website and creates a datapackage on Amazon S3.
Please take a look at the files under *serverless/* directory and give it a try with your AWS settings described in `Makefile`.

## How to extend

`datapackage.yml` is a source file for manual editing, and it would be converted into `datapackage.json` for packaging.

## LICENSE

The Japan Post does not claim copyright for the original data files of zipcode.

ref - [郵便番号データの説明 - 日本郵便](http://www.post.japanpost.jp/zipcode/dl/readme.html)

    郵便番号データに限っては日本郵便株式会社は著作権を主張しません。自由に配布していただいて結構です。

MIT License is applied to scripts in this repository, and [Open Data Commons Public Domain Dedication and License (PDDL)](https://opendatacommons.org/licenses/pddl/) is applied to the package definition.
