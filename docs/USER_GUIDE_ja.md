# ユーザーガイド：要件から実装まで

[English](USER_GUIDE.md) · [한국어](USER_GUIDE_ko.md) · [日本語](USER_GUIDE_ja.md)

例と会話の要約：[Databricks](../samples/databricks/README.md) · [Snowflake](../samples/snowflake/README.md) · [比較ガイド（英語）](../samples/COMPARISON.md)。

Beyond Entity をプロジェクト全体の共有 Architecture Memory として使いましょう。システムを説明し、AI エージェントと設計し、データフローをレビューして実装します。コードが変わったら設計も更新し、最新の状態を保ちます。

このガイドでは Databricks と Snowflake の設計例を使い、ERD と実装の例には Table Q を使います。これらは別々のプロジェクトであり、同じプロジェクトの連続した状態ではありません。Web/App アーキテクチャ、API、データベース、ETL/ELT パイプライン、スケジューラーでも同じ手順を使えます。

**始める前に：** [INSTALL.md](../INSTALL.md) に沿ってデスクトップアプリをインストールし、MCP を接続して `architecture-memory` スキルを追加してください。アプリは視覚的な作業画面を提供し、MCP はエージェントによるプロジェクトの読み取り・更新を可能にします。スキルは、そのメモリをどう使って作業するかを案内します。

スクリーンショットは macOS の例です。インストールは自分の環境に合った手順に従ってください。画像をクリックすると元の解像度で開きます。以下の依頼例はコピーし、プロジェクトに合わせて変更できます。ボタンとメニューの名前は、画像内の英語 UI 表記に合わせています。

## 目次

