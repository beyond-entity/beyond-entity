# be-parser

[English](README.md) | [한국어](README_ko.md) | **日本語**

Java/Spring コードベース向けの静的解析ツールです。ソースをビルドも実行もせずに読み取り、次のことを行います。

1. **アーキテクチャモデル**を作ります。モジュール、processor（controller・service・repository・listener など）、endpoint、データストア、entity と attribute、およびそれらの間の**データリネージ**です。
2. 同梱のルールカタログで**セキュリティ事前チェック**を行います。ルールは CWE、OWASP Top 10、韓国行政安全部のソフトウェアセキュリティ弱点診断ガイドに対応しています。
3. 必要に応じて、両方の結果をローカル MCP サーバー経由で **Beyond Entity（BE）プロジェクトに送信**します（[Beyond Entity 連携](#beyond-entity-連携)を参照）。

モデルは次のファイルに出力されます。

- `architecture-facts.json`：ソース位置付きの、ライブラリ非依存の fact。
- `be-plan.json`：BE が保存する形のモデル。
- Markdown レポート。

ステップ 1・2 は完全にオフラインで動作します。Beyond Entity のインストールが必要なのはステップ 3 だけです。

> 状態：`0.1.0-SNAPSHOT`、開発中です。出力形式は変わる可能性があります。

---

## 目次

- [解析対象](#解析対象)
- [クイックスタート](#クイックスタート)
- [コマンド](#コマンド)
- [出力ファイル](#出力ファイル)
- [Beyond Entity 連携](#beyond-entity-連携)
- [設定](#設定)
- [レポートの言語](#レポートの言語)
- [セキュリティルールカタログ](#セキュリティルールカタログ)
- [仕組み](#仕組み)
- [制限事項](#制限事項)
- [パッケージの構成](#パッケージの構成)

このフォルダはすぐに実行できるパッケージです。Java 21 以上だけが必要です。[INSTALL.md](INSTALL.md) を参照してください。ライセンス：MIT（このリポジトリ直下の `LICENSE`）。

---

## 解析対象

| 領域 | 対応範囲 |
|---|---|
| ビルド構成 | Maven・Gradle のマルチモジュールプロジェクト。各モジュールを固有のソースルートで解析。個別にデプロイされる Boot サービスからなるリアクターはサービスごとにモデルとなり、複数のサービスが使うライブラリは独自のモデルとなって、サービスからの呼び出しがそこにつながる |
| Web | Spring MVC / WebFlux controller、request mapping、パラメータと body、Spring Cloud Gateway のルート |
| コンポーネント | `@Service`、`@Component`、`@Repository`、XML bean 定義（eGovFrame 形式）、コンストラクタ・フィールド・setter インジェクション、interface → 実装の解決、profile・条件付き bean |
| データアクセス | JPA / Spring Data（派生クエリ、`@Query`、R2DBC を含む）、MyBatis mapper XML（動的 SQL・XML リロードを含む）、eGovFrame DAO、Spring Data Redis / MongoDB / Elasticsearch repository、Spring Session JDBC テーブル。データソースは Spring Boot・Druid・Hikari・dynamic-datasource のキーから読む（p6spy/log4jdbc のラッパーも含む）。スキーマスクリプト、Flyway、Liquibase、リポジトリ内のどこにある DDL スクリプトも使用 |
| メッセージング | Kafka（Kafka Streams トポロジーを含む）、RabbitMQ（exchange、queue、binding、dead-letter の経路）、Spring Cloud Stream、JMS、Amazon SQS。JMS/SQS のキューはそれを使うアプリケーションモデルの entity、複数のサービスが使う場合は共有モデル「Message queues」の entity |
| ライブラリ | カタログベースの port：Spring AI、LangChain4j、eGovFrame core、Spring Data |
| リネージ | argument、result、handoff（ある呼び出しの結果値が別の呼び出しに渡されるもの）、composed、store リネージ。オブジェクト port 内のフィールド単位（`creditCard.cardNumber`）まで。メッセージ、ログ、セッション属性を含む。検索キーは検索されたデータと区別 |
| セキュリティ | ルール 35 件（インジェクション、暗号、秘密情報、認可、CSRF、PII の保存・ログ、状態を変更する GET、認証なしの書き込みなど）、PII カラムの分類と保護レベル |

解析はソースルートだけで動作します。対象の第三者 classpath が不要なため、依存ライブラリを取得できない閉域網でも使えます。

---

## クイックスタート

```bash
# 1. be-parser コマンドを PATH に登録 (Java 21+)。またはこのフォルダで bin/be-parser を実行
./install.sh                         # → ~/.local/bin/be-parser

# 2a. Web 画面：フォルダと Beyond Entity プロジェクトを選んで Run
be-parser serve

# 2b. またはコマンド 1 つで：解析、レポート作成、Beyond Entity プロジェクトへ送信
be-parser projects                                   # プロジェクト ID を調べる
be-parser run ~/src/spring-app --project PxxxxxxxxxxxX
be-parser run ~/src/spring-app --no-send             # 解析とレポートのみ、Beyond Entity なし
```

`run` はすべての結果を `~/.be-parser/out/<リポジトリ>/` に書き出します：`architecture-facts.json`、`be-plan.json`、`analysis-report.md`、`security-report.md`、`pii-flow.md`。

`serve` は `127.0.0.1` でのみ開く Web 画面です。**Run** タブではフォルダを選び、そのフォルダのオプションを編集・記憶して実行し、実行ログとレポートをその場で確認できます。対象プロジェクトは Beyond Entity のプロジェクト一覧から選ぶか、「+ New project…」で名前と `.bemdl` ファイル名を入力して新規作成します（既定は `<フォルダ>/<フォルダ>.bemdl`）。**Settings** タブではすべての設定を説明・既定値とともに表示し、ユーザーの既定値として保存します（BE 接続テストを含む）。新しいプロジェクトは CLI でも作成できます：`be-parser projects create <file.bemdl> [--name <名前>]`。`be-parser config` と同じファイルを編集します（[設定](#設定)）。API 呼び出しには起動時に作られるランダムなトークンが必要で、トークンは表示・自動で開かれる URL に含まれます。ポートとトークンは `~/.be-parser/serve.json` に保存されるため、他のローカルツール（例：Beyond Entity デスクトップアプリ）が `http://127.0.0.1:<port>/?token=<token>&project=<プロジェクト ID>` で特定のプロジェクトの画面を開けます。

例：[spring-petclinic](https://github.com/spring-projects/spring-petclinic) では、数秒でセキュリティ finding 16 件と、3 つのデータベースプロファイル（MySQL、PostgreSQL、H2）それぞれのテーブル 7 個が得られます。

---

## コマンド

すべてのコマンドは `be-parser`（`bin/be-parser`、Windows は `bin\be-parser.cmd`）のサブコマンドで、`lib/be-extractor.jar` を実行します。`java -jar lib/be-extractor.jar <コマンド>` も同じです。`run`（解析+レポート+送信）、`projects`（プロジェクト一覧）、`serve`（Web 画面）は[クイックスタート](#クイックスタート)を参照してください。

### `analyze`：ソース → fact

```
analyze <repo-root> [-o architecture-facts.json] [--commit <sha>] [--exclude <glob>]...
        [--report <base>] [--schema model_creation_schema.json] [--no-report] [--catalog <dir>] [--lang en|ko|ja]
```

| オプション | 意味 |
|---|---|
| `-o` | 出力 fact ファイル（既定 `architecture-facts.json`） |
| `--commit` | 記録するソースのコミット。省略時はリポジトリの git 情報から branch・dirty 状態と共に読み取る |
| `--exclude` | スキップするパスの glob（複数指定可）。例：`--exclude '**/generated/**'` |
| `--report` | 解析レポートのベース名（`<base>.md`、`<base>.json`）。既定は fact と同じ場所の `analysis-report` |
| `--no-report` | 解析レポートを作成しない |
| `--schema` | レポートでデータ型を検証する BE ストレージ型カタログ |
| `--catalog` | 外部セキュリティカタログのディレクトリ（既定：同梱カタログ） |
| `--lang` | レポートの言語：`en`（既定）、`ko`、`ja`（[レポートの言語](#レポートの言語)を参照） |

### `plan`：fact → BE モデル（オフライン）

```
plan <architecture-facts.json> [-o be-plan.json] [--include-general-modules]
```

BE に接続せずに、`send` が書き込むモデル・processor・entity・リネージをそのまま作ります。`--include-general-modules` を付けると、Spring の役割を持たないモジュール（一般ライブラリ）も残します。

### `report`、`security-report`、`pii-report`

```
report           <architecture-facts.json> [-o <base>] [--schema model_creation_schema.json] [--catalog <dir>] [--lang en|ko|ja]
security-report  <architecture-facts.json> [-o security-report.md] [--catalog <dir>] [--lang en|ko|ja]
pii-report       <architecture-facts.json> [-o pii-flow.md] [--lang en|ko|ja]
```

- `report` は既存の fact から解析レポートを作り直します。
- `security-report` は finding をルール、CWE・標準への対応、位置、根拠と共に一覧にします。
- `pii-report` は PII カラム、その保護方式（ハッシュ、暗号化）、それを収集・公開する endpoint を一覧にします。

### `validate`

```
validate <architecture-facts.json> <model_creation_schema.json>
```

plan が書き込むすべてのデータ型が、BE ストレージ型カタログで許可されているかを確認します。

### `security-catalog`

```
security-catalog list|validate [--catalog <dir>] [--lang en|ko|ja]
security-catalog import-csv <items.csv> --id <standard-id> --version <v> --title <title>
        [--published <date>] [--source <url>] --catalog <dir> [--activate]
```

ルールカタログの一覧表示・検証を行います。新しい標準バージョン（例：より新しい CWE リスト）を外部カタログディレクトリに取り込むこともできます。

### `send`：fact → Beyond Entity

```
send <architecture-facts.json> [--config be-extractor.properties] [--dry-run] [--include-general-modules]
     [--allow-mass-resolve]
```

設定で指定した BE プロジェクトに、モデル、リネージ、セキュリティ finding を書き込みます。`--dry-run` は BE に接続して読み取るだけで、何も書き込みません。[Beyond Entity 連携](#beyond-entity-連携)を参照してください。

---

## 出力ファイル

| ファイル | 作成コマンド | 内容 |
|---|---|---|
| `architecture-facts.json` | `analyze` | fact（`MODULE`、`PROCESSOR`、`ENDPOINT`、`CALL`、`DATA_ENTITY`、`DATA_ATTRIBUTE`、`STORE_ACCESS`、`SECURITY_FINDING`、`UNRESOLVED` など）とソースファイル・行・根拠。ソースリポジトリ、branch、commit、extractor バージョン |
| `analysis-report.md` / `.json` | `analyze`、`report` | fact 種別ごとの件数、データストア、未解決項目、検証結果 |
| `be-plan.json` | `plan` | モデル → processor（入出力、endpoint、呼び出し依存）→ entity/attribute、SQL 形式の transformation で表したリネージ |
| `security-report.md` | `security-report` | 重大度別の finding と CWE / OWASP / 行政安全部ガイドへの対応 |
| `pii-flow.md` | `pii-report` | PII カラム、保護レベル、収集・公開する endpoint |
| `be-sync-report.json` | `send` | 作成・更新・削除したオブジェクト、失敗、セキュリティスキャン結果（`--dry-run` の場合は `be-sync-dry-run.json`） |

リネージは BE オブジェクトに対する SQL で表現します。例：

```sql
-- parser: EgovSysHistoryServiceImpl.selectSysHistory → EgovFileMngServiceImpl.deleteAllFileInf (handoff)
INSERT INTO {{EgovFileMngServiceImpl}} (atchFileId) SELECT p.OUTPUT.atchFileId FROM {{EgovSysHistoryServiceImpl}} p
```

---

## Beyond Entity 連携

Beyond Entity はデータ・アーキテクチャのモデリングツールです。`send` は Beyond Entity の**ローカルデスクトップ MCP サーバー**と stdio で通信します。対象プロジェクトは MCP サーバー自身が開くため、このリポジトリに認証情報は含まれません。 JMS/SQS のキュー entity にはデスクトップ MCP 3.2.38 以降が必要です。`send` はサーバーが提供する定義で plan を検査します。

`send` は次の順序で動作します。

1. MCP の利用ガイドを読み、plan を BE の現在の定義と照合します（schema check）。
2. コード解析 run を開始します（プロジェクト run + ノード run）。
3. モデル、processor、entity、attribute、transformation を作成・更新・削除します。差分だけを書き込みます。
4. セキュリティスキャンを解析 run と共にアトミックに記録します。根拠別（ソース fact、呼び出し到達、plan 由来）に分けます。finding が 200 件を超えるルールは、正確なソースファイル範囲に分けた complete スキャンとして記録します。
5. run を終了し、ソースの commit と extractor バージョンを含む checkpoint を残します。

安全装置：

- **`protected.projects`**（開発用の設定）：このリストのプロジェクトには書き込みません。`target.project` を誤ってその一つに設定した場合も同じです。多数のプロジェクトを一括で実行するためのもので、対象を自分で選ぶ実行には不要です。
- **プロジェクトロックの再試行**：プロジェクトがロックされている場合（デスクトップアプリやレビュー担当者が作業中）、`mcp.lock.retry_seconds` だけ待って再試行します。
- **大量解決の防止**：1 回の送信で、オープンな finding の異常に大きな割合が解決扱いになる場合、`--allow-mass-resolve` がなければ停止します。
- 書き込みが一つでも失敗するか、セキュリティスキャンを記録できなかった場合、`send` は 0 以外の終了コードで終わります。

設定ファイルは不要です。対象は `be-parser serve` で選ぶか、`run` に `--project` で渡します。リポジトリに設定を置くには、そこの `be-extractor.properties` に必要な[設定](#設定)を書きます。例：

```properties
target.project=PxxxxxxxxxxxX
report.language=ko
analysis.exclude=**/generated/**
```

すべてのオプションは [`be-extractor.example.properties`](be-extractor.example.properties) にあります。

```bash
be-parser run ~/src/spring-app --project PxxxxxxxxxxxX --dry-run
be-parser run ~/src/spring-app --project PxxxxxxxxxxxX
be-parser send out/architecture-facts.json --config be-extractor.properties   # existing facts, settings from a file
```

---

## 設定

実行オプションはすべて設定です。各値は次の層で決まり、後の層が前の層より優先されます：

1. 組み込みの既定値；
2. **ユーザーの既定値**：`~/.be-parser/config.properties`。`be-parser config set` または Web 画面の Settings タブで編集；
3. **設定ファイル**：`--config <file>`、なければ作業フォルダの `be-extractor.properties`（任意。リポジトリで設定を共有するとき）；
4. **フォルダごとのオプション**：`~/.be-parser/sources.json`。解析したフォルダごとに記憶（`run --save`、`config set --source`、Web の Run タブ）；
5. **コマンドラインオプション**。

相対パスはその値が書かれたファイルのフォルダを基準に、`~` はホームフォルダとして解釈します。`be-parser config` が各値とその出所を表示します。設定の保存場所を `~/.be-parser` 以外にするには `BE_PARSER_HOME` を指定します。

| キー | 既定値 | 意味 |
|---|---|---|
| `target.project` * | – | 解析結果を書き込む Beyond Entity プロジェクト。空なら解析のみ |
| `report.language` * | `en` | レポートと BE に書き込む finding の文言の言語：`en`、`ko`、`ja` |
| `analysis.exclude` * | – | スキップするファイル・フォルダの glob（カンマ区切り。Web 画面では 1 行に 1 つ） |
| `extract.include_general_modules` * | `false` | Spring の役割を持たないモジュール（一般ライブラリ）もモデルに含める |
| `analysis.repository_key` * | フォルダ名 | 複数の run にわたってソースリポジトリを識別するキー |
| `security.findings.branch` * | – | セキュリティ finding と共に記録する branch |
| `output.dir` | `~/.be-parser/out` | `run` が facts・plan・レポートを書き出す場所（リポジトリごとのサブフォルダ） |
| `java.heap` | `3g` | 解析の最大ヒープ（`BE_PARSER_HEAP` が優先） |
| `security.catalog.dir` | 同梱 | 外部セキュリティカタログのディレクトリ |
| `security.report.enabled` / `security.report.file` | `true` / `security-check-<repo>.md` | セキュリティレポートを BE ドキュメントとしてアップロード |
| `pii.report.enabled` / `pii.report.file` | `true` / `pii-flow-<repo>.md` | PII フローレポートを BE ドキュメントとしてアップロード |
| `checkpoint.actor` | `be-code-parser` | checkpoint と解析 run に記録される作成者名 |
| `implementation.status.enabled` | `true` | 作成したオブジェクトに実装状態も記録 |
| `be.schema` | – | 書き込み前に plan を照合する BE ストレージ型カタログ（`model_creation_schema.json`） |
| `security.findings.enabled` | `true` | セキュリティ finding を送信 |
| `security.findings.refresh` | `true` | 再検出された finding に今回の run の位置・コード片・メッセージを反映（人が決めたステータスは保持） |
| `security.findings.mass_resolve.min` / `.ratio` | `10` / `0.3` | 大量解決防止のしきい値 |
| `mcp.command` | `/usr/local/bin/beyond-entity-mcp` | Beyond Entity MCP サーバーの実行ファイル（`BE_MCP_COMMAND` が既定値の代わりになる） |
| `mcp.timeout.seconds` | `120` | MCP 呼び出しごとのタイムアウト |
| `mcp.batch_mode` | `true` | 送信中、呼び出し間でプロジェクト DB を開いたままにする |
| `mcp.lock.retry_seconds` / `mcp.lock.max_retries` | `30` / `20` | プロジェクトがロックされている間、待って再試行 |
| `protected.projects`（開発用） | – | パーサー開発中に多数のプロジェクトを一括で実行するとき、対象が誤って指定されても絶対に書き込まないプロジェクト ID。Web 画面にはなく、対象を自分で選ぶ実行には不要 |

\* フォルダごとのオプションとしても指定可能。

---

## レポートの言語

セキュリティレポート、PII フローレポート、BE に書き込む finding のタイトル・説明・対策は、**英語（既定）、韓国語、日本語**で作成できます。

| 対象 | 方法 |
|---|---|
| `send` | 設定ファイルに `report.language=ja` |
| `security-report`、`pii-report`、`report`、`analyze`、`security-catalog list` | `--lang ja` |
| すべてのコマンド | 環境変数 `BE_REPORT_LANGUAGE=ja`（既定値。`--lang` が優先） |

指定できる値：`en`、`ko`、`ja`（`english`、`korean`/`kr`、`japanese`/`jp` も可）。

言語によって変わるもの：

- レポートの見出し、表、説明；
- ルールのタイトル、説明、対策；
- 標準のタイトル、項目名、分類（行政安全部ガイドの英語・日本語名。OWASP・CWE は公式の英語名を維持）。

コードを引用する finding メッセージ（クラス、メソッド、パス、SQL）と開発者向けの解析レポート（`analysis-report.md`）は英語のままです。既存の BE プロジェクトで言語を変えると、次の `send` でレポートドキュメントが新しい言語で書き直され、新しい finding はその言語のタイトルになります。既存の finding のタイトルまで変わるかどうかは BE の更新動作（`security.findings.refresh`）によります。人が決めたステータスと判断はどちらの場合も保持されます。

---

## セキュリティルールカタログ

カタログは `lib/be-extractor.jar` の中（`security-catalog/`）に含まれています。

- `rules.json`：ルール 35 件。各ルールに検出方式、重大度と信頼度、CWE、標準への対応があります。文言は英語で、韓国語・日本語の翻訳が `i18n` にあります。
- `attribute-security.json`：PII データ種別と暗号化レベル。
- `standards/`：同梱の標準バージョン。CWE 4.20、CWE Top 25（2024、2025）、OWASP Top 10（2021、2025）、行政安全部ソフトウェアセキュリティ弱点診断ガイド（2021、49 項目）です。

標準はレポート作成時に解決されるため、カタログを更新すれば再解析なしで反映されます。再ビルドせずに新しい標準を使うには、`security-catalog import-csv` で作ったディレクトリを `--catalog`（または `security.catalog.dir`）に指定してください。

finding は判定ではなく**事前チェック**です。各 finding には根拠と信頼度が付きます。呼び出し到達に依存するルールは、経路を追えなかった場合に推測せず、その事実を報告します。

---

## 仕組み

```
ソースツリー ──► extractor-spring ──► architecture-facts.json ──► extractor-be ──► be-plan.json ──► send (MCP) ──► Beyond Entity
                 (JavaParser AST,       (ライブラリ非依存の fact,      (BeMapper, PortMapper,
                  XML, YAML, カタログ)   根拠, 未解決)                  LineageComposer, SecuritySync)
```

- **extractor-core**：fact モデル、fact JSON、セキュリティカタログ。
- **extractor-spring**：モジュール探索、JavaParser AST による Java/XML/YAML 解析、classpath なしの型解決、呼び出しグラフ、guard 解析、セキュリティスキャナー。
- **extractor-be**：fact を BE オブジェクトに対応付け、port とリネージの導出、多段リネージの合成、MCP による差分同期。
- **extractor-cli**：コマンドライン、レポート、解析 run、送信。

設計方針：

- 解析できなかったものは、理由付きの `UNRESOLVED` fact になります。黙って捨てることはしません。
- 呼び出し元のデータを運ばない呼び出し関係は、データリネージとは分けて processor の `call_dependencies` に理由（`handoff`、`no_mapping`、`no_caller_value`）付きで残します。
- 検索キーとしてだけ使われた値（`findById(id)`）は、検索されたオブジェクトへのリネージではありません。検索されたオブジェクトのプロパティは、検索結果からの **handoff** になります。


---

## 制限事項

- リフレクション、動的な bean 登録、実行時に生成される proxy は追跡しません。
- 型はソースからのみ取得します。カタログにないライブラリの型は、中身の分からない型として扱います。
- リネージはオブジェクト port の中へ 1 段階（`creditCard.cardNumber`）まで進みます。さらに深く読んだ値（`request.getA().getB().getC()`）は最も近い port に対応付けられます。同じ側の port と同名の入れ子フィールドは BE で曖昧になるため入れ子にしません。
- RabbitMQ のトポロジーは `@Bean` の Exchange/Queue/Binding 定義から読みます。他の場所（設定ファイル、管理画面）で宣言されたトポロジーは読みません。
- Kotlin、Groovy、Spring 以外のフレームワークは解析しません。

---

## パッケージの構成

```
bin/be-parser                     起動スクリプト (macOS, Linux)
bin/be-parser.cmd                 起動スクリプト (Windows)
lib/be-extractor.jar              プログラム
install.sh                        任意：be-parser を PATH に登録（既定 ~/.local）
be-extractor.example.properties   すべての設定の設定ファイル例
README.md, README_ko.md, README_ja.md, INSTALL.md, SECURITY.md
```

脆弱性の報告は [SECURITY.md](SECURITY.md) を参照してください。
