import sys, os, asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: CRM, ATS & PM Tools (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
CRM_DOM = """
<!DOCTYPE html><html><head><style>
.kanban-col { width: 30%; float: left; border: 1px solid #ccc; padding: 5px; }
.ticket-card { background: #eee; margin: 5px; padding: 5px; }
.hidden { display: none; }
</style></head><body>

<nav class="topbar">
    <input type="search" id="c1" placeholder="Search leads, contacts, tickets...">
    <button id="c2" aria-label="Global Create">➕ Create</button>
    <div role="button" id="c3" aria-label="Notifications">🔔</div>
    <a href="/pipelines" id="c4">Pipelines</a>
    <a href="/candidates" id="c5">Candidates (ATS)</a>
    <a href="/reports" id="c6">Reports</a>
    <button id="c7">Recent Items ▼</button>
    <button id="c8" aria-label="Settings">⚙️</button>
    <div role="menuitem" id="c9">My Profile</div>
    <button id="c10">Log Out</button>
</nav>

<div class="kanban-board">
    <div class="kanban-col">
        <h3>New Leads</h3>
        <div class="ticket-card">
            <span id="c11">Acme Corp Deal</span>
            <button id="c12">Move to Contacted</button>
        </div>
    </div>
    <div class="kanban-col">
        <h3>In Progress</h3>
        <div class="ticket-card">
            <span>TechCorp Upgrade</span>
            <button id="c13">Move to Closed Won</button>
            <button id="c14">Move to Closed Lost</button>
        </div>
    </div>
    <button id="c15">Add Column</button>
    <input type="text" id="c16" placeholder="Column Name">
    <button id="c17">Save Column</button>
    <button id="c18" aria-label="Filter Board">Filter</button>
    <select id="c19" aria-label="Board View"><option>Kanban</option><option>List</option></select>
    <button id="c20">Export Board</button>
</div>

<div class="create-form">
    <input type="text" id="c21" placeholder="Lead Name" required>
    <input type="text" id="c22" placeholder="Company Name">
    <input type="email" id="c23" placeholder="Contact Email">
    <input type="tel" id="c24" placeholder="Phone Number">
    <label>Lead Source</label>
    <select id="c25"><option>Inbound</option><option>Cold Call</option><option>Referral</option></select>
    <input type="number" id="c26" aria-label="Expected Revenue ($)">
    <input type="date" id="c27" aria-label="Estimated Close Date">
    <select id="c28" aria-label="Assignee"><option>Unassigned</option><option>Alex Dev</option></select>
    <button id="c29" class="btn-primary">Save Lead</button>
    <button id="c30" class="btn-cancel">Cancel</button>
</div>

<div class="activity-bar">
    <button id="c31">Log a Call</button>
    <button id="c32">Send Email</button>
    <button id="c33">Add Note</button>
    <button id="c34">Schedule Meeting</button>
    <button id="c35">Create Task</button>
    <div class="activity-form">
        <textarea id="c36" placeholder="Write your note here..."></textarea>
        <button id="c37">Attach File</button>
        <button id="c38">@ Mention</button>
        <button id="c39">Save Note</button>
        <div id="c40" role="alert">Note saved successfully.</div>
    </div>
</div>

<div class="ticket-details">
    <h2 id="c41" contenteditable="true" aria-label="Ticket Title">Server Outage</h2>
    <div class="field-group">
        <label>Status:</label>
        <select id="c42"><option>Open</option><option>Resolved</option></select>
    </div>
    <div class="field-group">
        <label>Priority:</label>
        <select id="c43"><option>Low</option><option>Critical</option></select>
    </div>
    <div class="tags">
        <span class="tag">Bug <button id="c44" aria-label="Remove Bug tag">x</button></span>
        <input type="text" id="c45" placeholder="Add tag...">
        <button id="c46">Add</button>
    </div>
    <button id="c47">Link Issue</button>
    <button id="c48">Clone Ticket</button>
    <button id="c49" aria-label="Watch Ticket">👀 Watch</button>
    <button id="c50" aria-label="Vote on Ticket">👍 Vote</button>
</div>

<div class="ats-view">
    <h3 id="c51" data-qa="candidate-name">Sarah Connor</h3>
    <a href="/resume.pdf" id="c52">View Resume</a>
    <a href="/linkedin" id="c53">LinkedIn Profile</a>
    <select id="c54" aria-label="Stage"><option>Screening</option><option>Interview</option><option>Offer</option></select>
    <button id="c55" style="background:green;">Move to Offer</button>
    <button id="c56" style="background:red;">Reject Candidate</button>
    <select id="c57" aria-label="Rejection Reason"><option>Not a fit</option><option>Salary expectations</option></select>
    <button id="c58">Send Rejection Email</button>
    <button id="c59">Schedule Interview</button>
    <button id="c60">Request Feedback from Team</button>
</div>

<table id="crm_table">
    <thead>
        <tr>
            <th><input type="checkbox" id="c61" aria-label="Select All Leads"></th>
            <th>Name</th>
            <th>Score</th>
            <th>Action</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><input type="checkbox" id="c62" aria-label="Select Lead 1"></td>
            <td>John Doe</td>
            <td id="c63">85</td>
            <td><button id="c64">Edit</button></td>
        </tr>
    </tbody>
</table>
<div class="bulk-actions">
    <button id="c65">Bulk Assign</button>
    <button id="c66">Bulk Delete</button>
    <button id="c67">Merge Duplicates</button>
    <button id="c68">Add to Campaign</button>
    <button id="c69">Change Status</button>
    <button id="c70" disabled>Apply Bulk Action</button>
</div>

<div class="advanced-filters">
    <select id="c71" aria-label="Filter Field"><option>Status</option><option>Revenue</option></select>
    <select id="c72" aria-label="Filter Operator"><option>Equals</option><option>Greater Than</option></select>
    <input type="text" id="c73" placeholder="Filter Value">
    <button id="c74">Add Condition</button>
    <button id="c75">Apply Filter</button>
    <div class="active-filter">Status equals Open <button id="c76" aria-label="Remove Filter">X</button></div>
    <input type="text" id="c77" placeholder="Save filter as...">
    <button id="c78">Save Filter</button>
    <select id="c79" aria-label="Saved Filters"><option>My Open Leads</option></select>
    <button id="c80">Clear All</button>
</div>

<div class="reporting">
    <select id="c81" aria-label="Report Type"><option>Sales Funnel</option><option>Time to Hire</option></select>
    <input type="date" id="c82" aria-label="Report Start Date">
    <input type="date" id="c83" aria-label="Report End Date">
    <button id="c84">Generate Report</button>
    <div id="c85" class="chart-value">Total Deals: 145</div>
    <button id="c86">Download Excel</button>
    <button id="c87">Download PDF</button>
    <button id="c88">Share via Email</button>
    <button id="c89">Schedule Report</button>
    <div role="switch" id="c90" aria-checked="false" aria-label="Include deleted records"></div>
</div>

<div class="settings-panel">
    <button id="c91">Create Workflow Rule</button>
    <input type="text" id="c92" placeholder="Rule Name">
    <select id="c93" aria-label="Trigger Event"><option>On Create</option><option>On Update</option></select>
    <select id="c94" aria-label="Action"><option>Send Email</option><option>Update Field</option></select>
    <button id="c95">Save Workflow</button>
    <button id="c96">Create Custom Field</button>
    <input type="text" id="c97" placeholder="Field Label">
    <select id="c98" aria-label="Field Type"><option>Text</option><option>Number</option><option>Dropdown</option></select>
    <button id="c99">Save Field</button>
    <button id="c100" style="display:none;">Unlock Admin Mode</button>
</div>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Global Topbar
    {
        "n": "1",
        "step": "Fill 'Search leads' with 'Acme'",
        "m": "input",
        "st": ["Search leads"],
        "tf": "search leads",
        "exp": "c1",
    },
    {"n": "2", "step": "Click 'Global Create'", "m": "clickable", "st": ["Global Create"], "tf": None, "exp": "c2"},
    {"n": "3", "step": "Click 'Notifications'", "m": "clickable", "st": ["Notifications"], "tf": None, "exp": "c3"},
    {"n": "4", "step": "Click 'Pipelines'", "m": "clickable", "st": ["Pipelines"], "tf": None, "exp": "c4"},
    {"n": "5", "step": "Click 'Candidates'", "m": "clickable", "st": ["Candidates"], "tf": None, "exp": "c5"},
    {"n": "6", "step": "Click 'Reports'", "m": "clickable", "st": ["Reports"], "tf": None, "exp": "c6"},
    {"n": "7", "step": "Click 'Recent Items'", "m": "clickable", "st": ["Recent Items"], "tf": None, "exp": "c7"},
    {"n": "8", "step": "Click 'Settings'", "m": "clickable", "st": ["Settings"], "tf": None, "exp": "c8"},
    {"n": "9", "step": "Click 'My Profile'", "m": "clickable", "st": ["My Profile"], "tf": None, "exp": "c9"},
    {"n": "10", "step": "Click 'Log Out'", "m": "clickable", "st": ["Log Out"], "tf": None, "exp": "c10"},
    # Kanban Board
    {
        "n": "11",
        "step": "EXTRACT text of 'Acme Corp Deal' into {deal}",
        "ex": True,
        "var": "deal",
        "val": "Acme Corp Deal",
    },
    {
        "n": "12",
        "step": "Click 'Move to Contacted'",
        "m": "clickable",
        "st": ["Move to Contacted"],
        "tf": None,
        "exp": "c12",
    },
    {
        "n": "13",
        "step": "Click 'Move to Closed Won'",
        "m": "clickable",
        "st": ["Move to Closed Won"],
        "tf": None,
        "exp": "c13",
    },
    {
        "n": "14",
        "step": "Click 'Move to Closed Lost'",
        "m": "clickable",
        "st": ["Move to Closed Lost"],
        "tf": None,
        "exp": "c14",
    },
    {"n": "15", "step": "Click 'Add Column'", "m": "clickable", "st": ["Add Column"], "tf": None, "exp": "c15"},
    {
        "n": "16",
        "step": "Fill 'Column Name' with 'On Hold'",
        "m": "input",
        "st": ["Column Name"],
        "tf": "column name",
        "exp": "c16",
    },
    {"n": "17", "step": "Click 'Save Column'", "m": "clickable", "st": ["Save Column"], "tf": None, "exp": "c17"},
    {"n": "18", "step": "Click 'Filter Board'", "m": "clickable", "st": ["Filter Board"], "tf": None, "exp": "c18"},
    {
        "n": "19",
        "step": "Select 'List' from 'Board View'",
        "m": "select",
        "st": ["List", "Board View"],
        "tf": None,
        "exp": "c19",
    },
    {"n": "20", "step": "Click 'Export Board'", "m": "clickable", "st": ["Export Board"], "tf": None, "exp": "c20"},
    # Lead Creation Form
    {
        "n": "21",
        "step": "Fill 'Lead Name' with 'Elon Musk'",
        "m": "input",
        "st": ["Lead Name"],
        "tf": "lead name",
        "exp": "c21",
    },
    {
        "n": "22",
        "step": "Fill 'Company Name' with 'SpaceX'",
        "m": "input",
        "st": ["Company Name"],
        "tf": "company name",
        "exp": "c22",
    },
    {
        "n": "23",
        "step": "Fill 'Contact Email' with 'elon@x.com'",
        "m": "input",
        "st": ["Contact Email"],
        "tf": "contact email",
        "exp": "c23",
    },
    {
        "n": "24",
        "step": "Fill 'Phone Number' with '12345'",
        "m": "input",
        "st": ["Phone Number"],
        "tf": "phone number",
        "exp": "c24",
    },
    {
        "n": "25",
        "step": "Select 'Inbound' from 'Lead Source'",
        "m": "select",
        "st": ["Inbound", "Lead Source"],
        "tf": None,
        "exp": "c25",
    },
    {
        "n": "26",
        "step": "Fill 'Expected Revenue' with '1000000'",
        "m": "input",
        "st": ["Expected Revenue"],
        "tf": "expected revenue",
        "exp": "c26",
    },
    {
        "n": "27",
        "step": "Fill 'Estimated Close Date' with '2026-12-31'",
        "m": "input",
        "st": ["Estimated Close Date"],
        "tf": "estimated close date",
        "exp": "c27",
    },
    {
        "n": "28",
        "step": "Select 'Alex Dev' from 'Assignee'",
        "m": "select",
        "st": ["Alex Dev", "Assignee"],
        "tf": None,
        "exp": "c28",
    },
    {"n": "29", "step": "Click 'Save Lead'", "m": "clickable", "st": ["Save Lead"], "tf": None, "exp": "c29"},
    {"n": "30", "step": "Click 'Cancel'", "m": "clickable", "st": ["Cancel"], "tf": None, "exp": "c30"},
    # Ticket Actions
    {"n": "31", "step": "Click 'Log a Call'", "m": "clickable", "st": ["Log a Call"], "tf": None, "exp": "c31"},
    {"n": "32", "step": "Click 'Send Email'", "m": "clickable", "st": ["Send Email"], "tf": None, "exp": "c32"},
    {"n": "33", "step": "Click 'Add Note'", "m": "clickable", "st": ["Add Note"], "tf": None, "exp": "c33"},
    {
        "n": "34",
        "step": "Click 'Schedule Meeting'",
        "m": "clickable",
        "st": ["Schedule Meeting"],
        "tf": None,
        "exp": "c34",
    },
    {"n": "35", "step": "Click 'Create Task'", "m": "clickable", "st": ["Create Task"], "tf": None, "exp": "c35"},
    {
        "n": "36",
        "step": "Fill 'Write your note' with 'Client called'",
        "m": "input",
        "st": ["Write your note"],
        "tf": "write your note",
        "exp": "c36",
    },
    {"n": "37", "step": "Click 'Attach File'", "m": "clickable", "st": ["Attach File"], "tf": None, "exp": "c37"},
    {"n": "38", "step": "Click '@ Mention'", "m": "clickable", "st": ["@ Mention"], "tf": None, "exp": "c38"},
    {"n": "39", "step": "Click 'Save Note'", "m": "clickable", "st": ["Save Note"], "tf": None, "exp": "c39"},
    {"n": "40", "step": "VERIFY 'Note saved successfully' is present", "ver": True, "res": True},
    # Details & Inline Edit
    {
        "n": "41",
        "step": "Fill 'Ticket Title' with 'Server FIXED'",
        "m": "input",
        "st": ["Ticket Title"],
        "tf": "ticket title",
        "exp": "c41",
    },
    {
        "n": "42",
        "step": "Select 'Resolved' from 'Status'",
        "m": "select",
        "st": ["Resolved", "Status"],
        "tf": None,
        "exp": "c42",
    },
    {
        "n": "43",
        "step": "Select 'Critical' from 'Priority'",
        "m": "select",
        "st": ["Critical", "Priority"],
        "tf": None,
        "exp": "c43",
    },
    {"n": "44", "step": "Click 'Remove Bug tag'", "m": "clickable", "st": ["Remove Bug tag"], "tf": None, "exp": "c44"},
    {
        "n": "45",
        "step": "Fill 'Add tag...' with 'Urgent'",
        "m": "input",
        "st": ["Add tag..."],
        "tf": "add tag...",
        "exp": "c45",
    },
    {"n": "46", "step": "Click 'Add'", "m": "clickable", "st": ["Add"], "tf": None, "exp": "c46"},
    {"n": "47", "step": "Click 'Link Issue'", "m": "clickable", "st": ["Link Issue"], "tf": None, "exp": "c47"},
    {"n": "48", "step": "Click 'Clone Ticket'", "m": "clickable", "st": ["Clone Ticket"], "tf": None, "exp": "c48"},
    {"n": "49", "step": "Click 'Watch Ticket'", "m": "clickable", "st": ["Watch Ticket"], "tf": None, "exp": "c49"},
    {"n": "50", "step": "Click 'Vote on Ticket'", "m": "clickable", "st": ["Vote on Ticket"], "tf": None, "exp": "c50"},
    # ATS (Applicant Tracking System)
    {"n": "51", "step": "EXTRACT Candidate name into {cand}", "ex": True, "var": "cand", "val": "Sarah Connor"},
    {"n": "52", "step": "Click 'View Resume'", "m": "clickable", "st": ["View Resume"], "tf": None, "exp": "c52"},
    {
        "n": "53",
        "step": "Click 'LinkedIn Profile'",
        "m": "clickable",
        "st": ["LinkedIn Profile"],
        "tf": None,
        "exp": "c53",
    },
    {
        "n": "54",
        "step": "Select 'Offer' from 'Stage'",
        "m": "select",
        "st": ["Offer", "Stage"],
        "tf": None,
        "exp": "c54",
    },
    {"n": "55", "step": "Click 'Move to Offer'", "m": "clickable", "st": ["Move to Offer"], "tf": None, "exp": "c55"},
    {
        "n": "56",
        "step": "Click 'Reject Candidate'",
        "m": "clickable",
        "st": ["Reject Candidate"],
        "tf": None,
        "exp": "c56",
    },
    {
        "n": "57",
        "step": "Select 'Not a fit' from 'Rejection Reason'",
        "m": "select",
        "st": ["Not a fit", "Rejection Reason"],
        "tf": None,
        "exp": "c57",
    },
    {
        "n": "58",
        "step": "Click 'Send Rejection Email'",
        "m": "clickable",
        "st": ["Send Rejection Email"],
        "tf": None,
        "exp": "c58",
    },
    {
        "n": "59",
        "step": "Click 'Schedule Interview'",
        "m": "clickable",
        "st": ["Schedule Interview"],
        "tf": None,
        "exp": "c59",
    },
    {
        "n": "60",
        "step": "Click 'Request Feedback'",
        "m": "clickable",
        "st": ["Request Feedback"],
        "tf": None,
        "exp": "c60",
    },
    # Bulk Actions
    {
        "n": "61",
        "step": "Check 'Select All Leads'",
        "m": "clickable",
        "st": ["Select All Leads"],
        "tf": None,
        "exp": "c61",
    },
    {"n": "62", "step": "Check 'Select Lead 1'", "m": "clickable", "st": ["Select Lead 1"], "tf": None, "exp": "c62"},
    {"n": "63", "step": "EXTRACT Score of 'John Doe' into {s}", "ex": True, "var": "s", "val": "85"},
    {"n": "64", "step": "Click 'Edit' for lead", "m": "clickable", "st": ["Edit"], "tf": None, "exp": "c64"},
    {"n": "65", "step": "Click 'Bulk Assign'", "m": "clickable", "st": ["Bulk Assign"], "tf": None, "exp": "c65"},
    {"n": "66", "step": "Click 'Bulk Delete'", "m": "clickable", "st": ["Bulk Delete"], "tf": None, "exp": "c66"},
    {
        "n": "67",
        "step": "Click 'Merge Duplicates'",
        "m": "clickable",
        "st": ["Merge Duplicates"],
        "tf": None,
        "exp": "c67",
    },
    {
        "n": "68",
        "step": "Click 'Add to Campaign'",
        "m": "clickable",
        "st": ["Add to Campaign"],
        "tf": None,
        "exp": "c68",
    },
    {"n": "69", "step": "Click 'Change Status'", "m": "clickable", "st": ["Change Status"], "tf": None, "exp": "c69"},
    {
        "n": "70",
        "step": "VERIFY 'Apply Bulk Action' is disabled",
        "ver": True,
        "step": "VERIFY that 'Apply Bulk Action' is disabled",
        "res": True,
    },
    # Advanced Filters
    {
        "n": "71",
        "step": "Select 'Status' from 'Filter Field'",
        "m": "select",
        "st": ["Status", "Filter Field"],
        "tf": None,
        "exp": "c71",
    },
    {
        "n": "72",
        "step": "Select 'Equals' from 'Filter Operator'",
        "m": "select",
        "st": ["Equals", "Filter Operator"],
        "tf": None,
        "exp": "c72",
    },
    {
        "n": "73",
        "step": "Fill 'Filter Value' with 'Open'",
        "m": "input",
        "st": ["Filter Value"],
        "tf": "filter value",
        "exp": "c73",
    },
    {"n": "74", "step": "Click 'Add Condition'", "m": "clickable", "st": ["Add Condition"], "tf": None, "exp": "c74"},
    {"n": "75", "step": "Click 'Apply Filter'", "m": "clickable", "st": ["Apply Filter"], "tf": None, "exp": "c75"},
    {"n": "76", "step": "Click 'Remove Filter'", "m": "clickable", "st": ["Remove Filter"], "tf": None, "exp": "c76"},
    {
        "n": "77",
        "step": "Fill 'Save filter as' with 'Active'",
        "m": "input",
        "st": ["Save filter as"],
        "tf": "save filter as",
        "exp": "c77",
    },
    {"n": "78", "step": "Click 'Save Filter'", "m": "clickable", "st": ["Save Filter"], "tf": None, "exp": "c78"},
    {
        "n": "79",
        "step": "Select 'My Open Leads' from 'Saved Filters'",
        "m": "select",
        "st": ["My Open Leads", "Saved Filters"],
        "tf": None,
        "exp": "c79",
    },
    {"n": "80", "step": "Click 'Clear All'", "m": "clickable", "st": ["Clear All"], "tf": None, "exp": "c80"},
    # Dashboards & Reporting
    {
        "n": "81",
        "step": "Select 'Time to Hire' from 'Report Type'",
        "m": "select",
        "st": ["Time to Hire", "Report Type"],
        "tf": None,
        "exp": "c81",
    },
    {
        "n": "82",
        "step": "Fill 'Report Start Date' with '2026-01-01'",
        "m": "input",
        "st": ["Report Start Date"],
        "tf": "report start date",
        "exp": "c82",
    },
    {
        "n": "83",
        "step": "Fill 'Report End Date' with '2026-01-31'",
        "m": "input",
        "st": ["Report End Date"],
        "tf": "report end date",
        "exp": "c83",
    },
    {
        "n": "84",
        "step": "Click 'Generate Report'",
        "m": "clickable",
        "st": ["Generate Report"],
        "tf": None,
        "exp": "c84",
    },
    {"n": "85", "step": "EXTRACT Total Deals into {td}", "ex": True, "var": "td", "val": "145"},
    {"n": "86", "step": "Click 'Download Excel'", "m": "clickable", "st": ["Download Excel"], "tf": None, "exp": "c86"},
    {"n": "87", "step": "Click 'Download PDF'", "m": "clickable", "st": ["Download PDF"], "tf": None, "exp": "c87"},
    {
        "n": "88",
        "step": "Click 'Share via Email'",
        "m": "clickable",
        "st": ["Share via Email"],
        "tf": None,
        "exp": "c88",
    },
    {
        "n": "89",
        "step": "Click 'Schedule Report'",
        "m": "clickable",
        "st": ["Schedule Report"],
        "tf": None,
        "exp": "c89",
    },
    {
        "n": "90",
        "step": "Click 'Include deleted records' switch",
        "m": "clickable",
        "st": ["Include deleted records"],
        "tf": None,
        "exp": "c90",
    },
    # Settings & Workflows
    {
        "n": "91",
        "step": "Click 'Create Workflow Rule'",
        "m": "clickable",
        "st": ["Create Workflow Rule"],
        "tf": None,
        "exp": "c91",
    },
    {
        "n": "92",
        "step": "Fill 'Rule Name' with 'Auto-assign'",
        "m": "input",
        "st": ["Rule Name"],
        "tf": "rule name",
        "exp": "c92",
    },
    {
        "n": "93",
        "step": "Select 'On Create' from 'Trigger Event'",
        "m": "select",
        "st": ["On Create", "Trigger Event"],
        "tf": None,
        "exp": "c93",
    },
    {
        "n": "94",
        "step": "Select 'Update Field' from 'Action'",
        "m": "select",
        "st": ["Update Field", "Action"],
        "tf": None,
        "exp": "c94",
    },
    {"n": "95", "step": "Click 'Save Workflow'", "m": "clickable", "st": ["Save Workflow"], "tf": None, "exp": "c95"},
    {
        "n": "96",
        "step": "Click 'Create Custom Field'",
        "m": "clickable",
        "st": ["Create Custom Field"],
        "tf": None,
        "exp": "c96",
    },
    {
        "n": "97",
        "step": "Fill 'Field Label' with 'Skype ID'",
        "m": "input",
        "st": ["Field Label"],
        "tf": "field label",
        "exp": "c97",
    },
    {
        "n": "98",
        "step": "Select 'Text' from 'Field Type'",
        "m": "select",
        "st": ["Text", "Field Type"],
        "tf": None,
        "exp": "c98",
    },
    {"n": "99", "step": "Click 'Save Field'", "m": "clickable", "st": ["Save Field"], "tf": None, "exp": "c99"},
    {
        "n": "100",
        "step": "Click 'Unlock Admin Mode' if exists",
        "m": "clickable",
        "st": ["Unlock Admin Mode"],
        "tf": None,
        "exp": None,
    },  # Hidden
]


async def run_suite():
    print(f"\n{'=' * 70}")
    print("💼 CRM, ATS & PM HELL: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(CRM_DOM)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🧬 {t['n']}")
            print(f"   🐾 Step : {t['step']}")

            manul.reset_session_state()

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
