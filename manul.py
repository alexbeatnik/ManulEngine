# manul.py
import asyncio, os, sys, importlib.util

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

class Logger:
    def __init__(self, filename):
        self.terminal, self.log = sys.stdout, open(filename, "w", encoding="utf-8")
    def write(self, message):
        self.terminal.write(message); self.log.write(message)
    def flush(self):
        self.terminal.flush(); self.log.flush()

async def run_test_file(file_path):
    print(f"\n{'='*50}\n🐾 EXECUTING: {os.path.basename(file_path)}\n{'='*50}")
    try:
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        # 🔥 ПРЯМЕ ОТРИМАННЯ РЕЗУЛЬТАТУ
        result = await test_module.main()
        return result 
    except Exception as e:
        print(f"\n❌ ERROR: {e}"); return False

async def main():
    sys.stdout = Logger("last_run.log")
    test_dir = "tests"
    
    # 🚀 НОВА ЛОГІКА: Перевіряємо, чи передано ім'я файлу при запуску
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        # Якщо користувач ввів просто "mega_hunt.py" замість "tests/mega_hunt.py"
        if not target_file.startswith(test_dir) and not os.path.isabs(target_file):
            target_file = os.path.join(test_dir, target_file)
        
        if not os.path.exists(target_file):
            print(f"❌ File not found: {target_file}")
            return
            
        files_to_run = [target_file]
    else:
        # Якщо нічого не передали - шукаємо всі файли hunt_*.py
        files_to_run = sorted([os.path.join(test_dir, f) for f in os.listdir(test_dir) if f.startswith('hunt_') and f.endswith('.py')])
    
    print(f"🚀 Manul CLI: Found {len(files_to_run)} tests.")
    results = []
    for f in files_to_run:
        success = await run_test_file(f)
        results.append((os.path.basename(f), "PASS" if success else "FAIL"))

    print(f"\n\n{'='*20} SUMMARY {'='*20}")
    for file, status in results:
        print(f"{'✅' if status == 'PASS' else '❌'} {file.ljust(30)} {status}")
    print('='*49)

if __name__ == "__main__":
    asyncio.run(main())