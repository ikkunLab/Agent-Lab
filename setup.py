import subprocess
import httpx
import sys
import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

VERSION = "1.0.0"

def clear_screen():
    """OS標準のクリアコマンドで画面を完全にリセットする"""
    os.system('cls' if os.name == 'nt' else 'clear')

def check_for_updates():
    """Gitを使用してアップデートを確認・実行する"""
    console.print("[cyan]アップデートを確認中...[/cyan]")
    try:
        # git fetchして差分があるか確認
        subprocess.run(["git", "fetch"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True)
        
        if "Your branch is behind" in result.stdout:
            if Confirm.ask("[yellow]新しいバージョンが見つかりました！アップデートしますか？[/yellow]"):
                subprocess.run(["git", "pull"], check=True)
                console.print("[bold green]✅ アップデートが完了しました！再起動してください。[/bold green]")
                sys.exit(0)
        else:
            console.print("[green]既に最新バージョンです。[/green]")
    except Exception:
        console.print("[yellow]Gitが見つからないか、リポジトリとして構成されていません。手動で最新版を取得してください。[/yellow]")

OLLAMA_API_BASE = "http://localhost:11434/api"

def check_ollama_installed():
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        return None

async def check_ollama_running():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{OLLAMA_API_BASE}/tags")
            return response.status_code == 200
        except Exception:
            return False

async def get_local_models():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{OLLAMA_API_BASE}/tags")
            if response.status_code == 200:
                return response.json().get("models", [])
        except Exception:
            return []
    return []

async def pull_model(model_name: str):
    console.print(f"[cyan]モデル '{model_name}' をダウンロード中... (時間がかかる場合があります)[/cyan]")
    # Ollamaのpull APIはストリーミングで進捗を返す
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("POST", f"{OLLAMA_API_BASE}/pull", json={"name": model_name}) as response:
                if response.status_code != 200:
                    console.print("[red]ダウンロード開始に失敗しました。[/red]")
                    return

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                ) as progress:
                    task = progress.add_task(f"Pulling {model_name}...", total=None)
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            status = data.get("status", "")
                            progress.update(task, description=f"{model_name}: {status}")
                            if status == "success":
                                break
            console.print(f"[bold green]✅ {model_name} の導入が完了しました！[/bold green]")
        except Exception as e:
            console.print(f"[red]エラーが発生しました: {e}[/red]")

import questionary
import asyncio

