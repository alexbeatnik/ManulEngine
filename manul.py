# manul.py
import asyncio, os, sys, importlib.util

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def flush(self):
        self.terminal.flush()
        self.log.flush()

async def run_test_file(file_path):
    print(f"\n{'='*50}\n🐾 EXECUTING: {os.path.basename(file_path)}\n{'='*50}")
    try:
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        result = await test_module.main()
        return result 
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

async def run_direct_mission(prompt):
    from framework.engine import ManulEngine
    print(f"\n{'='*50}\n🐾 EXECUTING DIRECT HUNT\n{'='*50}")
    print(f"📜 Target: {prompt}")
    
    manul = ManulEngine(headless=False)
    try:
        await manul.run_mission(prompt, keep_open=True)
    except KeyboardInterrupt:
        pass

async def main():
    sys.stdout = Logger("last_run.log")
    test_dir = "tests"
    
    # 🐾 ЛОГІКА CLI 🐾
    if len(sys.argv) > 1:
        target = sys.argv[1]
        
        is_file = target.endswith('.py') or os.path.exists(target) or os.path.exists(os.path.join(test_dir, target))
        
        if is_file:
            if not target.startswith(test_dir) and not os.path.isabs(target):
                target = os.path.join(test_dir, target)
            
            if not os.path.exists(target):
                print(f"❌ File not found: {target}")
                return
            
            files_to_run = [target]
        else:
            await run_direct_mission(target)
            return
    else:
        files_to_run = sorted([os.path.join(test_dir, f) for f in os.listdir(test_dir) if f.startswith('hunt_') and f.endswith('.py')])
    
    print(f"🐱 Manul CLI: Found {len(files_to_run)} targets in hunting grounds.")
    results = []
    for f in files_to_run:
        success = await run_test_file(f)
        results.append((os.path.basename(f), "PASS" if success else "FAIL"))

    print(f"\n\n{'='*20} HUNT SUMMARY {'='*20}")
    for file, status in results:
        print(f"{'✅' if status == 'PASS' else '❌'} {file.ljust(30)} {status}")
    print('='*54)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🐾 Manul returned to the den.")