# Jira タスク一覧 公開ボード（GitHub Pages）

Jira のタスクを1時間ごとに自動取得し、GitHub Pages で静的に公開するための一式です。
表示項目：タスク名 / ステータス / 開始日 / 期限 / 担当者

## 仕組み

```
GitHub Actions（1時間ごと）
  → Jira REST API から課題を取得
  → docs/data.json を更新してコミット
  → GitHub Pages が docs/ を静的公開
  → 閲覧者のブラウザが data.json を読み込んで表示（Jiraには直接アクセスしない）
```

Jira の API トークンはブラウザ側には一切渡らず、GitHub Actions の実行環境内でのみ使われます。

## セットアップ手順

### 1. このフォルダの中身をリポジトリにpush

パブリックリポジトリとして作成してください（GitHub Pagesが無料で使えます）。

以下のコマンドはWindows / Mac / Linux共通です（[Git for Windows](https://gitforwindows.org/)導入済みが前提。コマンドプロンプト・PowerShell・Git Bashのいずれからでも実行できます）。

```bash
git init
git add .
git commit -m "init: jira public status board"
git branch -M main
git remote add origin https://github.com/<あなたのアカウント>/<リポジトリ名>.git
git push -u origin main
```

> GitHub Desktop（GUIアプリ）を使う場合は、このフォルダを「Add local repository」で読み込み、コミット→Publish repositoryを押すだけでも同じことができます。コマンド操作が苦手な場合はこちらがおすすめです。

### 2. Jira の API トークンを発行

1. https://id.atlassian.com/manage-profile/security/api-tokens にアクセス
2. 「APIトークンを作成」→ ラベルを付けて発行（例: `public-status-board`）
3. 表示されたトークンをコピー（この画面を閉じると二度と表示されません）

**推奨：** 全プロジェクトが見える自分のアカウントではなく、公開したいプロジェクトだけ閲覧権限を持つ専用の「閲覧用アカウント」を作り、そのアカウントでトークンを発行すると安全です。

### 3. GitHub Secrets に登録

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** から、以下を1つずつ登録します。

| Secret名 | 内容 | 例 |
|---|---|---|
| `JIRA_DOMAIN` | Jiraサイトのドメイン | `yourcompany.atlassian.net` |
| `JIRA_EMAIL` | トークンを発行したアカウントのメール | `bot@yourcompany.com` |
| `JIRA_API_TOKEN` | 手順2で発行したトークン | `ATATT3xFfGF0...` |
| `JIRA_JQL` | 公開したいタスクを絞り込むJQL | `project = ABC ORDER BY updated DESC` |
| `JIRA_START_DATE_FIELD` | （任意）「開始日」カスタムフィールドID | `customfield_10015` |

**JQLの例：**
- 特定プロジェクトの未完了タスクのみ：`project = ABC AND statusCategory != Done ORDER BY updated DESC`
- 特定ボードのタスクのみ：`project = ABC AND sprint in openSprints() ORDER BY updated DESC`

⚠️ ここで指定したJQLに一致するタスクの「タスク名・ステータス・開始日・期限・担当者名」はすべて**インターネット上に公開**されます。社外秘の情報を含むタスクが混ざらないよう、JQLで対象プロジェクト・条件を明確に絞り込んでください。

### 4. 「開始日」カスタムフィールドIDを調べる（該当する場合）

Jiraの「開始日」は多くの場合カスタムフィールドで、サイトごとにIDが異なります。調べ方の一例：

**Mac / Linux / Git Bash の場合：**

```bash
curl -u your-email@example.com:YOUR_API_TOKEN \
  "https://yourcompany.atlassian.net/rest/api/3/issue/ABC-1?fields=*all" \
  | python3 -m json.tool | grep -i "start date" -B5
```

**Windows（PowerShell）の場合：**

コマンドプロンプトではなく **PowerShell** を使ってください（スタートメニューで「PowerShell」を検索）。

```powershell
$cred = "your-email@example.com:YOUR_API_TOKEN"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($cred)
$b64 = [System.Convert]::ToBase64String($bytes)

$response = Invoke-RestMethod -Uri "https://yourcompany.atlassian.net/rest/api/3/issue/ABC-1?fields=*all" `
  -Headers @{ Authorization = "Basic $b64" }

$response.names.PSObject.Properties | Where-Object { $_.Value -like "*Start date*" }
```

実行結果に `customfield_10015` のようなキーが表示されます。それが探しているフィールドIDです。

どちらの方法でも、`ABC-1` の部分は実際に存在する課題キー（例：自分のプロジェクトの課題番号）に置き換えてください。出てきた `customfield_XXXXX` を `JIRA_START_DATE_FIELD` に設定してください。見つからない場合は空欄のままでOKです（開始日列は「—」表示になります）。

### 5. GitHub Pages を有効化

リポジトリの **Settings → Pages** で、

- Source: `Deploy from a branch`
- Branch: `main` / フォルダ: `/docs`

を選択して保存します。数分後、`https://<あなたのアカウント>.github.io/<リポジトリ名>/` で公開されます。

### 6. 動作確認

**Actions** タブ → `Update Jira Task List` ワークフロー → **Run workflow** で手動実行し、`docs/data.json` が更新されてコミットされることを確認してください。以降は1時間ごとに自動実行されます。

## 更新頻度を変える場合

`.github/workflows/update-jira-tasks.yml` の `cron` を編集してください（UTC基準です）。

```yaml
schedule:
  - cron: "0 * * * *"   # 毎時0分（1時間ごと）
  # - cron: "*/30 * * * *"  # 30分ごと
  # - cron: "0 0 * * *"     # 1日1回（UTC 0時 = JST 9時）
```

## 公開範囲を絞りたくなったら

現状の構成はプロジェクト全体をJQLで絞り込む方式です。ユーザー・チーム単位で細かく出し分けたい場合は、`fetch_jira.py` を複数JQL対応に拡張し、`docs/team-a.json` のように出力先を分けることも可能です。