async def setup_menu():
    while True:
        clear_screen()
        console.print(Panel.fit(f"🧪 [bold]Agent Lab[/bold] [dim]v{VERSION}[/dim]", style="cyan", width=60))
        
        # ステータスチェック
        version = check_ollama_installed()
        is_running = await check_ollama_running()
        
        status_table = Table(box=None, show_header=False)
        status_table.add_row("Ollama Status:", "[green]Running[/green]" if is_running else "[red]Stopped[/red]")
        status_table.add_row("Ollama Version:", version if version else "[red]Not Found[/red]")
        console.print(status_table)
        console.print("-" * 40)

        # メインメニュー
        console.print("0. [bold green]Ollama サーバーを起動 / 再起動[/bold green]")
        console.print("1. [bold]インストール済みモデル一覧[/bold]")
        console.print("2. [bold]新しいモデルを導入 (Pull)[/bold]")
        console.print("3. [bold]不要なモデルを削除 (Remove)[/bold]")
        console.print("4. [bold cyan]Agent Lab を実行する (a2a.py)[/bold cyan]")
        console.print("5. [bold]Agent Lab をアップデートする (Git)[/bold]")
        console.print("6. [bold]Ollama をアップデートする (ブラウザ)[/bold]")
        console.print("q. 終了")
        
        choice = Prompt.ask("\n選択してください", choices=["0", "1", "2", "3", "4", "5", "6", "q"], default="4")
        
        if choice == "0":
            clear_screen()
            console.print(Panel.fit("🚀 Ollama サーバー起動 / 再起動", style="green"))
            
            if is_running:
                if Confirm.ask("サーバーは実行中です。一度終了して再起動しますか？"):
                    console.print("[yellow]Ollama を終了しています...[/yellow]")
                    # Windowsでプロセスを強制終了
                    subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await asyncio.sleep(2)
            
            console.print("[cyan]Ollama サーバーを起動中...[/cyan]")
            try:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                console.print("[green]起動コマンドを送信しました。数秒待ってから再試行してください。[/green]")
            except Exception as e:
                console.print(f"[red]起動に失敗しました: {e}[/red]")
            Prompt.ask("\nEnterで戻る")

        elif choice == "1":
            clear_screen()
            models = await get_local_models()
            if not models:
                console.print("[yellow]モデルが見つかりません。[/yellow]")
            else:
                table = Table(title="インストール済みモデル")
                table.add_column("Name", style="cyan")
                table.add_column("Size (GB)", justify="right")
                table.add_column("Modified")
                for m in models:
                    size_gb = m.get('size', 0) / (1024**3)
                    table.add_row(m['name'], f"{size_gb:.2f}", m['modified_at'][:10])
                console.print(table)
            Prompt.ask("\nEnterで戻る")
            
        elif choice == "2":
            clear_screen()
            console.print(Panel.fit("📥 新しいモデルを導入 (Pull)", style="cyan"))
            recommends = [
                "pakachan/elyza-llama3-8b:latest (日本語に強い)",
                "phi3:mini (爆速・軽量)",
                "gemma2:9b (Google最新・高性能)",
                "gemma:2b (超軽量)",
                "qwen2:7b (非常に高性能な多言語モデル)",
                "command-r (文脈理解が深い)",
                "llama3 (Meta標準モデル)",
                "mistral (バランス良好)",
                "[ ブラウザで探す ]",
                "[ 手入力する ]",
                "[ 戻る ]"
            ]
            
            selected = await questionary.select(
                "導入したいモデルを選択してください:",
                choices=recommends
            ).ask_async()
            
            if selected == "[ 戻る ]" or selected is None:
                continue
            
            if selected == "[ ブラウザで探す ]":
                import webbrowser
                console.print("[cyan]ブラウザを開いています... https://ollama.com/search[/cyan]")
                webbrowser.open("https://ollama.com/search")
                selected = "[ 手入力する ]"
                
            model_to_pull = ""
            if selected == "[ 手入力する ]":
                model_to_pull = Prompt.ask("導入したいモデル名")
            else:
                model_to_pull = selected.split(" ")[0]
                
            if model_to_pull:
                clear_screen() # ゲージを出す前にもう一度クリア
                await pull_model(model_to_pull)
            Prompt.ask("\nEnterで戻る")

        elif choice == "3":
            clear_screen()
            console.print(Panel.fit("🗑️ 不要なモデルを削除 (Remove)", style="red"))
            models = await get_local_models()
            if not models:
                console.print("[yellow]削除できるモデルがありません。[/yellow]")
                Prompt.ask("Enterで戻る")
                continue
            
            model_names = [m['name'] for m in models]
            selected = await questionary.select(
                "削除するモデルを選択してください (CAUTION!):",
                choices=model_names + ["[ 戻る ]"]
            ).ask_async()
            
            if selected == "[ 戻る ]" or selected is None:
                continue
            
            if Confirm.ask(f"本当に '{selected}' を削除しますか？"):
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.request("DELETE", f"{OLLAMA_API_BASE}/delete", json={"name": selected})
                        if response.status_code == 200:
                            console.print(f"[bold green]✅ {selected} を削除しました。[/bold green]")
                        else:
                            console.print(f"[red]削除に失敗しました: {response.status_code}[/red]")
                    except Exception as e:
                        console.print(f"[red]エラーが発生しました: {e}[/red]")
            Prompt.ask("\nEnterで戻る")
            
        elif choice == "4":
            if not is_running:
                console.print("[red]Ollamaサーバーが起動していません！ 0番で起動するか、手動で立ち上げてください。[/red]")
                Prompt.ask("Enterで戻る")
                continue
            console.print("[green]Agent Lab を起動します...[/green]")
            import a2a
            try:
                asyncio.run(a2a.run_a2a())
            except Exception as e:
                console.print(f"[red]エラーが発生しました: {e}[/red]")
            Prompt.ask("\nEnterで戻る")
            
        elif choice == "5":
            clear_screen()
            console.print(Panel.fit("🆙 Agent Lab アップデート", style="cyan"))
            check_for_updates()
            Prompt.ask("\nEnterで戻る")

        elif choice == "6":
            import webbrowser
            console.print("[cyan]公式サイトを開いています... https://ollama.com/[/cyan]")
            console.print("[cyan]最新のインストーラーをダウンロードして実行すればアップデート完了だよ！[/cyan]")
            webbrowser.open("https://ollama.com/")
            Prompt.ask("\nEnterで戻る")
            
        elif choice == "q":
            break

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(setup_menu())
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]終了します。[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]エラーが発生しました: {e}[/red]")
