# 🧪 Agent Lab v1.0.0

**Agent Lab** は、Ollamaを利用したマルチエージェント対話シミュレーションおよび挙動テストのためのプラットフォームです。
複数のAIエージェントに詳細なプロファイルと内部状態（Internal States）を定義し、自律的な対話における挙動の観測や、リアルタイムの介入（Intervention）による影響のテストを行うことができます。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Ollama](https://img.shields.io/badge/Ollama-supported-orange.svg)

---

## 🛠 特徴

- **動的内部状態 (Dynamic Internal States)**: 怒り、好奇心、信頼などのパラメータに基づき、エージェントの性格や応答トーンがリアルタイムに変化します。
- **行動制約エンジン (Behavioral Constraints)**: ローカルLLM特有の反復性を抑制し、常に多角的な視点からの応答を促すための動的制約を注入します。
- **リアルタイム介入テスト (Intervention Testing)**: 
  - **Broadcast**: 全エージェントに共通のコンテキストを注入し、集団の反応を観測します。
  - **Direct Message (DM)**: 特定のエージェントにのみ秘匿情報を伝達し、情報の非対称性が対話構造に与える影響をシミュレートします。
- **統合管理インターフェース**: モデルの管理（Pull/Remove）、Ollamaサーバーの制御（起動/再起動）を一つのコンソールから完結させることができます。
- **エビデンス記録**: セッション全体のログを保存し、セッション終了時にはAIによる自動サマリー生成が可能です。

## ⚙ 動作環境

- **Ollama**: [ollama.com](https://ollama.com/)
- **Python**: 3.10以上
- **推奨モデル**: 
  - 汎用・高性能: `elyza-llama3-8b`, `qwen2:7b`
  - 低リソース環境: `gemma2:2b`, `llama3.2:3b`

## 🚀 セットアップ

### 1. インストール
```bash
git clone https://github.com/ikkundayo/AgentLab.git
cd AgentLab
pip install -r requirements.txt
```

### 2. 実行
Windows環境では `AgentLab.bat` で直接起動可能です。
```bash
python setup.py
```

### 3. シミュレーションの開始
セットアップメニューの `0` でサーバーの状態を確認し、`4` でインターアクション・テストベッドを起動します。

## 🏗 バイナリビルド (Standalone EXE)

Python環境がないユーザー向け、またはソースコードを秘匿した状態で配布したい場合は、以下の手順でスタンドアロンの実行ファイル（.exe）を生成できます。

1. ビルドスクリプトを実行：
   ```bash
   python build.py
   ```
2. 生成されたファイルを確認：
   `dist/AgentLab.exe` が生成されます。

この実行ファイルは、内部に全ての依存関係と `a2a.py` のロジックを含んでおり、単体での配布・実行が可能です。

## 📄 ライセンス
[MIT License](LICENSE) - Copyright (c) 2026 ikkundayo

---
Developed by **ikkunLab** 🧪🔬
