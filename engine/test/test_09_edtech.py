import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: EdTech & E-Learning (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
EDTECH_DOM = """
<!DOCTYPE html><html><head><style>
.quiz-option { margin-bottom: 10px; }
.code-editor { font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 10px; width: 100%; height: 100px; }
.hidden { display: none; }
</style></head><body>

<div class="catalog">
    <input type="search" id="l1" placeholder="Search courses, skills, and videos">
    <select id="l2" aria-label="Category"><option>Computer Science</option><option>Data Science</option></select>
    <button id="l3" class="btn-enroll">Enroll for Free</button>
    <a href="/syllabus" id="l4">View Syllabus</a>
    <button id="l5" aria-label="Bookmark Course">🔖</button>
    <fieldset>
        <legend>Level</legend>
        <label><input type="radio" name="lvl" id="l6"> Beginner</label>
        <label><input type="radio" name="lvl" id="l7"> Advanced</label>
    </fieldset>
    <button id="l8">Apply Filters</button>
    <button id="l9">Clear All</button>
    <div role="button" id="l10" aria-expanded="false">Instructor Bio ▼</div>
</div>

<div class="lecture-view">
    <button id="l11">Previous Lecture</button>
    <button id="l12" class="next-btn">Next Lecture</button>
    <div role="switch" id="l13" aria-checked="false" aria-label="Auto-advance"></div>
    <button id="l14">Show Transcript</button>
    <button id="l15">Take Notes</button>
    <select id="l16" aria-label="Speed"><option>1x</option><option>2x</option></select>
    <input type="checkbox" id="l17"><label for="l17">Mark as Complete</label>
    <a href="/dl/slides.pdf" id="l18">Download Slides</a>
    <button id="l19">Ask Question in Q&A</button>
    <button id="l20" style="color:red;">Report Audio Issue</button>
</div>

<div class="quiz-container">
    <h3>Question 1: What is Python?</h3>
    <div class="quiz-option"><input type="radio" name="q1" id="l21"><label for="l21">A snake</label></div>
    <div class="quiz-option"><input type="radio" name="q1" id="l22"><label for="l22">A programming language</label></div>
    
    <h3>Question 2: Select valid HTML tags</h3>
    <div class="quiz-option"><input type="checkbox" id="l23"><label for="l23">div</label></div>
    <div class="quiz-option"><input type="checkbox" id="l24"><label for="l24">span</label></div>
    <div class="quiz-option"><input type="checkbox" id="l25"><label for="l25">fakeTag</label></div>

    <button id="l26">Clear my choices</button>
    <button id="l27" class="btn-submit">Submit Quiz</button>
    <button id="l28" disabled>Review Answers</button>
    <div id="l29" class="quiz-score">Score: 85%</div>
    <button id="l30">Retake Quiz</button>
</div>

<div class="interactive-exercise">
    <p>Fill in the blank: <input type="text" id="l31" placeholder="def" style="width:50px;">():</p>
    <textarea id="l32" class="code-editor" aria-label="Code Editor">print("Hello")</textarea>
    <button id="l33">Run Code</button>
    <button id="l34" class="btn-success">Submit Code</button>
    <div id="l35" class="console-output">SyntaxError: invalid syntax</div>
    <button id="l36" aria-label="Show Hint 1">💡 Hint</button>
    <button id="l37">View Solution</button>
    <div role="button" id="l38">Reset Workspace</div>
    <input type="file" id="l39" aria-label="Upload Source File">
    <select id="l40" aria-label="Language"><option>Python 3</option><option>Java</option></select>
</div>

<div class="forum">
    <input type="text" id="l41" placeholder="Search discussions...">
    <button id="l42">Create New Thread</button>
    <input type="text" id="l43" placeholder="Thread Title">
    <textarea id="l44" placeholder="Type your question here..."></textarea>
    <button id="l45">Post Thread</button>
    <button id="l46" aria-label="Upvote Post">⬆</button>
    <button id="l47" aria-label="Downvote Post">⬇</button>
    <button id="l48">Reply to Thread</button>
    <button id="l49">Mark as Answer</button>
    <button id="l50">Subscribe to updates</button>
</div>

<div class="assignment">
    <h2 id="l51">Final Project: Web Scraper</h2>
    <input type="file" id="l52" aria-label="Upload Assignment">
    <input type="url" id="l53" placeholder="Paste Google Drive Link">
    <textarea id="l54" placeholder="Add comments for grader"></textarea>
    <input type="checkbox" id="l55"><label for="l55">I agree to the Honor Code</label>
    <button id="l56" class="btn-primary">Submit Assignment</button>
    <button id="l57">Withdraw Submission</button>
    <div role="button" id="l58">View Grading Rubric</div>
    <button id="l59">Request Extension</button>
    <div id="l60" class="status-badge">Status: Not Submitted</div>
</div>

<div class="grades-dashboard">
    <div id="l61" class="final-grade">Final Grade: A-</div>
    <button id="l62">Download Transcript</button>
    <div id="l63" class="progress-text">Course Progress: 75%</div>
    <button id="l64">Request Regrade</button>
    <select id="l65" aria-label="Semester"><option>Fall 2025</option><option>Spring 2026</option></select>
    <div id="l66">GPA: 3.8</div>
    <button id="l67">Share Grades</button>
    <div role="button" id="l68">View Weighting</div>
    <input type="text" id="l69" placeholder="Enter target grade to calculate needed score">
    <button id="l70">Calculate</button>
</div>

<div class="peer-review">
    <button id="l71">Start Reviewing</button>
    <select id="l72" aria-label="Criterion 1 Score"><option>0</option><option>5</option><option>10</option></select>
    <select id="l73" aria-label="Criterion 2 Score"><option>0</option><option>5</option><option>10</option></select>
    <textarea id="l74" placeholder="Constructive Feedback"></textarea>
    <button id="l75">Submit Review</button>
    <button id="l76" style="color:red;">Flag for Plagiarism</button>
    <button id="l77">Save Draft Review</button>
    <div role="button" id="l78">View Student Submission</div>
    <div role="button" id="l79">Show Rubric Guidelines</div>
    <button id="l80" disabled>Next Submission</button>
</div>

<div class="instructor-tools">
    <button id="l81">Create New Course</button>
    <button id="l82">Edit Syllabus</button>
    <button id="l83">Post Announcement</button>
    <input type="text" id="l84" placeholder="Message to Students">
    <button id="l85">Send Message</button>
    <a href="/gradebook" id="l86">Open Gradebook</a>
    <button id="l87" class="publish-btn">Publish Grades</button>
    <button id="l88">Export Analytics</button>
    <div role="switch" id="l89" aria-checked="true" aria-label="Accepting Enrollments"></div>
    <button id="l90" style="color:darkred;">Unpublish Course</button>
</div>

<div class="gamification">
    <button id="l91" class="pulse">Claim Daily Reward</button>
    <div id="l92">Current Streak: 14 Days</div>
    <button id="l93">View Certificate</button>
    <button id="l94">Share to LinkedIn</button>
    <button id="l95">Download PDF Certificate</button>
    <div id="l96">Rank: #4 in Class</div>
    <button id="l97" aria-label="View Leaderboard">🏆</button>
    <button id="l98">Equip Avatar Frame</button>
    <button id="l99">Spend XP Points</button>
    <button id="l100" style="display:none;">Secret Dev Mode</button>
</div>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Catalog
    {"n": "1", "step": "Fill 'Search courses' with 'Python'", "m": "input", "st": ["Search courses"], "tf": "search courses", "exp": "l1"},
    {"n": "2", "step": "Select 'Data Science' from 'Category'", "m": "select", "st": ["Data Science", "Category"], "tf": None, "exp": "l2"},
    {"n": "3", "step": "Click 'Enroll for Free'", "m": "clickable", "st": ["Enroll for Free"], "tf": None, "exp": "l3"},
    {"n": "4", "step": "Click 'View Syllabus'", "m": "clickable", "st": ["View Syllabus"], "tf": None, "exp": "l4"},
    {"n": "5", "step": "Click 'Bookmark Course'", "m": "clickable", "st": ["Bookmark Course"], "tf": None, "exp": "l5"},
    {"n": "6", "step": "Click radio 'Beginner'", "m": "clickable", "st": ["Beginner"], "tf": None, "exp": "l6"},
    {"n": "7", "step": "Click radio 'Advanced'", "m": "clickable", "st": ["Advanced"], "tf": None, "exp": "l7"},
    {"n": "8", "step": "Click 'Apply Filters'", "m": "clickable", "st": ["Apply Filters"], "tf": None, "exp": "l8"},
    {"n": "9", "step": "Click 'Clear All'", "m": "clickable", "st": ["Clear All"], "tf": None, "exp": "l9"},
    {"n": "10", "step": "Click 'Instructor Bio'", "m": "clickable", "st": ["Instructor Bio"], "tf": None, "exp": "l10"},

    # Lectures
    {"n": "11", "step": "Click 'Previous Lecture'", "m": "clickable", "st": ["Previous Lecture"], "tf": None, "exp": "l11"},
    {"n": "12", "step": "Click 'Next Lecture'", "m": "clickable", "st": ["Next Lecture"], "tf": None, "exp": "l12"},
    {"n": "13", "step": "Click 'Auto-advance' switch", "m": "clickable", "st": ["Auto-advance"], "tf": None, "exp": "l13"},
    {"n": "14", "step": "Click 'Show Transcript'", "m": "clickable", "st": ["Show Transcript"], "tf": None, "exp": "l14"},
    {"n": "15", "step": "Click 'Take Notes'", "m": "clickable", "st": ["Take Notes"], "tf": None, "exp": "l15"},
    {"n": "16", "step": "Select '2x' from 'Speed'", "m": "select", "st": ["2x", "Speed"], "tf": None, "exp": "l16"},
    {"n": "17", "step": "Check 'Mark as Complete'", "m": "clickable", "st": ["Mark as Complete"], "tf": None, "exp": "l17"},
    {"n": "18", "step": "Click 'Download Slides'", "m": "clickable", "st": ["Download Slides"], "tf": None, "exp": "l18"},
    {"n": "19", "step": "Click 'Ask Question in Q&A'", "m": "clickable", "st": ["Ask Question in Q&A"], "tf": None, "exp": "l19"},
    {"n": "20", "step": "Click 'Report Audio Issue'", "m": "clickable", "st": ["Report Audio Issue"], "tf": None, "exp": "l20"},

    # Quizzes
    {"n": "21", "step": "Click radio 'A snake'", "m": "clickable", "st": ["A snake"], "tf": None, "exp": "l21"},
    {"n": "22", "step": "Click radio 'A programming language'", "m": "clickable", "st": ["A programming language"], "tf": None, "exp": "l22"},
    {"n": "23", "step": "Check 'div'", "m": "clickable", "st": ["div"], "tf": None, "exp": "l23"},
    {"n": "24", "step": "Check 'span'", "m": "clickable", "st": ["span"], "tf": None, "exp": "l24"},
    {"n": "25", "step": "Check 'fakeTag'", "m": "clickable", "st": ["fakeTag"], "tf": None, "exp": "l25"},
    {"n": "26", "step": "Click 'Clear my choices'", "m": "clickable", "st": ["Clear my choices"], "tf": None, "exp": "l26"},
    {"n": "27", "step": "Click 'Submit Quiz'", "m": "clickable", "st": ["Submit Quiz"], "tf": None, "exp": "l27"},
    {"n": "28", "step": "VERIFY 'Review Answers' is disabled", "ver": True, "step": "VERIFY that 'Review Answers' is disabled", "res": True},
    {"n": "29", "step": "EXTRACT Quiz Score into {qs}", "ex": True, "var": "qs", "val": "85%"},
    {"n": "30", "step": "Click 'Retake Quiz'", "m": "clickable", "st": ["Retake Quiz"], "tf": None, "exp": "l30"},

    # Coding
    {"n": "31", "step": "Fill 'def' field with 'main'", "m": "input", "st": ["def"], "tf": "def", "exp": "l31"},
    {"n": "32", "step": "Fill 'Code Editor' with 'print(1)'", "m": "input", "st": ["Code Editor"], "tf": "code editor", "exp": "l32"},
    {"n": "33", "step": "Click 'Run Code'", "m": "clickable", "st": ["Run Code"], "tf": None, "exp": "l33"},
    {"n": "34", "step": "Click 'Submit Code'", "m": "clickable", "st": ["Submit Code"], "tf": None, "exp": "l34"},
    {"n": "35", "step": "EXTRACT console output into {out}", "ex": True, "var": "out", "val": "invalid syntax"},
    {"n": "36", "step": "Click 'Hint'", "m": "clickable", "st": ["Hint"], "tf": None, "exp": "l36"},
    {"n": "37", "step": "Click 'View Solution'", "m": "clickable", "st": ["View Solution"], "tf": None, "exp": "l37"},
    {"n": "38", "step": "Click 'Reset Workspace'", "m": "clickable", "st": ["Reset Workspace"], "tf": None, "exp": "l38"},
    {"n": "39", "step": "Click 'Upload Source File'", "m": "clickable", "st": ["Upload Source File"], "tf": None, "exp": "l39"},
    {"n": "40", "step": "Select 'Java' from 'Language'", "m": "select", "st": ["Java", "Language"], "tf": None, "exp": "l40"},

    # Forums
    {"n": "41", "step": "Fill 'Search discussions' with 'help'", "m": "input", "st": ["Search discussions"], "tf": "search discussions", "exp": "l41"},
    {"n": "42", "step": "Click 'Create New Thread'", "m": "clickable", "st": ["Create New Thread"], "tf": None, "exp": "l42"},
    {"n": "43", "step": "Fill 'Thread Title' with 'Bug in Lecture 2'", "m": "input", "st": ["Thread Title"], "tf": "thread title", "exp": "l43"},
    {"n": "44", "step": "Fill 'Type your question here' with 'Audio is missing.'", "m": "input", "st": ["Type your question here"], "tf": "type your question here", "exp": "l44"},
    {"n": "45", "step": "Click 'Post Thread'", "m": "clickable", "st": ["Post Thread"], "tf": None, "exp": "l45"},
    {"n": "46", "step": "Click 'Upvote Post'", "m": "clickable", "st": ["Upvote Post"], "tf": None, "exp": "l46"},
    {"n": "47", "step": "Click 'Downvote Post'", "m": "clickable", "st": ["Downvote Post"], "tf": None, "exp": "l47"},
    {"n": "48", "step": "Click 'Reply to Thread'", "m": "clickable", "st": ["Reply to Thread"], "tf": None, "exp": "l48"},
    {"n": "49", "step": "Click 'Mark as Answer'", "m": "clickable", "st": ["Mark as Answer"], "tf": None, "exp": "l49"},
    {"n": "50", "step": "Click 'Subscribe to updates'", "m": "clickable", "st": ["Subscribe to updates"], "tf": None, "exp": "l50"},

    # Assignments
    {"n": "51", "step": "EXTRACT Project title into {proj}", "ex": True, "var": "proj", "val": "Web Scraper"},
    {"n": "52", "step": "Click 'Upload Assignment'", "m": "clickable", "st": ["Upload Assignment"], "tf": None, "exp": "l52"},
    {"n": "53", "step": "Fill 'Google Drive Link' with 'http://link'", "m": "input", "st": ["Google Drive Link"], "tf": "google drive link", "exp": "l53"},
    {"n": "54", "step": "Fill 'Add comments for grader' with 'Done'", "m": "input", "st": ["Add comments for grader"], "tf": "add comments for grader", "exp": "l54"},
    {"n": "55", "step": "Check 'Honor Code'", "m": "clickable", "st": ["Honor Code"], "tf": None, "exp": "l55"},
    {"n": "56", "step": "Click 'Submit Assignment'", "m": "clickable", "st": ["Submit Assignment"], "tf": None, "exp": "l56"},
    {"n": "57", "step": "Click 'Withdraw Submission'", "m": "clickable", "st": ["Withdraw Submission"], "tf": None, "exp": "l57"},
    {"n": "58", "step": "Click 'View Grading Rubric'", "m": "clickable", "st": ["View Grading Rubric"], "tf": None, "exp": "l58"},
    {"n": "59", "step": "Click 'Request Extension'", "m": "clickable", "st": ["Request Extension"], "tf": None, "exp": "l59"},
    {"n": "60", "step": "VERIFY 'Status: Not Submitted' is present", "ver": True, "res": True},

    # Grades
    {"n": "61", "step": "EXTRACT Final Grade into {fg}", "ex": True, "var": "fg", "val": "A-"},
    {"n": "62", "step": "Click 'Download Transcript'", "m": "clickable", "st": ["Download Transcript"], "tf": None, "exp": "l62"},
    {"n": "63", "step": "EXTRACT Course Progress into {cp}", "ex": True, "var": "cp", "val": "75%"},
    {"n": "64", "step": "Click 'Request Regrade'", "m": "clickable", "st": ["Request Regrade"], "tf": None, "exp": "l64"},
    {"n": "65", "step": "Select 'Spring 2026' from 'Semester'", "m": "select", "st": ["Spring 2026", "Semester"], "tf": None, "exp": "l65"},
    {"n": "66", "step": "EXTRACT GPA into {gpa}", "ex": True, "var": "gpa", "val": "3.8"},
    {"n": "67", "step": "Click 'Share Grades'", "m": "clickable", "st": ["Share Grades"], "tf": None, "exp": "l67"},
    {"n": "68", "step": "Click 'View Weighting'", "m": "clickable", "st": ["View Weighting"], "tf": None, "exp": "l68"},
    {"n": "69", "step": "Fill 'Enter target grade' with '95'", "m": "input", "st": ["Enter target grade"], "tf": "enter target grade", "exp": "l69"},
    {"n": "70", "step": "Click 'Calculate'", "m": "clickable", "st": ["Calculate"], "tf": None, "exp": "l70"},

    # Peer Review
    {"n": "71", "step": "Click 'Start Reviewing'", "m": "clickable", "st": ["Start Reviewing"], "tf": None, "exp": "l71"},
    {"n": "72", "step": "Select '10' from 'Criterion 1'", "m": "select", "st": ["10", "Criterion 1"], "tf": None, "exp": "l72"},
    {"n": "73", "step": "Select '5' from 'Criterion 2'", "m": "select", "st": ["5", "Criterion 2"], "tf": None, "exp": "l73"},
    {"n": "74", "step": "Fill 'Constructive Feedback' with 'Great job'", "m": "input", "st": ["Constructive Feedback"], "tf": "constructive feedback", "exp": "l74"},
    {"n": "75", "step": "Click 'Submit Review'", "m": "clickable", "st": ["Submit Review"], "tf": None, "exp": "l75"},
    {"n": "76", "step": "Click 'Flag for Plagiarism'", "m": "clickable", "st": ["Flag for Plagiarism"], "tf": None, "exp": "l76"},
    {"n": "77", "step": "Click 'Save Draft Review'", "m": "clickable", "st": ["Save Draft Review"], "tf": None, "exp": "l77"},
    {"n": "78", "step": "Click 'View Student Submission'", "m": "clickable", "st": ["View Student Submission"], "tf": None, "exp": "l78"},
    {"n": "79", "step": "Click 'Show Rubric Guidelines'", "m": "clickable", "st": ["Show Rubric Guidelines"], "tf": None, "exp": "l79"},
    {"n": "80", "step": "VERIFY 'Next Submission' is disabled", "ver": True, "step": "VERIFY that 'Next Submission' is disabled", "res": True},

    # Instructor
    {"n": "81", "step": "Click 'Create New Course'", "m": "clickable", "st": ["Create New Course"], "tf": None, "exp": "l81"},
    {"n": "82", "step": "Click 'Edit Syllabus'", "m": "clickable", "st": ["Edit Syllabus"], "tf": None, "exp": "l82"},
    {"n": "83", "step": "Click 'Post Announcement'", "m": "clickable", "st": ["Post Announcement"], "tf": None, "exp": "l83"},
    {"n": "84", "step": "Fill 'Message to Students' with 'Welcome!'", "m": "input", "st": ["Message to Students"], "tf": "message to students", "exp": "l84"},
    {"n": "85", "step": "Click 'Send Message'", "m": "clickable", "st": ["Send Message"], "tf": None, "exp": "l85"},
    {"n": "86", "step": "Click 'Open Gradebook'", "m": "clickable", "st": ["Open Gradebook"], "tf": None, "exp": "l86"},
    {"n": "87", "step": "Click 'Publish Grades'", "m": "clickable", "st": ["Publish Grades"], "tf": None, "exp": "l87"},
    {"n": "88", "step": "Click 'Export Analytics'", "m": "clickable", "st": ["Export Analytics"], "tf": None, "exp": "l88"},
    {"n": "89", "step": "Click 'Accepting Enrollments' switch", "m": "clickable", "st": ["Accepting Enrollments"], "tf": None, "exp": "l89"},
    {"n": "90", "step": "Click 'Unpublish Course'", "m": "clickable", "st": ["Unpublish Course"], "tf": None, "exp": "l90"},

    # Gamification
    {"n": "91", "step": "Click 'Claim Daily Reward'", "m": "clickable", "st": ["Claim Daily Reward"], "tf": None, "exp": "l91"},
    {"n": "92", "step": "EXTRACT Current Streak into {streak}", "ex": True, "var": "streak", "val": "14 Days"},
    {"n": "93", "step": "Click 'View Certificate'", "m": "clickable", "st": ["View Certificate"], "tf": None, "exp": "l93"},
    {"n": "94", "step": "Click 'Share to LinkedIn'", "m": "clickable", "st": ["Share to LinkedIn"], "tf": None, "exp": "l94"},
    {"n": "95", "step": "Click 'Download PDF Certificate'", "m": "clickable", "st": ["Download PDF Certificate"], "tf": None, "exp": "l95"},
    {"n": "96", "step": "EXTRACT Rank into {rank}", "ex": True, "var": "rank", "val": "#4 in Class"},
    {"n": "97", "step": "Click 'View Leaderboard'", "m": "clickable", "st": ["View Leaderboard"], "tf": None, "exp": "l97"},
    {"n": "98", "step": "Click 'Equip Avatar Frame'", "m": "clickable", "st": ["Equip Avatar Frame"], "tf": None, "exp": "l98"},
    {"n": "99", "step": "Click 'Spend XP Points'", "m": "clickable", "st": ["Spend XP Points"], "tf": None, "exp": "l99"},
    {"n": "100", "step": "Click 'Secret Dev Mode' if exists", "m": "clickable", "st": ["Secret Dev Mode"], "tf": None, "exp": None},
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("🎓 EDTECH & E-LEARNING HELL: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(EDTECH_DOM)

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

            elif "if exists" in t["step"]:
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
            print("\n🏆 FLAWLESS VICTORY!")
        print(f"{'=' * 70}")
        await browser.close()

    return passed == len(TESTS)

if __name__ == "__main__":
    asyncio.run(run_suite())