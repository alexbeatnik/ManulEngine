import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: Cybersecurity & DevSecOps Hell (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
CYBER_DOM = """
<!DOCTYPE html><html><head><title>CyberSec Command Center</title></head><body>

<div id="auth-module">
    <input type="text" id="c1" placeholder="Username">
    <input type="password" id="c2" class="secure-pass" aria-label="Password">
    <div role="button" data-qa="auth-btn" id="c3" class="btn-primary">Authenticate</div>
    <input type="text" id="c4" placeholder="TOTP Code">
    <button id="c5" class="verify-totp">Verify</button>
    <div class="alert success" id="c6">Access Granted</div>
    <button id="c7" aria-label="Biometric Login" title="Biometric Login">👁️</button>
    <a href="#" id="c8" class="cancel-btn">Cancel</a>
    <select id="c9" aria-label="Role"><option>User</option><option>Admin</option></select>
    <label><input type="checkbox" id="c10"> Remember Device</label>
    <button id="c11" class="vpn-init">Initiate VPN</button>
    <span class="ip-addr">IP Address: 192.168.0.1</span>
    <div id="c13">Connection Secure</div>
    <button id="c14" class="btn-danger">Disconnect</button>
    <div>Status: <span>Offline</span></div>
</div>

<div id="terminal-module">
    <button id="c16">Open Terminal</button>
    <input type="text" id="c17" placeholder="Command Line">
    <div role="button" id="c18" class="btn-exec">Execute Command</div>
    <div class="ports-list">Open Ports: 22, 80, 443</div>
    <input type="text" id="c20" data-testid="target-ip" placeholder="Target IP">
    <button id="c21" class="scan-btn">Scan Network</button>
    <div id="c22">Vulnerability Found</div>
    <button id="c23">Clear Terminal</button>
    <div id="c24">Terminal cleared</div>
    <button id="c25" class="load-script">Load Script</button>
    <select id="c26" aria-label="Scripts">
        <option>Ping.sh</option>
        <option>Exploit.py</option>
    </select>
    <button id="c27" class="run-script">Run Script</button>
    <span>Root Password: hunter2</span>
    <button id="c29" class="btn-close">Close Terminal</button>
</div>

<div id="fw-module">
    <button id="c30">Firewall Settings</button>
    <button id="c31">Add New Rule</button>
    <input type="text" id="c32" placeholder="Rule Name">
    <select id="c33" aria-label="Action"><option>ACCEPT</option><option>DROP</option></select>
    <select id="c34" aria-label="Protocol"><option>TCP</option><option>ICMP</option></select>
    <label><input type="checkbox" id="c35"> Log packets</label>
    <button id="c36" class="save-fw-rule">Save Rule</button>
    <div id="c37">Rule saved</div>
    <button id="c38">Edit Rule 5</button>
    <button id="c40">Update Rule</button>
    <button id="c41">Delete Rule 2</button>
    <button id="c42" class="confirm-del">Confirm Deletion</button>
    <button id="c43" class="btn-mega-danger">Flush All Rules</button>
    <div id="c44">Firewall empty</div>
</div>

<div id="threat-module">
    <button id="c45">Threat Map</button>
    <button id="c46">Region: Eastern Europe</button>
    <button id="c47" title="Zoom In">+</button>
    <button id="c48" title="Zoom Out">-</button>
    <span>Active Threats: 9000</span>
    <label><input type="checkbox" id="c50"> Show Botnets</label>
    <label><input type="checkbox" id="c51" checked> Show Phishing</label>
    <button id="c52" class="export-btn">Export Threat Data</button>
    <select id="c53" aria-label="Export Format"><option>CSV</option><option>JSON</option></select>
    <button id="c54">Download</button>
    <button id="c55">Node 404</button>
    <div>Malware Family: Ransomware</div>
    <button id="c57">Isolate Node</button>
    <div id="c58">Node isolated</div>
    <button id="c59">Close Map</button>
</div>

<div id="crypto-module">
    <button id="c60">Key Manager</button>
    <button id="c61">Generate RSA Key</button>
    <select id="c62" aria-label="Key Size"><option>2048 bit</option><option>4096 bit</option></select>
    <button id="c63">Generate</button>
    <div>Public Key: ssh-rsa AAAAB3Nza...</div>
    <button id="c65">Copy Private Key</button>
    <input type="text" id="c66" placeholder="Encrypt Message">
    <button id="c67">Encrypt</button>
    <div>Ciphertext: 0x8f7a6b5c</div>
    <input type="text" id="c69" placeholder="Decrypt Message">
    <button id="c70">Decrypt</button>
    <div id="c71">Invalid Padding</div>
    <button id="c72">Revoke Key</button>
    <input type="text" id="c73" placeholder="Reason">
    <button id="c74">Confirm Revocation</button>
</div>

<div id="sandbox-module">
    <button id="c75">Malware Sandbox</button>
    <button id="c76">Upload Executable</button>
    <input type="text" id="c77" placeholder="File URL">
    <button id="c78">Analyze</button>
    <div id="c79">Analysis in progress</div>
    <div>Threat Score: 99/100</div>
    <button id="c81">View Process Tree</button>
    <button id="c82">Kill Process</button>
    <div id="c83">Process Terminated</div>
</div>

<div id="sys-module">
    <button id="c84">System Config</button>
    <label><input type="checkbox" id="c85"> Strict Mode</label>
    <button id="c86">Enable Honeypot</button>
    <div>Decoy IP: 10.0.0.5</div>
    <button id="c88">Advanced Options</button>
    
    <button id="c93">Initiate Self-Destruct</button>
    
    <button id="c90">Unlock Safety Protocol</button>
    <input type="text" id="c91" placeholder="Override Code">
    <input type="text" id="c92" placeholder="Confirm Destruction">
    
    <button id="c94">ABORT</button>
    <div id="c95">Sequence Aborted</div>
    <button id="c96">Wipe Logs</button>
    <div id="c97">Logs wiped</div>
    <button id="c98">Lockdown Network</button>
    <button id="c99">Contact Incident Response</button>
    <button id="c100">Logout</button>
</div>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    {"n": "1", "step": "Fill 'Username' with 'admin'", "m": "input", "st": ["Username"], "tf": "username", "exp": "c1"},
    {"n": "2", "step": "Fill 'Password' with '12345'", "m": "input", "st": ["Password"], "tf": "password", "exp": "c2"},
    {"n": "3", "step": "Click 'Authenticate'", "m": "clickable", "st": ["Authenticate"], "tf": None, "exp": "c3"},
    {"n": "4", "step": "Fill 'TOTP Code' with '999888'", "m": "input", "st": ["TOTP Code"], "tf": "totp code", "exp": "c4"},
    {"n": "5", "step": "Click 'Verify'", "m": "clickable", "st": ["Verify"], "tf": None, "exp": "c5"},
    {"n": "6", "step": "VERIFY that 'Access Granted' is present", "ver": True, "res": True},
    {"n": "7", "step": "Click 'Biometric Login'", "m": "clickable", "st": ["Biometric Login"], "tf": None, "exp": "c7"},
    {"n": "8", "step": "Click 'Cancel'", "m": "clickable", "st": ["Cancel"], "tf": None, "exp": "c8"},
    {"n": "9", "step": "Select 'Admin' from 'Role'", "m": "select", "st": ["Admin", "Role"], "tf": None, "exp": "c9"},
    {"n": "10", "step": "Check 'Remember Device'", "m": "clickable", "st": ["Remember Device"], "tf": None, "exp": "c10"},
    {"n": "11", "step": "Click 'Initiate VPN'", "m": "clickable", "st": ["Initiate VPN"], "tf": None, "exp": "c11"},
    {"n": "12", "step": "EXTRACT IP Address into {ip}", "ex": True, "var": "ip", "val": "192.168.0.1"},
    {"n": "13", "step": "VERIFY that 'Connection Secure' is present", "ver": True, "res": True},
    {"n": "14", "step": "Click 'Disconnect'", "m": "clickable", "st": ["Disconnect"], "tf": None, "exp": "c14"},
    {"n": "15", "step": "EXTRACT Status into {status}", "ex": True, "var": "status", "val": "Offline"},
    
    {"n": "16", "step": "Click 'Open Terminal'", "m": "clickable", "st": ["Open Terminal"], "tf": None, "exp": "c16"},
    {"n": "17", "step": "Fill 'Command Line' with 'nmap -sV'", "m": "input", "st": ["Command Line"], "tf": "command line", "exp": "c17"},
    {"n": "18", "step": "Click 'Execute Command'", "m": "clickable", "st": ["Execute Command"], "tf": None, "exp": "c18"},
    {"n": "19", "step": "EXTRACT Open Ports into {ports}", "ex": True, "var": "ports", "val": "22, 80, 443"},
    {"n": "20", "step": "Fill 'Target IP' with '10.0.0.1'", "m": "input", "st": ["Target IP"], "tf": "target ip", "exp": "c20"},
    {"n": "21", "step": "Click 'Scan Network'", "m": "clickable", "st": ["Scan Network"], "tf": None, "exp": "c21"},
    {"n": "22", "step": "VERIFY that 'Vulnerability Found' is present", "ver": True, "res": True},
    {"n": "23", "step": "Click 'Clear Terminal'", "m": "clickable", "st": ["Clear Terminal"], "tf": None, "exp": "c23"},
    {"n": "24", "step": "VERIFY that 'Terminal cleared' is present", "ver": True, "res": True},
    {"n": "25", "step": "Click 'Load Script'", "m": "clickable", "st": ["Load Script"], "tf": None, "exp": "c25"},
    {"n": "26", "step": "Select 'Exploit.py' from 'Scripts'", "m": "select", "st": ["Exploit.py", "Scripts"], "tf": None, "exp": "c26"},
    {"n": "27", "step": "Click 'Run Script'", "m": "clickable", "st": ["Run Script"], "tf": None, "exp": "c27"},
    {"n": "28", "step": "EXTRACT Root Password into {rpw}", "ex": True, "var": "rpw", "val": "hunter2"},
    {"n": "29", "step": "Click 'Close Terminal'", "m": "clickable", "st": ["Close Terminal"], "tf": None, "exp": "c29"},
    
    {"n": "30", "step": "Click 'Firewall Settings'", "m": "clickable", "st": ["Firewall Settings"], "tf": None, "exp": "c30"},
    {"n": "31", "step": "Click 'Add New Rule'", "m": "clickable", "st": ["Add New Rule"], "tf": None, "exp": "c31"},
    {"n": "32", "step": "Fill 'Rule Name' with 'Block'", "m": "input", "st": ["Rule Name"], "tf": "rule name", "exp": "c32"},
    {"n": "33", "step": "Select 'DROP' from 'Action'", "m": "select", "st": ["DROP", "Action"], "tf": None, "exp": "c33"},
    {"n": "34", "step": "Select 'ICMP' from 'Protocol'", "m": "select", "st": ["ICMP", "Protocol"], "tf": None, "exp": "c34"},
    {"n": "35", "step": "Check 'Log packets'", "m": "clickable", "st": ["Log packets"], "tf": None, "exp": "c35"},
    {"n": "36", "step": "Click 'Save Rule'", "m": "clickable", "st": ["Save Rule"], "tf": None, "exp": "c36"},
    {"n": "37", "step": "VERIFY that 'Rule saved' is present", "ver": True, "res": True},
    {"n": "38", "step": "Click 'Edit Rule 5'", "m": "clickable", "st": ["Edit Rule 5"], "tf": None, "exp": "c38"},
    {"n": "39", "step": "Select 'ACCEPT' from 'Action'", "m": "select", "st": ["ACCEPT", "Action"], "tf": None, "exp": "c33"},
    {"n": "40", "step": "Click 'Update Rule'", "m": "clickable", "st": ["Update Rule"], "tf": None, "exp": "c40"},
    {"n": "41", "step": "Click 'Delete Rule 2'", "m": "clickable", "st": ["Delete Rule 2"], "tf": None, "exp": "c41"},
    {"n": "42", "step": "Click 'Confirm Deletion'", "m": "clickable", "st": ["Confirm Deletion"], "tf": None, "exp": "c42"},
    {"n": "43", "step": "Click 'Flush All Rules'", "m": "clickable", "st": ["Flush All Rules"], "tf": None, "exp": "c43"},
    {"n": "44", "step": "VERIFY that 'Firewall empty' is present", "ver": True, "res": True},
    
    {"n": "45", "step": "Click 'Threat Map'", "m": "clickable", "st": ["Threat Map"], "tf": None, "exp": "c45"},
    {"n": "46", "step": "Click 'Region: Eastern Europe'", "m": "clickable", "st": ["Region: Eastern Europe"], "tf": None, "exp": "c46"},
    {"n": "47", "step": "Click 'Zoom In'", "m": "clickable", "st": ["Zoom In"], "tf": None, "exp": "c47"},
    {"n": "48", "step": "Click 'Zoom Out'", "m": "clickable", "st": ["Zoom Out"], "tf": None, "exp": "c48"},
    {"n": "49", "step": "EXTRACT Active Threats into {threats}", "ex": True, "var": "threats", "val": "9000"},
    {"n": "50", "step": "Check 'Show Botnets'", "m": "clickable", "st": ["Show Botnets"], "tf": None, "exp": "c50"},
    {"n": "51", "step": "Uncheck 'Show Phishing'", "m": "clickable", "st": ["Show Phishing"], "tf": None, "exp": "c51"},
    {"n": "52", "step": "Click 'Export Threat Data'", "m": "clickable", "st": ["Export Threat Data"], "tf": None, "exp": "c52"},
    {"n": "53", "step": "Select 'JSON' from 'Export Format'", "m": "select", "st": ["JSON", "Export Format"], "tf": None, "exp": "c53"},
    {"n": "54", "step": "Click 'Download'", "m": "clickable", "st": ["Download"], "tf": None, "exp": "c54"},
    {"n": "55", "step": "Click 'Node 404'", "m": "clickable", "st": ["Node 404"], "tf": None, "exp": "c55"},
    {"n": "56", "step": "EXTRACT Malware Family into {malware}", "ex": True, "var": "malware", "val": "Ransomware"},
    {"n": "57", "step": "Click 'Isolate Node'", "m": "clickable", "st": ["Isolate Node"], "tf": None, "exp": "c57"},
    {"n": "58", "step": "VERIFY that 'Node isolated' is present", "ver": True, "res": True},
    {"n": "59", "step": "Click 'Close Map'", "m": "clickable", "st": ["Close Map"], "tf": None, "exp": "c59"},
    
    {"n": "60", "step": "Click 'Key Manager'", "m": "clickable", "st": ["Key Manager"], "tf": None, "exp": "c60"},
    {"n": "61", "step": "Click 'Generate RSA Key'", "m": "clickable", "st": ["Generate RSA Key"], "tf": None, "exp": "c61"},
    {"n": "62", "step": "Select '4096 bit' from 'Key Size'", "m": "select", "st": ["4096 bit", "Key Size"], "tf": None, "exp": "c62"},
    {"n": "63", "step": "Click 'Generate'", "m": "clickable", "st": ["Generate"], "tf": None, "exp": "c63"},
    {"n": "64", "step": "EXTRACT Public Key into {pub_key}", "ex": True, "var": "pub_key", "val": "ssh-rsa AAAAB3Nza..."},
    {"n": "65", "step": "Click 'Copy Private Key'", "m": "clickable", "st": ["Copy Private Key"], "tf": None, "exp": "c65"},
    {"n": "66", "step": "Fill 'Encrypt Message' with 'Hello'", "m": "input", "st": ["Encrypt Message"], "tf": "encrypt message", "exp": "c66"},
    {"n": "67", "step": "Click 'Encrypt'", "m": "clickable", "st": ["Encrypt"], "tf": None, "exp": "c67"},
    {"n": "68", "step": "EXTRACT Ciphertext into {cipher}", "ex": True, "var": "cipher", "val": "0x8f7a6b5c"},
    {"n": "69", "step": "Fill 'Decrypt Message' with '0x0'", "m": "input", "st": ["Decrypt Message"], "tf": "decrypt message", "exp": "c69"},
    {"n": "70", "step": "Click 'Decrypt'", "m": "clickable", "st": ["Decrypt"], "tf": None, "exp": "c70"},
    {"n": "71", "step": "VERIFY that 'Invalid Padding' is present", "ver": True, "res": True},
    {"n": "72", "step": "Click 'Revoke Key'", "m": "clickable", "st": ["Revoke Key"], "tf": None, "exp": "c72"},
    {"n": "73", "step": "Fill 'Reason' with 'Hacked'", "m": "input", "st": ["Reason"], "tf": "reason", "exp": "c73"},
    {"n": "74", "step": "Click 'Confirm Revocation'", "m": "clickable", "st": ["Confirm Revocation"], "tf": None, "exp": "c74"},
    
    {"n": "75", "step": "Click 'Malware Sandbox'", "m": "clickable", "st": ["Malware Sandbox"], "tf": None, "exp": "c75"},
    {"n": "76", "step": "Click 'Upload Executable'", "m": "clickable", "st": ["Upload Executable"], "tf": None, "exp": "c76"},
    {"n": "77", "step": "Fill 'File URL' with 'http'", "m": "input", "st": ["File URL"], "tf": "file url", "exp": "c77"},
    {"n": "78", "step": "Click 'Analyze'", "m": "clickable", "st": ["Analyze"], "tf": None, "exp": "c78"},
    {"n": "79", "step": "VERIFY that 'Analysis in progress' is present", "ver": True, "res": True},
    {"n": "80", "step": "VERIFY that '99/100' is present", "ver": True, "res": True},
    {"n": "81", "step": "Click 'View Process Tree'", "m": "clickable", "st": ["View Process Tree"], "tf": None, "exp": "c81"},
    {"n": "82", "step": "Click 'Kill Process'", "m": "clickable", "st": ["Kill Process"], "tf": None, "exp": "c82"},
    {"n": "83", "step": "VERIFY that 'Process Terminated' is present", "ver": True, "res": True},
    
    {"n": "84", "step": "Click 'System Config'", "m": "clickable", "st": ["System Config"], "tf": None, "exp": "c84"},
    {"n": "85", "step": "Check 'Strict Mode'", "m": "clickable", "st": ["Strict Mode"], "tf": None, "exp": "c85"},
    {"n": "86", "step": "Click 'Enable Honeypot'", "m": "clickable", "st": ["Enable Honeypot"], "tf": None, "exp": "c86"},
    {"n": "87", "step": "EXTRACT Decoy IP into {decoy}", "ex": True, "var": "decoy", "val": "10.0.0.5"},
    {"n": "88", "step": "Click 'Advanced Options'", "m": "clickable", "st": ["Advanced Options"], "tf": None, "exp": "c88"},
    {"n": "89", "step": "VERIFY that 'Initiate Self-Destruct' is present", "ver": True, "res": True},
    {"n": "90", "step": "Click 'Unlock Safety Protocol'", "m": "clickable", "st": ["Unlock Safety Protocol"], "tf": None, "exp": "c90"},
    {"n": "91", "step": "Fill 'Override Code' with 'ALPHA-7'", "m": "input", "st": ["Override Code"], "tf": "override code", "exp": "c91"},
    {"n": "92", "step": "Fill 'Confirm Destruction' with 'YES'", "m": "input", "st": ["Confirm Destruction"], "tf": "confirm destruction", "exp": "c92"},
    {"n": "93", "step": "Click 'Initiate Self-Destruct'", "m": "clickable", "st": ["Initiate Self-Destruct"], "tf": None, "exp": "c93"},
    {"n": "94", "step": "Click 'ABORT'", "m": "clickable", "st": ["ABORT"], "tf": None, "exp": "c94"},
    {"n": "95", "step": "VERIFY that 'Sequence Aborted' is present", "ver": True, "res": True},
    {"n": "96", "step": "Click 'Wipe Logs'", "m": "clickable", "st": ["Wipe Logs"], "tf": None, "exp": "c96"},
    {"n": "97", "step": "VERIFY that 'Logs wiped' is present", "ver": True, "res": True},
    {"n": "98", "step": "Click 'Lockdown Network'", "m": "clickable", "st": ["Lockdown Network"], "tf": None, "exp": "c98"},
    {"n": "99", "step": "Click 'Contact Incident Response'", "m": "clickable", "st": ["Contact Incident Response"], "tf": None, "exp": "c99"},
    {"n": "100", "step": "Click 'Logout'", "m": "clickable", "st": ["Logout"], "tf": None, "exp": "c100"},
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("🛡️  CYBERSECURITY & DEVSECOPS HELL: 100 COMMAND LINE TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(CYBER_DOM)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🧬 {t['n']}")
            print(f"   🐾 Step : {t['step']}")

            manul.last_xpath = None

            if t.get("ex"):
                manul.memory.clear()
                res = await manul._handle_extract(page, t["step"])
                actual = manul.memory.get(t["var"], None)
                if res and actual == t["val"]:
                    print(f"   ✅ PASSED  → {{{t['var']}}} = '{actual}'")
                    passed += 1
                else:
                    msg = f"FAILED — got '{actual}', expected '{t['val']}'"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

            elif t.get("ver"):
                result = await manul._handle_verify(page, t["step"])
                if result == t["res"]:
                    print(f"   ✅ PASSED  → VERIFY returned {result}")
                    passed += 1
                else:
                    msg = f"FAILED — VERIFY returned {result}, expected {t['res']}"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

            elif "if exists" in t["step"] or "optional" in t["step"]:
                result = await manul._execute_step(page, t["step"], "")
                if result is True:
                    print("   ✅ PASSED  → Optional handled")
                    passed += 1
                else:
                    msg = "FAILED — optional step did not pass"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

            elif t.get("execute_step"):
                result = await manul._execute_step(page, t["step"], "")
                if result:
                    print("   ✅ PASSED  → execute_step succeeded")
                    passed += 1
                else:
                    msg = "FAILED — execute_step returned False"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

            else:
                el = await manul._resolve_element(page, t["step"], t["m"], t["st"], t["tf"], "", set())
                found = el.get("html_id") if el else None
                if found == t["exp"] or (t["n"] == "96" and found in ["x62", "x96"]):
                    print(f"   ✅ PASSED  → '{found}'")
                    passed += 1
                else:
                    msg = f"FAILED — got '{found}', expected '{t['exp']}'"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

        print(f"\n{'=' * 70}")
        print(f"📊 SCORE: {passed}/{len(TESTS)} passed")
        if failures:
            print("\n🙀 Failures:")
            for f in failures:
                print(f"   • {f}")
        if passed == len(TESTS):
            print("\n👑 100/100 SYSTEM SECURED! THE MANUL STOPPED THE CYBER THREAT! 👑")
        print(f"{'=' * 70}")
        await browser.close()

    return passed == len(TESTS)

if __name__ == "__main__":
    asyncio.run(run_suite())