1. [エージェントを接続して確認する](#step-1)
2. [プロジェクトを作成する・開く](#step-2)
3. [システムを説明して AI に設計を依頼する](#step-3)
4. [既存コードから始める](#step-4)
5. [画面で設計をレビューする](#step-5)
6. [Checkpoint と実装状況を確認する](#step-6)
7. [レビュー済みの設計を実装する](#step-7)
8. [コードの変更を Beyond Entity に反映する](#step-8)
9. [別のエージェントやチームメンバーと作業を再開する](#step-9)

<a id="step-1"></a>

## 1. エージェントを接続して確認する

デスクトップアプリの設定で **MCP setup guide** を選びます。[インストールガイド](../INSTALL.md) の Claude Code または Codex の手順に従い、architecture-memory スキルも準備してください。MCP が接続できていても、スキルがインストール済みとは限りません。

画像では接続名が `beyond-entity` で、実行ファイルには macOS のパスが使われています。現在のインストールガイドは `beyond-entity-mcp` と PATH 経由のコマンドを使います。動作している接続があれば、重複して追加せず、その接続を利用してください。

設定後、次のように依頼します。

> Beyond Entity MCP で利用可能なプロジェクトを一覧表示してください。何も変更せず、プロジェクト名と ID を報告してください。

**確認：** 応答に自分のプロジェクトが含まれているか確認します。まだなければ次の手順で作成します。呼び出しが失敗した場合は、接続の問題を解決してから進めてください。

<a href="../assets/screenshots/mcp_setting_codex.png"><img src="../assets/screenshots/mcp_setting_codex.png" alt="Codex の設定依頼とプロジェクト一覧、Beyond Entity の MCP 設定ガイド" width="960"></a>

*Codex の例です。右側の MCP setup guide と左側のプロジェクト一覧の応答を確認してください。*

<details>
<summary>Claude Code の接続例</summary>

<a href="../assets/screenshots/mcp_setting_claude.png"><img src="../assets/screenshots/mcp_setting_claude.png" alt="Claude の接続設定とプロジェクト取得、MCP 設定ガイド" width="960"></a>

*Claude の例です。最新の設定とスキルの導入手順は INSTALL.md を参照してください。*

</details>

<a id="step-2"></a>

## 2. プロジェクトを作成する・開く

エージェントに作成を依頼することも、Beyond Entity で直接作成することもできます。

### エージェントに依頼する

プロジェクト名と、エージェントがアクセスできるフォルダーを指定します。

> [プロジェクトフォルダー] に「Retail Analytics」という新しいローカル Beyond Entity プロジェクトを MCP で作成してください。作成したプロジェクトの名前、ID、ファイルの場所を報告し、初期プロジェクト文書を読んでください。

**確認：** デスクトップアプリのローカルプロジェクト一覧に表示されるか確認します。プロジェクトを開き、名前をエージェントの応答と照合してください。

<a href="../assets/screenshots/project_creation_by_ai.png"><img src="../assets/screenshots/project_creation_by_ai.png" alt="AI が作成した Databricks プロジェクトと Beyond Entity の一覧" width="960"></a>

*左側の作成結果に対応するプロジェクトが右側の一覧に表示されています。その行の Open ボタンで開けます。*

### 自分で作成する

ローカルプロジェクト一覧で **New Platform Project** を選びます。**New Local Project** ダイアログにプロジェクト名、保存場所、ファイル名を入力し、**Create** を選択してください。

既存ファイルは **Select Project File** で選びます。変更前にエージェントに一覧を再取得させ、対象プロジェクトを特定してください。

<a href="../assets/screenshots/project_creation_by_user.png"><img src="../assets/screenshots/project_creation_by_user.png" alt="名前、保存場所、ファイル名、Create ボタンのある新規プロジェクトダイアログ" width="960"></a>

*手動作成には右側のダイアログを参照してください。左側の Databricks の会話は別の例で、右側は Snowflake プロジェクトの作成画面です。*

<a id="step-3"></a>

## 3. システムを説明して AI に設計を依頼する

**DOCUMENT → about_this_system.md** を開き、システムの目的、利用者、業務フロー、ソースシステム、出力、制約を記録します。**Code/Text** で編集して **Save** で保存するか、エージェントに MCP 経由での更新を依頼してください。

セキュリティ境界、障害時の処理、実行頻度、対象範囲に含めない事項など、設計に影響する要件も記載します。

> MCP でこのプロジェクトの文書を読んでください。以下の要件を about_this_system.md に反映し、設計前に不明確な要件を確認して、仮定を明示的に記録してください：[要件]。

<a href="../assets/screenshots/edit_about_this_system_document.png"><img src="../assets/screenshots/edit_about_this_system_document.png" alt="Databricks プロジェクトを説明する About This System 文書" width="960"></a>

*about_this_system.md の目的と業務シナリオを確認してください。右上に Code/Text と Save があります。*

要件が明確になったら、次のように依頼します。

> Beyond Entity をこのプロジェクトの Architecture Memory として使ってください。MCP で最新の文書と設計状態を読み、要件に合ったシステム境界、Entity、データ契約、Processor、Transformation を設計してください。レビュー可能な段階に分け、モデルとアーキテクチャ文書の整合性を保ってください。各マイルストーンで決定事項、確認内容、未解決の質問を Checkpoint に残してください。まだコーディングは開始しないでください。

アプリで直接モデリングし、エージェントに拡張やレビューを依頼しても構いません。続行する前に最新状態を読ませ、自分の編集内容を確認させてください。

<a href="../assets/screenshots/snowflask_start_design.png"><img src="../assets/screenshots/snowflask_start_design.png" alt="AI への設計依頼と Beyond Entity の設計原則文書" width="960"></a>

*この Snowflake の例では、決定事項、データフロー、Transformation をプロジェクトに保存し、マイルストーンを記録するよう依頼しています。*

<a id="step-4"></a>

## 4. 既存コードから始める

実装がすでにある場合は、サービスや業務フローを一つ選び、範囲を絞って始めてください。ソースフォルダーへのアクセスを提供し、更新対象の Beyond Entity プロジェクトを指定します。

> [ソースフォルダー] の [業務フローまたはサービス] を調べてください。MCP で現在の Beyond Entity プロジェクトを読み、このコードに表れているシステム境界、ストレージ Entity、API、Processor、契約、Transformation を記録してください。コードで確認できた事実、推定した意図、未解決の質問を区別し、必要に応じてソースの参照先を残してください。この段階では実装を変更しないでください。

**確認：** 代表的なエンドポイントやジョブを、抽出された設計と比較します。実際の入力、出力、ストレージアクセス、障害時の動作がモデルに含まれているか確認してください。抽出した設計を実装の契約として扱う前に、不確実な点を解消します。

<a id="step-5"></a>

## 5. 画面で設計をレビューする

システム全体から個々の Transformation へと範囲を絞りながら確認します。以下のデスクトップ画像には編集機能も含まれています。公開サンプル Viewer では設計を探索でき、プロジェクトの変更はデスクトップアプリまたは MCP で行います。

### アーキテクチャ全体を見る

**CANVAS → Satellite View** を開くか、すでに開いているタブを選びます。ズームでシステムのグループを見渡せるよう調整し、キャンバスを移動して確認してください。個々の Attribute を追跡する前に、システム名と境界を確認します。

<a href="../assets/screenshots/databricks_review_in_satellite_view.png"><img src="../assets/screenshots/databricks_review_in_satellite_view.png" alt="アプリケーション、ストレージ、Lakehouse の各層、実行制御、分析を示す Databricks Satellite View" width="960"></a>

*Satellite View タブ、システムのグループ、ズーム操作を確認してください。この画面には選択中の Attribute と、それに接続する Lineage も表示されています。*

### 詳細を展開する・折りたたむ

基本モデル画面では、すべての Attribute が初期状態で展開されています。Satellite View とユーザー作成の Canvas は、Entity と Processor の名前を中心としたコンパクトなボックスで始まります。各ボックス右上の展開・折りたたみボタンで Attribute の表示を切り替えます。

確認するオブジェクトだけを展開し、それ以外は折りたたんでおきましょう。折りたたみは表示だけを変更し、設計から Attribute を削除するものではありません。

<a href="../assets/screenshots/snowflask_review_by_satellite_view.png"><img src="../assets/screenshots/snowflask_review_by_satellite_view.png" alt="折りたたまれたボックスと展開された Entity・Processor がある Snowflake Satellite View" width="960"></a>

*下側の折りたたまれた分析ボックスと、上側の展開された Customer Entity を比較してください。各ボックス右上のボタンで表示を変更できます。*

### ERD を確認する

**MODEL** からデータベースモデルを開き、Entity、Attribute、キーのマーカー、関係線を確認します。**Logical / Physical** で業務上の名前と実装上の名前を比較できます。

> このデータベースモデルを要件と照らしてレビューしてください。キーと関係を説明し、欠けている制約や曖昧な所有関係を特定してください。変更を提案する前に MCP で現在のモデルを読んでください。

<a href="../assets/screenshots/database_review_using_erd.png"><img src="../assets/screenshots/database_review_using_erd.png" alt="Entity、キー、関係線、モデルのプロパティを示す Table Q データベースモデル" width="960"></a>

*Table Q の ERD の例です。左側のサイドバーでモデルを選択し、テーブルと関係を確認してください。*

### 検索して Lineage を追跡する

**Search** で `email` などの関連する名前を検索します。**Entity、Processor、または Attribute をクリックすると、接続されたデータフローが表示されます。** 個々の値がシステム内を移動する過程を追う場合は、特定の Attribute を選択してください。

検索は対象を見つける操作で、選択は追跡の基準を決める操作です。

<a href="../assets/screenshots/databricks_review_by%20search.png"><img src="../assets/screenshots/databricks_review_by%20search.png" alt="email の検索後、Raw Customers の Email Attribute を選択して Lineage を表示した画面" width="960"></a>

*検索欄、選択中の Email Attribute、青い接続線、右側の Attribute 詳細を確認してください。*

### Lineage Depth を変更する

右側パネルの **Max Lineage Depth** の横にある **− / +** で、何段階先の接続まで追うかを調整します。Depth を比較する際は、同じオブジェクトを選択したままにしてください。小さい値は近くの接続に集中する場合に、大きい値はアーキテクチャのより遠い範囲を調べる場合に役立ちます。

フローを追いにくい場合は、関連するボックスを展開し、ズームも調整してください。Depth は追跡範囲を、ズームはキャンバスの表示サイズを変更します。

### Processor の Transformation を読む

対象の Processor を選択し、プロパティの **Transformations** を開きます。入力、Lookup/Context、出力 Attribute と合わせて処理ルールを読んでください。Attribute の接続はデータがどこへ移動するかを示し、Transformation はどのように算出・処理するかを説明します。

業務ルール、検証、エラー処理、状態変更、出力契約を確認します。ETL/ELT では変換の実行場所と、読み書きするデータも確認してください。

> MCP でこの Processor と Transformation を読んでください。入力、処理ルール、出力、失敗ケースを説明し、[要件] と比較して実装前に不足している点を特定してください。

<a id="step-6"></a>

## 6. Checkpoint と実装状況を確認する

左側のナビゲーションで **Implementation Status** の領域を開き、**Checkpoints** を選びます。項目を開き、作成者、時刻、メッセージ、当時の状態を確認してください。

有用な Checkpoint は、何をなぜ変更したか、何を検証したか、何が残っているかを説明します。Checkpoint 内の状態は記録時点のスナップショットです。現在の状態は **Implementation Status** と **Test Status** の画面で確認します。

実装状況が記録されているだけでは、実行時テストの合格は証明できません。テストの根拠と、エージェントが説明する制約を併せて確認してください。

<a href="../assets/screenshots/databricks_checkpoint.png"><img src="../assets/screenshots/databricks_checkpoint.png" alt="作成者、時刻、設計段階、実装状況のスナップショットを示す Checkpoint 詳細" width="960"></a>

*この Checkpoint は設計仕様であることを明記し、DESIGNING 状態を示しています。左側の Computer Use の許可要求は撮影時のセッションのもので、Checkpoint 確認に必要な手順ではありません。*

次の例は、その後の実装中に見つかった問題と、解決のための設計変更を記録しています。

<a href="../assets/screenshots/snowflake_checkpoint_2.png"><img src="../assets/screenshots/snowflake_checkpoint_2.png" alt="為替レートの生成フロー追加と取り込み処理の修正を説明する Snowflake Checkpoint" width="960"></a>

*マイルストーン、新しい設計が必要な理由、影響するオブジェクトを読んでください。上部の Changed by MCP と Refresh は、アプリが外部の更新を検出したことを示します。未保存のローカル作業を整理してから Refresh で最新状態を読み込んでください。*

<a id="step-7"></a>

## 7. レビュー済みの設計を実装する

レビュー済みの小さな範囲を選びます。コードの場所と関連設計を指定し、実装前にもう一度読むよう依頼してください。

> レビュー済みの Beyond Entity 設計を使い、[ソースフォルダー] に [業務フロー] を実装してください。まず MCP で最新の Checkpoint、関連 Processor の Transformation、データ契約、依存関係を読んでください。動作を決める前に曖昧な点を説明してください。実装後に適切な確認を行い、その根拠に合わせて実装・テスト状況を更新してください。変更ファイル、検証結果、残る制約を Checkpoint に記録してください。

**結果のレビュー：** コードの入力、出力、ルール、エラー処理を Transformation と比較します。実際に実行したテストと、サービスや環境が利用できず実行できなかったテストを確認してください。更新後に設計を再度読み取って確認するよう依頼します。

以下の進捗メッセージは、エージェントが確認結果を報告し、実行制御の不足を見つけ、Beyond Entity を更新して契約の整合性を確認しようとする例です。作業の進め方を示すもので、ここで結果を独立に検証したわけではありません。

<a href="../assets/screenshots/codex_comment.png"><img src="../assets/screenshots/codex_comment.png" alt="実装検証、実行制御の不足、設計の再確認を説明するエージェントの進捗報告" width="720"></a>

*エージェントの報告から、具体的な設計変更と検証内容を確認してください。*

ソースコードと実行画面を含む実装例は [Table Q by Codex](../samples/table-q/README.md) を参照してください。

<a id="step-8"></a>

## 8. コードの変更を Beyond Entity に反映する

要件やコードが変わったら、アーキテクチャを見直します。コードとの差分をすべて新しい設計ルールに置き換えないでください。差分はバグ、意図した変更、未決定の事項の可能性があります。

> [ファイルまたは Commit] の変更を最新の Beyond Entity 設計と比較してください。差分を、意図した動作変更、実装の不具合、未決定の事項に分類してください。意図した変更は MCP で関連する Transformation、契約、関係、アーキテクチャ文書に反映し、他の人やエージェントによる無関係な編集は保持してください。更新した設計をコードと比較して検証し、理由、確認内容、残る問題を Checkpoint に記録してください。

**確認：** 変更された Transformation と関連 Attribute の流れを確認し、新しい Checkpoint を読みます。更新した状態が実際の検証内容と一致するか確認してください。アプリに **Changed by MCP** が表示されている場合は、最新状態を読み込んでからレビューします。

<a id="step-9"></a>

## 9. 別のエージェントやチームメンバーと作業を再開する

新しい作業セッションは、以前の会話だけに頼らず、現在のコンテキストを復元することから始めてください。

> MCP で [Beyond Entity プロジェクト] を開いてください。最新の Checkpoint、関連文書、[作業] に必要な現在の設計を読んでください。現在のコードと最後の記録以降の変更を確認し、他のエージェントや人による変更も含めてください。編集前に、完了した作業、未解決の差分、次の手順をまとめてください。Checkpoint の情報だけでは変更を判断できない場合は、そのことを伝えてください。

Checkpoint は意図の復元に役立ちますが、現在の設計とコードの確認を代替するものではありません。セッションを終える際は、次の担当者に必要な決定事項と根拠を記録してください。

---

[README に戻る](../README.md) · [インストールガイド](../INSTALL.md) · [サンプルプロジェクト](../samples/README.md)
