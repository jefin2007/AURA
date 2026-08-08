from brain.database import create_memory_table
import config
from brain.commands import process
from brain.commands import UNKNOWN_COMMAND, process_deterministic
from brain.ai.gemini_adapter import GeminiAdapter, GeminiUnavailableError
from brain.ai.orchestrator import run
create_memory_table()
print()
print("=" * 60)

try:
    gemini = GeminiAdapter()
except GeminiUnavailableError:
    gemini = None
print(f"{config.AI_NAME} | {config.FULL_NAME}")
print(f"Version: {config.VERSION}")
print(config.GREETING)
print("Type 'help' to see available commands. Type 'exit' to quit.")
print("=" * 60)

while True:

    command = input("\nYou : ")

    if command.lower() == "exit":
        print(f"\n{config.AI_NAME}: Goodbye, {config.OWNER}.")
        break

    response = process_deterministic(command)
    if response is UNKNOWN_COMMAND:
        if gemini is None:
            response = "AI brain is unavailable. Deterministic commands are still working."
        else:
            try:
                response = run(command, gemini)
            except GeminiUnavailableError:
                response = "AI brain is unavailable right now. Deterministic commands are still working."

    print(f"\n{config.AI_NAME}: {response}")
