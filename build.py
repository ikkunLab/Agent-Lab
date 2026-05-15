import PyInstaller.__main__
import os

# アプリ名
app_name = "AgentLab"

print(f"--- {app_name} のビルドを開始します ---")

PyInstaller.__main__.run([
    'setup.py',              # メインのエントリポイント
    '--onefile',             # 1つのexeにまとめる
    '--name', app_name,      # 出力ファイル名
    '--console',             # コンソールアプリとして作成
    '--hidden-import', 'a2a', # 動的にインポートされるa2aを含める
    '--collect-all', 'rich', # richライブラリの資産をすべて含める
    '--collect-all', 'questionary',
])

print(f"\n--- ビルド完了! dist/{app_name}.exe が生成されました ---")
