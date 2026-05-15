import asyncio
import httpx
import json
import sys
import datetime
import os
from typing import List, Dict
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.layout import Layout
from rich.text import Text
from rich.markdown import Markdown
from rich.theme import Theme
from rich.rule import Rule

# デザインテーマの設定
custom_theme = Theme({
    "agent_a": "bold cyan",
    "agent_b": "bold magenta",
    "system": "italic grey50",
    "topic": "bold yellow",
})

console = Console(theme=custom_theme)

def clear_screen():
    """OS標準のクリアコマンドで画面を完全にリセットする"""
    os.system('cls' if os.name == 'nt' else 'clear')

OLLAMA_URL = "http://localhost:11434/api/chat"

class Agent:
    def __init__(self, name: str, system_prompt: str, style: str, model: str, temperature: float = 0.8):
        self.name = name
        self.system_prompt = system_prompt
        self.style = style
        self.model = model
        self.temperature = temperature
        # 感情パラメータ (0.0 ~ 1.0)
        self.emotions = {
            "anger": 0.0,
            "curiosity": 0.8,
            "trust": 0.5
        }
        self.history: List[Dict[str, str]] = []
        self._update_system_prompt()

    def _update_system_prompt(self):
        # 感情を反映したシステムプロンプトの構築
        emotion_desc = f"\n現在の感情状態: 怒り:{self.emotions['anger']:.1f}, 好奇心:{self.emotions['curiosity']:.1f}, 信頼:{self.emotions['trust']:.1f}"
        
        # メタ発言や一人二役を徹底的に禁止する指示
        base_constraints = (
            f"\n\n--- 鉄の掟 ---\n"
            f"- あなたは {self.name} としてのみ発言してください。\n"
            f"- 絶対に一人二役（相手のセリフを勝手に書くこと）をしないでください。\n"
            f"- 解説、感想、評価（「良い会話ですね」など）は一切不要です。\n"
            f"- {self.name} のセリフのみを、地の文なしで出力してください。\n"
            f"----------------"
        )
        
        full_prompt = f"{self.system_prompt}\n{emotion_desc}{base_constraints}\n感情に合わせた反応を心がけてください。"
        
        # 履歴の先頭がsystemなら更新、なければ挿入
        if self.history and self.history[0]["role"] == "system":
            self.history[0]["content"] = full_prompt
        else:
            if self.system_prompt and self.system_prompt.lower() != "none":
                self.history.insert(0, {"role": "system", "content": full_prompt})

    async def chat(self, message: str, max_tokens: int = 512, dynamic_constraint: str = ""):
        # 動的制約の追加 (ループ防止)
        if dynamic_constraint:
            message += f"\n\n(追加条件: {dynamic_constraint})"
            
        self.history.append({"role": "user", "content": message})
        
        payload = {
            "model": self.model,
            "messages": self.history,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": max_tokens,
                "repeat_penalty": 1.5, # 1.2から1.5に強化
                "repeat_last_n": 256,   # 64から256に拡大（より広い範囲のループを検知）
                "top_p": 0.9,          # 確率の低いトンデモ発言を少しカット
                "presence_penalty": 0.6 # 新しい話題を出すように促す
            }
        }

        full_response = ""
        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream("POST", OLLAMA_URL, json=payload) as response:
                    if response.status_code != 200:
                        console.print(f"[red]Error: Ollama returned {response.status_code}[/red]")
                        return

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data:
                                    chunk = data["message"]["content"]
                                    full_response += chunk
                                    yield chunk
                                if data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                console.print(f"[red]Connection Error: {e}[/red]")
                return
        
        if full_response:
            self.history.append({"role": "assistant", "content": full_response})
            # 感情変動のトリガーチェック
            if "？" in full_response or "?" in full_response:
                self.emotions["curiosity"] = min(1.0, self.emotions["curiosity"] + 0.05)

    def add_memory(self, name: str, content: str):
        """外部（ユーザーや他者）の発言を記憶に追加する"""
        self.history.append({"role": "user", "content": f"[{name}]: {content}"})

import questionary

async def get_local_models():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{OLLAMA_URL.replace('/chat', '')}/tags")
            if response.status_code == 200:
                return [m['name'] for m in response.json().get("models", [])]
        except Exception:
            return []
    return []

async def select_model_interactive(default_model: str):
    models = await get_local_models()
    if not models:
        console.print("[yellow]ローカルモデルが見つかりません。直接入力してください。[/yellow]")
        return Prompt.ask("モデル名を入力", default=default_model)
    
    selected = await questionary.select(
        "使用するモデルを選択してください:",
        choices=models + ["[ 手入力する ]"],
        default=default_model if default_model in models else models[0]
    ).ask_async()
    
    if selected == "[ 手入力する ]":
        return Prompt.ask("モデル名を入力")
    return selected

