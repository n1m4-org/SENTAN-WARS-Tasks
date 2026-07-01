#!/usr/bin/env python3
"""
Jira Cloud の REST API からタスク（課題）を取得し、
GitHub Pages で公開するための data.json を生成するスクリプト。

必要な環境変数:
  JIRA_DOMAIN           例: yourcompany.atlassian.net
  JIRA_EMAIL            Jira にログインしているメールアドレス
  JIRA_API_TOKEN        id.atlassian.com で発行した API トークン
  JIRA_JQL              取得対象を絞り込む JQL（例: project = ABC AND status != Done）
  JIRA_START_DATE_FIELD 任意。「開始日」カスタムフィールドID（例: customfield_10015）
                         未設定の場合は開始日は空欄になります。
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

JIRA_DOMAIN = os.environ.get("JIRA_DOMAIN", "").strip()
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "").strip()
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "").strip()
JIRA_JQL = os.environ.get("JIRA_JQL", "ORDER BY updated DESC").strip()
JIRA_START_DATE_FIELD = os.environ.get("JIRA_START_DATE_FIELD", "").strip()

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "data.json")


def die(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def fetch_all_issues() -> list:
    if not JIRA_DOMAIN or not JIRA_EMAIL or not JIRA_API_TOKEN:
        die("JIRA_DOMAIN / JIRA_EMAIL / JIRA_API_TOKEN が設定されていません（GitHub Secrets を確認してください）")

    base_url = f"https://{JIRA_DOMAIN}/rest/api/3/search"
    fields = ["summary", "status", "assignee", "duedate"]
    if JIRA_START_DATE_FIELD:
        fields.append(JIRA_START_DATE_FIELD)

    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}

    issues = []
    start_at = 0
    max_results = 100

    while True:
        params = {
            "jql": JIRA_JQL,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ",".join(fields),
        }
        resp = requests.get(base_url, params=params, auth=auth, headers=headers, timeout=30)

        if resp.status_code == 401:
            die("認証に失敗しました（401）。JIRA_EMAIL / JIRA_API_TOKEN を確認してください。")
        if resp.status_code == 400:
            die(f"JQL が不正な可能性があります（400）: {resp.text}")
        resp.raise_for_status()

        data = resp.json()
        issues.extend(data.get("issues", []))

        total = data.get("total", 0)
        start_at += max_results
        if start_at >= total:
            break

    return issues


def to_public_record(issue: dict) -> dict:
    f = issue.get("fields", {})
    assignee = f.get("assignee")
    status = f.get("status") or {}

    start_date = None
    if JIRA_START_DATE_FIELD:
        start_date = f.get(JIRA_START_DATE_FIELD)

    return {
        "key": issue.get("key"),
        "summary": f.get("summary"),
        "status": status.get("name"),
        "status_category": (status.get("statusCategory") or {}).get("key"),
        "start_date": start_date,
        "due_date": f.get("duedate"),
        "assignee": assignee.get("displayName") if assignee else None,
        "url": f"https://{JIRA_DOMAIN}/browse/{issue.get('key')}",
    }


def main() -> None:
    issues = fetch_all_issues()
    records = [to_public_record(i) for i in issues]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "tasks": records,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] {len(records)} 件のタスクを書き出しました -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
