import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: Rahul Shetty & Blogspot QA Practice (Legacy HTML Patterns)
# ─────────────────────────────────────────────────────────────────────────────
CLASSICS_DOM = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .tableFixHead { overflow: auto; height: 100px; }
        .tableFixHead thead th { position: sticky; top: 0; }
        .mouse-hover-content { display: none; position: absolute; background-color: #f9f9f9; box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2); }
        .mouse-hover:hover .mouse-hover-content { display: block; }
        #displayed-text { display: block; }
    </style>
</head>
<body>

<h1>Rahul Shetty Academy - Automation Practice</h1>

<div id="radio-btn-example">
    <fieldset>
        <legend>Radio Button Example</legend>
        <label><input value="radio1" name="radioButton" class="radioButton" type="radio" id="rs_rad1"> Radio1</label>
        <label><input value="radio2" name="radioButton" class="radioButton" type="radio" id="rs_rad2"> Radio2</label>
        <label><input value="radio3" name="radioButton" class="radioButton" type="radio" id="rs_rad3"> Radio3</label>
    </fieldset>
</div>

<div id="select-class-example">
    <fieldset>
        <legend>Suggession Class Example</legend>
        <input type="text" id="autocomplete" class="inputs" placeholder="Type to Select Countries">
    </fieldset>
</div>

<div id="dropdown-example">
    <fieldset>
        <legend>Dropdown Example</legend>
        <select id="dropdown-class-example" name="dropdown-class-example">
            <option value="">Select</option>
            <option value="option1">Option1</option>
            <option value="option2">Option2</option>
            <option value="option3">Option3</option>
        </select>
    </fieldset>
</div>

<div id="checkbox-example">
    <fieldset>
        <legend>Checkbox Example</legend>
        <label><input id="checkBoxOption1" value="option1" name="checkBoxOption1" type="checkbox"> Option1</label>
        <label><input id="checkBoxOption2" value="option2" name="checkBoxOption2" type="checkbox"> Option2</label>
        <label><input id="checkBoxOption3" value="option3" name="checkBoxOption3" type="checkbox"> Option3</label>
    </fieldset>
</div>

<div id="alert-example">
    <fieldset>
        <legend>Switch To Alert Example</legend>
        <input id="name" name="enter-name" class="inputs" placeholder="Enter Your Name" type="text">
        <input id="alertbtn" class="btn-style" value="Alert" onclick="alert('Hello')" type="button">
        <input id="confirmbtn" class="btn-style" value="Confirm" onclick="confirm('Are you sure?')" type="button">
    </fieldset>
</div>

<div id="element-displayed-example">
    <fieldset>
        <legend>Element Displayed Example</legend>
        <input id="hide-textbox" class="btn-style class2" value="Hide" onclick="document.getElementById('displayed-text').style.display='none';" type="button">
        <input id="show-textbox" class="btn-style class2" value="Show" onclick="document.getElementById('displayed-text').style.display='block';" type="button">
        <br><br>
        <input id="displayed-text" name="show-hide" class="inputs" placeholder="Hide/Show Example" type="text">
    </fieldset>
</div>

<div class="table-example">
    <fieldset>
        <legend>Web Table Example</legend>
        <table id="product" name="courses" border="1" cellpadding="5">
            <tbody>
                <tr><th>Instructor</th><th>Course</th><th>Price</th></tr>
                <tr><td>Rahul Shetty</td><td>Selenium Webdriver with Java Basics + Advanced</td><td>30</td></tr>
                <tr><td>Rahul Shetty</td><td>Learn SQL in Practical + Database Testing</td><td>25</td></tr>
                <tr><td>Rahul Shetty</td><td>Appium (Selenium) - Mobile Automation</td><td>30</td></tr>
                <tr><td>Rahul Shetty</td><td>Master Selenium Automation in simple Python</td><td>25</td></tr>
            </tbody>
        </table>
    </fieldset>
</div>

<div class="mouse-hover">
    <button id="mousehover" class="btn btn-primary">Mouse Hover</button>
    <div class="mouse-hover-content">
        <a href="#top" id="rs_top">Top</a>
        <a href="" id="rs_reload">Reload</a>
    </div>
</div>

<hr>
<h1>TestAutomationPractice Blogspot</h1>

<div class="widget-content">
    <label for="Wikipedia1_wikipedia-search-input">Wikipedia Search:</label>
    <input class="wikipedia-search-input" id="Wikipedia1_wikipedia-search-input" type="text">
    <input class="wikipedia-search-button" type="button" value="🔍" id="bs_wiki_btn">
</div>

<button id="bs_new_window" onclick="window.open()">New Browser Window</button>

<div class="form-group">
    <label>Date Picker:</label>
    <input type="text" id="datepicker">
</div>

<div class="form-group">
    <label for="speed">Select Speed</label>
    <select name="speed" id="speed">
        <option value="Slow">Slow</option>
        <option value="Medium" selected>Medium</option>
        <option value="Fast">Fast</option>
        <option value="Faster">Faster</option>
    </select>
</div>

<div class="form-group">
    <label for="files">Select a file</label>
    <select name="files" id="files">
        <option value="jquery">jQuery.js</option>
        <option value="ui">ui.jQuery.js</option>
        <option value="somefile">Some unknown file</option>
    </select>
</div>

<div class="form-group">
    <p>Double Click Example</p>
    <button id="bs_dbl_click" ondblclick="document.getElementById('bs_field2').value = document.getElementById('bs_field1').value">Copy Text</button>
    <input type="text" id="bs_field1" value="Hello World">
    <input type="text" id="bs_field2">
</div>

<div class="form-group">
    <p>Drag and Drop</p>
    <div id="draggable" style="width:50px;height:50px;background:gray;">Drag me</div>
    <div id="droppable" style="width:100px;height:100px;border:1px solid black;">Drop here</div>
</div>

<div class="table-container">
    <h2>HTML Table</h2>
    <table name="BookTable" id="BookTable" border="1">
        <tbody>
            <tr><th>BookName</th><th>Author</th><th>Subject</th><th>Price</th></tr>
            <tr><td>Learn Selenium</td><td>Amit</td><td>Selenium</td><td>300</td></tr>
            <tr><td>Learn Java</td><td>Mukesh</td><td>Java</td><td>500</td></tr>
            <tr><td>Master In JS</td><td>Amod</td><td>Javascript</td><td>300</td></tr>
            <tr><td>Master In Python</td><td>Mukesh</td><td>Python</td><td>3000</td></tr>
        </tbody>
    </table>
</div>

</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-30 (Classic QA Challenges)
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── RAHUL SHETTY ACADEMY ──
    {"n": "1", "step": "Click the radio button for 'Radio2'", "m": "clickable", "st": ["Radio2"], "tf": None, "exp": "rs_rad2"},
    {"n": "2", "step": "Fill 'Suggession Class Example' with 'Ukraine'", "m": "input", "st": ["Suggession Class Example"], "tf": "suggession class example", "exp": "autocomplete"},
    {"n": "3", "step": "Select 'Option3' from 'Dropdown Example'", "m": "select", "st": ["Option3", "Dropdown Example"], "tf": None, "exp": "dropdown-class-example"},
    {"n": "4", "step": "Check 'Option1' checkbox", "m": "clickable", "st": ["Option1"], "tf": None, "exp": "checkBoxOption1"},
    {"n": "5", "step": "Check 'Option3' checkbox", "m": "clickable", "st": ["Option3"], "tf": None, "exp": "checkBoxOption3"},
    {"n": "6", "step": "Fill 'Enter Your Name' with 'John Doe'", "m": "input", "st": ["Enter Your Name"], "tf": "enter your name", "exp": "name"},
    {"n": "7", "step": "Click 'Alert' button", "m": "clickable", "st": ["Alert"], "tf": None, "exp": "alertbtn"},
    {"n": "8", "step": "Click 'Confirm' button", "m": "clickable", "st": ["Confirm"], "tf": None, "exp": "confirmbtn"},
    {"n": "9", "step": "Fill 'Hide/Show Example' with 'Magic'", "m": "input", "st": ["Hide/Show Example"], "tf": "hide/show example", "exp": "displayed-text"},
    {"n": "10", "step": "Click 'Hide' button", "m": "clickable", "st": ["Hide"], "tf": None, "exp": "hide-textbox"},
    
    # Table Extraction (Classic <table> without specific data-attributes)
    {"n": "11", "step": "EXTRACT the Price of 'Appium (Selenium)' into {appium_price}", "ex": True, "var": "appium_price", "val": "30"},
    {"n": "12", "step": "EXTRACT the Price of 'Master Selenium Automation in simple Python' into {python_price}", "ex": True, "var": "python_price", "val": "25"},
    {"n": "13", "step": "EXTRACT the Instructor of 'Learn SQL' into {sql_inst}", "ex": True, "var": "sql_inst", "val": "Rahul Shetty"},
    
    # Hover Menus
    {"n": "14", "step": "HOVER over 'Mouse Hover'", "m": "hover", "st": ["Mouse Hover"], "tf": None, "exp": "mousehover", "execute_step": True},
    {"n": "15", "step": "Click 'Top' from hover menu", "m": "clickable", "st": ["Top"], "tf": None, "exp": "rs_top"},
    {"n": "16", "step": "Click 'Reload' from hover menu", "m": "clickable", "st": ["Reload"], "tf": None, "exp": "rs_reload"},

    # ── TEST AUTOMATION PRACTICE BLOGSPOT ──
    {"n": "17", "step": "Fill 'Wikipedia Search' with 'Manul'", "m": "input", "st": ["Wikipedia Search"], "tf": "wikipedia search", "exp": "Wikipedia1_wikipedia-search-input"},
    {"n": "18", "step": "Click the Wikipedia search button (🔍)", "m": "clickable", "st": ["🔍"], "tf": None, "exp": "bs_wiki_btn"},
    {"n": "19", "step": "Click 'New Browser Window'", "m": "clickable", "st": ["New Browser Window"], "tf": None, "exp": "bs_new_window"},
    {"n": "20", "step": "Fill 'Date Picker' with '10/10/2026'", "m": "input", "st": ["Date Picker"], "tf": "date picker", "exp": "datepicker"},
    
    # Legacy Select Menus
    {"n": "21", "step": "Select 'Fast' from 'Select Speed'", "m": "select", "st": ["Fast", "Select Speed"], "tf": None, "exp": "speed"},
    {"n": "22", "step": "Select 'jQuery.js' from 'Select a file'", "m": "select", "st": ["jQuery.js", "Select a file"], "tf": None, "exp": "files"},
    
    # Complex Actions
    {"n": "23", "step": "DOUBLE CLICK 'Copy Text'", "m": "clickable", "st": ["Copy Text"], "tf": None, "exp": "bs_dbl_click"},
    {"n": "24", "step": "Fill 'bs_field1' optional field with 'Override'", "m": "input", "st": ["Hello World"], "tf": None, "exp": "bs_field1"},
    
    # Drag and Drop Targeting
    {"n": "25", "step": "Click 'Drag me'", "m": "clickable", "st": ["Drag me"], "tf": None, "exp": "draggable"},
    {"n": "26", "step": "Click 'Drop here'", "m": "clickable", "st": ["Drop here"], "tf": None, "exp": "droppable"},
    
    # Blogspot Table Extraction
    {"n": "27", "step": "EXTRACT the Author of 'Learn Selenium' into {sel_auth}", "ex": True, "var": "sel_auth", "val": "Amit"},
    {"n": "28", "step": "EXTRACT the Price of 'Master In Java' into {java_price}", "ex": True, "var": "java_price", "val": "500"}, # Testing if it finds 'Learn Java' dynamically
    {"n": "29", "step": "EXTRACT the Subject of 'Master In Python' into {py_subj}", "ex": True, "var": "py_subj", "val": "Python"},
    
    # Verify Legacy UI
    {"n": "30", "step": "VERIFY that 'Radio Button Example' is present", "ver": True, "res": True},
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("🎓 QA CLASSICS HELL: 30 LEGACY HTML TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Автоматично закривати алерти, як це робить Playwright за замовчуванням
        ctx  = await browser.new_context()
        page = await ctx.new_page()
        page.on("dialog", lambda dialog: dialog.accept()) # Перехоплювач алертів!
        
        await page.set_content(CLASSICS_DOM)

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
                if found == t["exp"]:
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
            print("\n🏆 FLAWLESS VICTORY! Manul mastered the QA Classics! 🏆")
        print(f"{'=' * 70}")
        await browser.close()

    return passed == len(TESTS)

if __name__ == "__main__":
    asyncio.run(run_suite())