import random

CONSTRAINTS = [
    "前回とは違う視点を出してください",
    "同じ表現を繰り返さないでください",
    "新しい具体例を1つ含めてください",
    "相手の発言の矛盾を突いてください",
    "より感情的に反応してください",
    "自分の信念を強く主張してください"
]

async def run_a2a():
    clear_screen()
    console.print(Panel.fit("🧪 [bold]Agent Lab[/bold] [dim]Interaction Testbed v1.0.0[/dim]", style="cyan", width=60))

    # システム設定
    console.print("[system]※ エージェント間の動的対話シミュレーションを開始します[/system]")
    
    model_a = Prompt.ask("Agent A のモデル", default="pakachan/elyza-llama3-8b:latest")
    if model_a == ".":
        model_a = await select_model_interactive("pakachan/elyza-llama3-8b:latest")
    name_a = Prompt.ask("Agent A の名前", default="アリス")
    prompt_a = Prompt.ask(f"{name_a} の性格 (空欄で素のAI)", default="あなたは好奇心旺盛な哲学者です。")
    temp_a = FloatPrompt.ask(f"{name_a} の冒険度 (Temperature: 0.0~2.0)", default=0.8)
    
    console.print("")
    model_b = Prompt.ask("Agent B のモデル", default="pakachan/elyza-llama3-8b:latest")
    if model_b == ".":
        model_b = await select_model_interactive("pakachan/elyza-llama3-8b:latest")
    name_b = Prompt.ask("Agent B の名前", default="ボブ")
    prompt_b = Prompt.ask(f"{name_b} の性格 (空欄で素のAI)", default="あなたは論理的で皮肉屋な科学者です。")
    temp_b = FloatPrompt.ask(f"{name_b} の冒険度 (Temperature: 0.0~2.0)", default=0.6)
    
    console.print("")
    topic = Prompt.ask("会話のテーマ", default="AIが意識を持つ可能性について")
    max_turns = IntPrompt.ask("会話の回数 (往復)", default=5)
    
    # ユーザー介入設定
    user_participation = Confirm.ask("あなた（ユーザー）も会話に乱入しますか？", default=False)

    # 詳細設定
    console.print("\n[system]--- 詳細設定 ---[/system]")
    max_tokens = IntPrompt.ask("1回の発言の最大文字数 (目安)", default=1024)
    delay = FloatPrompt.ask("次の人が話すまでの待ち時間 (秒)", default=1.0)

    agent_a = Agent(name_a, prompt_a, "agent_a", model_a, temperature=temp_a)
    agent_b = Agent(name_b, prompt_b, "agent_b", model_b, temperature=temp_b)

    console.print(f"\n[topic]Topic: {topic}[/topic]")
    console.print(f"[system]Session: {name_a} vs {name_b}[/system]")
    if user_participation:
        console.print("[yellow]Intervention Mode: Enabled (Manual injection available)[/yellow]")
    console.print("[system]シミュレーションを開始します...[/system]\n")

    conversation_log = f"Topic: {topic}\n"
    conversation_log += f"Agent A: {name_a} ({model_a}, T={temp_a})\n"
    conversation_log += f"Agent B: {name_b} ({model_b}, T={temp_b})\n\n"

    current_message = f"「{topic}」について、あなたの最初の発言を短く始めてください。解説や挨拶は不要です。"

    for turn in range(1, max_turns + 1):
        # Agent A's Turn
        constraint_a = random.choice(CONSTRAINTS) if turn > 1 else ""
        emotion_str_a = f" [grey50](Status - Anger:{agent_a.emotions['anger']:.1f} Curio:{agent_a.emotions['curiosity']:.1f} Trust:{agent_a.emotions['trust']:.1f})[/grey50]"
        console.print(Rule(f"Turn {turn} - {agent_a.name}{emotion_str_a}", style="cyan"))
        
        response_a = ""
        with Live(Text(style="agent_a"), refresh_per_second=20, vertical_overflow="visible") as live:
            async for chunk in agent_a.chat(current_message, max_tokens=max_tokens, dynamic_constraint=constraint_a):
                response_a += chunk
                live.update(Text(response_a, style="agent_a"))
        
        conversation_log += f"[{agent_a.name}]\n{response_a}\n\n"
        agent_b.add_memory(agent_a.name, response_a)
        current_message = response_a
        
        # 簡易的な感情変動ロジック
        if "？" in response_a or "?" in response_a: agent_b.emotions["curiosity"] = min(1.0, agent_b.emotions["curiosity"] + 0.1)
        agent_a._update_system_prompt()
        await asyncio.sleep(delay)

        # Agent B's Turn
        constraint_b = random.choice(CONSTRAINTS) if turn > 1 else ""
        emotion_str_b = f" [grey50](Status - Anger:{agent_b.emotions['anger']:.1f} Curio:{agent_b.emotions['curiosity']:.1f} Trust:{agent_b.emotions['trust']:.1f})[/grey50]"
        console.print(Rule(f"Turn {turn} - {agent_b.name}{emotion_str_b}", style="magenta"))
        
        response_b = ""
        with Live(Text(style="agent_b"), refresh_per_second=20, vertical_overflow="visible") as live:
            async for chunk in agent_b.chat(current_message, max_tokens=max_tokens, dynamic_constraint=constraint_b):
                response_b += chunk
                live.update(Text(response_b, style="agent_b"))
        
        conversation_log += f"[{agent_b.name}]\n{response_b}\n\n"
        agent_a.add_memory(agent_b.name, response_b)
        current_message = response_b
        
        # 簡易的な感情変動ロジック
        if "違う" in response_b or "ない" in response_b: agent_a.emotions["anger"] = min(1.0, agent_a.emotions["anger"] + 0.1)
        agent_b._update_system_prompt()
        await asyncio.sleep(delay)

        # ユーザー介入 (インターベンション)
        if user_participation and turn < max_turns:
            console.print(Rule("⚙️ Intervention (介入テスト)", style="yellow"))
            action = questionary.select(
                "実行する介入を選択してください:",
                choices=[
                    {"name": "📢 Broadcast (全員への送信)", "value": "all"},
                    {"name": f"🤫 Direct Message (to {agent_a.name})", "value": "dm_a"},
                    {"name": f"🤫 Direct Message (to {agent_b.name})", "value": "dm_b"},
                    {"name": "⏭ スキップ (シミュレーション継続)", "value": "skip"}
                ]
            ).ask_async()
            
            action = await action # questionaryの非同期処理
            
            if action == "all":
                user_input = Prompt.ask("[yellow]天の声を入力[/yellow]")
                if user_input:
                    agent_a.add_memory("User (天の声)", user_input)
                    agent_b.add_memory("User (天の声)", user_input)
                    conversation_log += f"[User (天の声)]\n{user_input}\n\n"
                    current_message = f"User (天の声)から「{user_input}」という言葉がありました。これに反応してください。"
                    console.print(f"[yellow]>>> 二人に「{user_input}」と伝えました。[/yellow]\n")
            
            elif action == "dm_a":
                user_input = Prompt.ask(f"[cyan]{agent_a.name} へのDMを入力[/cyan]")
                if user_input:
                    agent_a.add_memory("User (耳打ち)", user_input)
                    conversation_log += f"[User -> {agent_a.name} (DM)]\n{user_input}\n\n"
                    current_message = f"Userからあなただけに「{user_input}」という耳打ちがありました。相手には内緒でこれに反応してください。"
                    console.print(f"[cyan]>>> {agent_a.name} にだけ伝えました。[/cyan]\n")
                    
            elif action == "dm_b":
                user_input = Prompt.ask(f"[magenta]{agent_b.name} へのDMを入力[/magenta]")
                if user_input:
                    agent_b.add_memory("User (耳打ち)", user_input)
                    conversation_log += f"[User -> {agent_b.name} (DM)]\n{user_input}\n\n"
                    # 次のターンがBならcurrent_messageを更新
                    # (このロジックだと次はAのターンから始まるので、Bが反応するのは1ターン遅れる可能性があるが、
                    #  記憶には入っているので自然な流れで出てくるはず)
                    console.print(f"[magenta]>>> {agent_b.name} にだけ伝えました。[/magenta]\n")

    # 要約機能
    if Confirm.ask("会話を要約しますか？"):
        console.print("[system]要約を作成中...[/system]")
        summary_prompt = "これまでの会話を150文字程度で要約してください。"
        summary = ""
        # Agent Aのコンテキストを使って要約
        async for chunk in agent_a.chat(summary_prompt, max_tokens=512):
            summary += chunk
        
        console.print(Panel(summary, title="要約結果", border_style="green"))
        conversation_log += f"--- 要約 ---\n{summary}\n"

    # ファイル保存
    if Confirm.ask("ログをファイルに保存しますか？"):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(conversation_log)
        console.print(f"[bold green]💾 ログを保存しました: {filename}[/bold green]")

if __name__ == "__main__":
    try:
        asyncio.run(run_a2a())
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]中断されました。終了します。[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]予期せぬエラーが発生しました: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]エラーが発生しました: {e}[/red]")
