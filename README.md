# Japanese Zipcode

There are four files from Japan Postal.

Three types of different writing systems for Japanese yomi-gana:

* Oogaki
* Kogaki
* Roman

And, another file is different code structure for facilities.

You can download all files using `scripts/pulldata.py`.
Each downloaded file is converted its encoding from 'cp932' to 'utf8',
normalized from half-width Katakana to full-width,
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
半角カタカナは全角に変換されます。
最終的に `data` ディレクトリに配置されます。

日本郵便株式会社: http://www.post.japanpost.jp

## Development

Setup Python development environments using `pipenv`.

```bash
$ pip3 install --user pipenv
$ pipenv install --ignore-pipfile
```
Prepare `.env` file if you use VisualStudio Code.
`.vscode/settings.json` depends on environmental variable to search Python binary.

```bash
$ echo PYTHONENV=`pipenv --venv` > .env
```

To generate CREATE statements, run `pgddl.py` in *scripts/*.

```bash
$ pipenv run scripts/pgddl.py > datapackage.sql
```


## LICENSE

[郵便番号データの説明 - 日本郵便](http://www.post.japanpost.jp/zipcode/dl/readme.html)

    郵便番号データに限っては日本郵便株式会社は著作権を主張しません。自由に配布していただいて結構です。

Others:

- MIT license for scripts.
- [Open Data Commons Public Domain Dedication and License (PDDL)](https://opendatacommons.org/licenses/pddl/) for package definition.
