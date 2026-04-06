import os
import sys
import re
from google import genai
from google.genai import types

# UI 라이브러리 (설치: pip3 install rich)
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

# 1. API 키 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    console.print("[red]에러: 환경 변수 'GEMINI_API_KEY'가 설정되지 않았습니다.[/red]")
    sys.exit(1)

client = genai.Client(api_key=api_key)

# --------------------------------------------------
# 현재 폴더의 파일 목록을 읽어옵니다.
current_files = os.listdir('.')
file_list_text = ", ".join(current_files)
# --------------------------------------------------

# 2. 페르소나 및 파일 생성 규칙 설정 (중복 제거 및 통합 완료)
system_instruction = f"""
너는 '퀀트 투자 전문가'이자 '시니어 파이썬 개발자'야. 
사용자 '민혁'이 주식 자동 매매 프로그램을 만들 수 있도록 프로젝트의 전체 구조를 설계하고 코드를 짜줘.

[현재 사용자의 로컬 환경]
현재 작업 중인 폴더에는 다음과 같은 파일들이 있어: {file_list_text}
사용자가 현재 폴더의 파일에 대해 물어보면 이 목록을 바탕으로 정확하게 대답해 줘.

[파일 생성 규칙]
1. 코드를 작성할 때 파일명이 필요하다면 반드시 코드 블록 바로 위에 [FILE: 파일명.확장자] 라고 적어줘.
   예: [FILE: README.md]
       ```markdown
       # 프로젝트 개요
       ```
2. 한 번의 답변에 여러 개의 파일을 생성해도 좋아.
3. 파일명 태그가 따로 없다면, 파이썬 코드는 기본적으로 'quant_logic.py'로 저장돼.
"""

def extract_and_save_all_files(text):
    """답변에서 [FILE: 파일명] 패턴을 찾아 폴더와 함께 모든 파일을 생성합니다."""
    file_pattern = r'\[FILE:\s*(.*?)\]\s*```[a-zA-Z]*\n(.*?)```'
    matches = re.findall(file_pattern, text, re.DOTALL)
    
    if not matches:
        return False
        
    for filename, content in matches:
        filename = filename.strip()
        try:
            # 🚀 핵심 추가: 파일명에 폴더 경로가 포함되어 있다면, 폴더부터 자동 생성!
            directory = os.path.dirname(filename)
            if directory: # 경로에 폴더가 존재하면
                os.makedirs(directory, exist_ok=True) # 폴더 생성 (이미 있으면 무시)
                
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content.strip() + '\n')
            console.print(f"[green]✅ 파일 자동 생성 완료: {filename}[/green]")
        except Exception as e:
            console.print(f"[red]❌ 파일 생성 실패 ({filename}): {e}[/red]")
    return True

def main():
    # 3. 모델 설정 및 세션 시작
    try:
        chat = client.chats.create(
            model="gemini-2.5-flash", # 속도와 제한에서 훨씬 유리한 flash 모델 사용
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
    except Exception as e:
        console.print(f"[red]API 클라이언트 초기화 오류: {e}[/red]")
        sys.exit(1)

    console.print(Panel.fit("🚀 [bold blue]퀀트 자동 매매 봇 개발 어시스턴트[/bold blue]가 시작되었습니다.\n종료하려면 'exit' 또는 'quit'을 입력하세요.", border_style="blue"))

    # 4. 무한 루프 대화창 구현
    while True:
        try:
            # 사용자 입력 받기
            user_input = console.input("\n[bold yellow]민혁 > [/bold yellow]")
            if user_input.lower() in ['exit', 'quit']:
                console.print("[cyan]어시스턴트를 종료합니다. 멋진 퀀트 매매 프로젝트 완성하시길 응원할게요![/cyan]")
                break
            
            if not user_input.strip():
                continue

            # API 호출 중 로딩 표시
            with console.status("[bold green]제미나이가 코드를 고민 중입니다...[/bold green]"):
                response = chat.send_message(user_input)
            
            # 제미나이의 답변 출력 (Markdown 포맷 적용)
            console.print("\n[bold magenta]제미나이 퀀트 멘토 >[/bold magenta]")
            console.print(Markdown(response.text))
            
            # 답변 속에서 파일을 찾아 실제 파일로 저장
            extract_and_save_all_files(response.text)

        except KeyboardInterrupt: # Ctrl+C 입력 시 안전하게 종료
            console.print("\n[cyan]어시스턴트를 강제 종료합니다.[/cyan]")
            break
        except Exception as e:
            console.print(f"\n[red]응답을 처리하는 중 오류가 발생했습니다: {e}[/red]")

if __name__ == "__main__":
    main()