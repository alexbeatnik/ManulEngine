import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: Media & Video Streaming (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
MEDIA_DOM = """
<!DOCTYPE html><html><head><style>
.player-controls { background: #000; color: #fff; padding: 10px; display: flex; gap: 10px; }
.svg-btn { width: 30px; height: 30px; cursor: pointer; }
.hidden { display: none; }
.ad-banner { background: yellow; padding: 10px; }
</style></head><body>

<div class="player-controls">
    <button id="m1" aria-label="Play Video">▶</button>
    <button id="m2" aria-label="Pause Video" style="display:none;">⏸</button>
    <button id="m3" aria-label="Rewind 10 seconds">⏪</button>
    <button id="m4" aria-label="Forward 10 seconds">⏩</button>
    <button id="m5" aria-label="Mute"><svg><path d="speaker"/></svg></button>
    <input type="range" id="m6" aria-label="Volume" min="0" max="100" value="50">
    <input type="range" id="m7" aria-label="Timeline" min="0" max="1000" value="120">
    <span id="m8" data-qa="timestamp">12:34 / 45:00</span>
    <button id="m9" aria-label="Next Video">⏭</button>
    <div role="button" id="m10" aria-label="Miniplayer">🔲</div>
</div>

<div class="player-settings">
    <button id="m11" aria-label="Settings">⚙️</button>
    <button id="m12" aria-label="Subtitles/closed captions (c)">CC</button>
    <button id="m13" aria-label="Theater mode (t)">🖵</button>
    <button id="m14" aria-label="Fullscreen (f)">🔲</button>
    <select id="m15" aria-label="Playback Quality"><option>Auto</option><option>1080p</option><option>4K</option></select>
    <select id="m16" aria-label="Playback Speed"><option>Normal</option><option>1.5x</option><option>2x</option></select>
    <div role="menuitem" id="m17">Report playback issue</div>
    <div role="switch" id="m18" aria-checked="true" aria-label="Annotations"></div>
    <div role="switch" id="m19" aria-checked="false" aria-label="Ambient Mode"></div>
    <button id="m20" aria-label="Loop video">🔁</button>
</div>

<div class="video-info">
    <h1 id="m21" data-qa="video-title">10 Hours of Manul Cats Meowing</h1>
    <span id="m22">1,500,000 views</span>
    <button id="m23" aria-label="Like this video">👍 50K</button>
    <button id="m24" aria-label="Dislike this video">👎</button>
    <button id="m25">Share</button>
    <button id="m26">Download</button>
    <button id="m27" aria-label="Save to playlist">➕ Save</button>
    <button id="m28" class="btn-subscribe">Subscribe</button>
    <button id="m29" aria-label="Join channel">Join</button>
    <button id="m30" aria-label="More actions">•••</button>
</div>

<div class="comments">
    <h2 id="m31">1,204 Comments</h2>
    <button id="m32">Sort by</button>
    <div role="menuitem" id="m33">Top comments</div>
    <div role="menuitem" id="m34">Newest first</div>
    <input type="text" id="m35" placeholder="Add a comment...">
    <button id="m36" disabled>Comment</button>
    <button id="m37">Cancel</button>
    <div class="comment-thread">
        <button id="m38" aria-label="Like comment">👍</button>
        <button id="m39">Reply</button>
        <div role="button" id="m40">View 5 replies</div>
    </div>
</div>

<div class="sidebar">
    <div role="switch" id="m41" aria-checked="true">Autoplay</div>
    <div class="video-card">
        <a href="/watch?v=2" id="m42">Funny Dogs Compilation</a>
        <button id="m43" aria-label="Add to queue">🕒</button>
    </div>
    <div class="video-card">
        <a href="/watch?v=3" id="m44">Nature Documentary</a>
        <button id="m45" aria-label="Add to queue">🕒</button>
    </div>
    <button id="m46">Show more</button>
    <div id="m47">Playlist: Favorites (12/50)</div>
    <button id="m48" aria-label="Shuffle playlist">🔀</button>
    <button id="m49" aria-label="Save playlist">➕</button>
    <button id="m50" aria-label="Hide playlist">❌</button>
</div>

<div class="hero-banner">
    <h1 id="m51">Stranger Manuls</h1>
    <button id="m52" class="btn-play" data-qa="hero-play">▶ Play</button>
    <button id="m53" class="btn-info">ℹ More Info</button>
    <button id="m54" aria-label="Mute trailer">🔇</button>
</div>
<div class="carousel">
    <h3 id="m55">Trending Now</h3>
    <button id="m56" aria-label="Scroll Left">◀</button>
    <div class="movie-card" id="m57">Movie 1</div>
    <div class="movie-card" id="m58">Movie 2</div>
    <button id="m59" aria-label="Scroll Right">▶</button>
    <button id="m60" aria-label="Add to My List">✚</button>
</div>

<div class="episode-modal">
    <select id="m61" aria-label="Season Selector"><option>Season 1</option><option>Season 2</option></select>
    <div class="episode" id="m62">
        <h4>1. The Beginning</h4>
        <button id="m63">Play Episode 1</button>
        <button id="m64">Download Episode 1</button>
    </div>
    <div class="episode" id="m65">
        <h4>2. The Middle</h4>
        <button id="m66">Play Episode 2</button>
    </div>
    <button id="m67">Resume from 15:00</button>
    <button id="m68">Play from beginning</button>
    <button id="m69">Rate this title</button>
    <button id="m70" aria-label="Remove from My List">✔</button>
</div>

<div class="audio-player">
    <img src="album.jpg" alt="Album Cover" id="m71">
    <button id="m72" aria-label="Save to Your Library">💚</button>
    <button id="m73" aria-label="Enable shuffle">🔀</button>
    <button id="m74" aria-label="Previous track">⏮</button>
    <button id="m75" class="play-btn" aria-label="Pause/Play">▶</button>
    <button id="m76" aria-label="Next track">⏭</button>
    <button id="m77" aria-label="Enable repeat">🔁</button>
    <button id="m78" aria-label="Lyrics">🎤</button>
    <button id="m79" aria-label="Queue">🎶</button>
    <button id="m80" aria-label="Connect to a device">💻</button>
</div>

<div class="discover">
    <input type="search" id="m81" placeholder="Movies, shows, and more">
    <button id="m82" aria-label="Clear Search">X</button>
    <button id="m83">Filter by Genre</button>
    <div role="checkbox" id="m84" aria-checked="false">Action</div>
    <div role="checkbox" id="m85" aria-checked="true">Comedy</div>
    <div role="checkbox" id="m86" aria-checked="false">Sci-Fi</div>
    <button id="m87">Apply Filters</button>
    <a href="/browse/podcasts" id="m88">Podcasts</a>
    <a href="/browse/audiobooks" id="m89">Audiobooks</a>
    <a href="/browse/live" id="m90">Live Radio</a>
</div>

<div class="ad-banner">
    <div id="m91">Ad ends in 5</div>
    <button id="m92">Skip Ad</button>
    <button id="m93" aria-label="Learn more about this ad">Learn More</button>
</div>
<div class="popup" id="timeout_modal">
    <h2 id="m94">Are you still watching?</h2>
    <button id="m95">Continue Watching</button>
    <button id="m96">Go to Homepage</button>
</div>
<div class="age-gate">
    <h2 id="m97">This video may be inappropriate for some users.</h2>
    <button id="m98">I understand and wish to proceed</button>
    <button id="m99">Go back</button>
</div>
<button id="m100" style="display:none;">Claim Free Premium</button>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-97
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Main Player Controls (1-10)
    {"n": "1", "step": "Click 'Play Video'", "m": "clickable", "st": ["Play Video"], "tf": None, "exp": "m1"},
    {"n": "2", "step": "Click 'Pause Video' if exists", "m": "clickable", "st": ["Pause Video"], "tf": None, "exp": None}, # Hidden
    {"n": "3", "step": "Click 'Rewind 10 seconds'", "m": "clickable", "st": ["Rewind 10 seconds"], "tf": None, "exp": "m3"},
    {"n": "4", "step": "Click 'Forward 10 seconds'", "m": "clickable", "st": ["Forward 10 seconds"], "tf": None, "exp": "m4"},
    {"n": "5", "step": "Click 'Mute'", "m": "clickable", "st": ["Mute"], "tf": None, "exp": "m5"},
    {"n": "6", "step": "Fill 'Volume' slider with '80'", "m": "input", "st": ["Volume"], "tf": "volume", "exp": "m6"},
    {"n": "7", "step": "Fill 'Timeline' with '500'", "m": "input", "st": ["Timeline"], "tf": "timeline", "exp": "m7"},
    {"n": "8", "step": "EXTRACT timestamp into {time}", "ex": True, "var": "time", "val": "12:34 / 45:00"},
    {"n": "9", "step": "Click 'Next Video'", "m": "clickable", "st": ["Next Video"], "tf": None, "exp": "m9"},
    {"n": "10", "step": "Click 'Miniplayer'", "m": "clickable", "st": ["Miniplayer"], "tf": None, "exp": "m10"},

    # Player Settings (11-20)
    {"n": "11", "step": "Click 'Settings'", "m": "clickable", "st": ["Settings"], "tf": None, "exp": "m11"},
    {"n": "12", "step": "Click 'Subtitles/closed captions'", "m": "clickable", "st": ["Subtitles/closed captions"], "tf": None, "exp": "m12"},
    {"n": "13", "step": "Click 'Theater mode'", "m": "clickable", "st": ["Theater mode"], "tf": None, "exp": "m13"},
    {"n": "14", "step": "Click 'Fullscreen'", "m": "clickable", "st": ["Fullscreen"], "tf": None, "exp": "m14"},
    {"n": "15", "step": "Select '4K' from 'Playback Quality'", "m": "select", "st": ["4K", "Playback Quality"], "tf": None, "exp": "m15"},
    {"n": "16", "step": "Select '1.5x' from 'Playback Speed'", "m": "select", "st": ["1.5x", "Playback Speed"], "tf": None, "exp": "m16"},
    {"n": "17", "step": "Click 'Report playback issue'", "m": "clickable", "st": ["Report playback issue"], "tf": None, "exp": "m17"},
    {"n": "18", "step": "Click 'Annotations' switch", "m": "clickable", "st": ["Annotations"], "tf": None, "exp": "m18"},
    {"n": "19", "step": "Click 'Ambient Mode'", "m": "clickable", "st": ["Ambient Mode"], "tf": None, "exp": "m19"},
    {"n": "20", "step": "Click 'Loop video'", "m": "clickable", "st": ["Loop video"], "tf": None, "exp": "m20"},

    # Video Info & Actions (21-30)
    {"n": "21", "step": "EXTRACT video title into {title}", "ex": True, "var": "title", "val": "10 Hours of Manul Cats Meowing"},
    {"n": "22", "step": "EXTRACT views into {views}", "ex": True, "var": "views", "val": "1,500,000 views"},
    {"n": "23", "step": "Click 'Like this video'", "m": "clickable", "st": ["Like this video"], "tf": None, "exp": "m23"},
    {"n": "24", "step": "Click 'Dislike this video'", "m": "clickable", "st": ["Dislike this video"], "tf": None, "exp": "m24"},
    {"n": "25", "step": "Click 'Share'", "m": "clickable", "st": ["Share"], "tf": None, "exp": "m25"},
    {"n": "26", "step": "Click 'Download'", "m": "clickable", "st": ["Download"], "tf": None, "exp": "m26"},
    {"n": "27", "step": "Click 'Save to playlist'", "m": "clickable", "st": ["Save to playlist"], "tf": None, "exp": "m27"},
    {"n": "28", "step": "Click 'Subscribe'", "m": "clickable", "st": ["Subscribe"], "tf": None, "exp": "m28"},
    {"n": "29", "step": "Click 'Join channel'", "m": "clickable", "st": ["Join channel"], "tf": None, "exp": "m29"},
    {"n": "30", "step": "Click 'More actions'", "m": "clickable", "st": ["More actions"], "tf": None, "exp": "m30"},

    # Comments Section (31-40)
    {"n": "31", "step": "VERIFY '1,204 Comments' is present", "ver": True, "res": True},
    {"n": "32", "step": "Click 'Sort by'", "m": "clickable", "st": ["Sort by"], "tf": None, "exp": "m32"},
    {"n": "33", "step": "Click 'Top comments'", "m": "clickable", "st": ["Top comments"], "tf": None, "exp": "m33"},
    {"n": "34", "step": "Click 'Newest first'", "m": "clickable", "st": ["Newest first"], "tf": None, "exp": "m34"},
    {"n": "35", "step": "Fill 'Add a comment...' with 'Awesome!'", "m": "input", "st": ["Add a comment..."], "tf": "add a comment...", "exp": "m35"},
    {"n": "36", "step": "VERIFY 'Comment' is disabled", "ver": True, "step": "VERIFY that 'Comment' is disabled", "res": True},
    {"n": "37", "step": "Click 'Cancel'", "m": "clickable", "st": ["Cancel"], "tf": None, "exp": "m37"},
    {"n": "38", "step": "Click 'Like comment'", "m": "clickable", "st": ["Like comment"], "tf": None, "exp": "m38"},
    {"n": "39", "step": "Click 'Reply'", "m": "clickable", "st": ["Reply"], "tf": None, "exp": "m39"},
    {"n": "40", "step": "Click 'View 5 replies'", "m": "clickable", "st": ["View 5 replies"], "tf": None, "exp": "m40"},

    # Sidebar & Up Next (41-49)
    {"n": "41", "step": "Click 'Autoplay' toggle", "m": "clickable", "st": ["Autoplay"], "tf": None, "exp": "m41"},
    {"n": "42", "step": "Click 'Funny Dogs Compilation'", "m": "clickable", "st": ["Funny Dogs Compilation"], "tf": None, "exp": "m42"},
    {"n": "43", "step": "Click 'Add to queue' (first)", "m": "clickable", "st": ["Add to queue"], "tf": None, "exp": "m43"},
    {"n": "44", "step": "Click 'Nature Documentary'", "m": "clickable", "st": ["Nature Documentary"], "tf": None, "exp": "m44"},
    {"n": "45", "step": "Click 'Show more'", "m": "clickable", "st": ["Show more"], "tf": None, "exp": "m46"},
    {"n": "46", "step": "VERIFY 'Playlist: Favorites' is present", "ver": True, "res": True},
    {"n": "47", "step": "Click 'Shuffle playlist'", "m": "clickable", "st": ["Shuffle playlist"], "tf": None, "exp": "m48"},
    {"n": "48", "step": "Click 'Save playlist'", "m": "clickable", "st": ["Save playlist"], "tf": None, "exp": "m49"},
    {"n": "49", "step": "Click 'Hide playlist'", "m": "clickable", "st": ["Hide playlist"], "tf": None, "exp": "m50"},

    # Streaming Homepage (51-59)
    {"n": "51", "step": "VERIFY 'Stranger Manuls' is present", "ver": True, "res": True},
    {"n": "52", "step": "Click 'Play'", "m": "clickable", "st": ["Play"], "tf": None, "exp": "m52"},
    {"n": "53", "step": "Click 'More Info'", "m": "clickable", "st": ["More Info"], "tf": None, "exp": "m53"},
    {"n": "54", "step": "Click 'Mute trailer'", "m": "clickable", "st": ["Mute trailer"], "tf": None, "exp": "m54"},
    {"n": "55", "step": "VERIFY 'Trending Now' is present", "ver": True, "res": True},
    {"n": "56", "step": "Click 'Scroll Left'", "m": "clickable", "st": ["Scroll Left"], "tf": None, "exp": "m56"},
    {"n": "57", "step": "Click 'Movie 1'", "m": "clickable", "st": ["Movie 1"], "tf": None, "exp": "m57"},
    {"n": "58", "step": "Click 'Scroll Right'", "m": "clickable", "st": ["Scroll Right"], "tf": None, "exp": "m59"},
    {"n": "59", "step": "Click 'Add to My List'", "m": "clickable", "st": ["Add to My List"], "tf": None, "exp": "m60"},

    # Episode Selector (61-70)
    {"n": "61", "step": "Select 'Season 2' from 'Season Selector'", "m": "select", "st": ["Season 2", "Season Selector"], "tf": None, "exp": "m61"},
    {"n": "62", "step": "VERIFY 'The Beginning' is present", "ver": True, "res": True},
    {"n": "63", "step": "Click 'Play Episode 1'", "m": "clickable", "st": ["Play Episode 1"], "tf": None, "exp": "m63"},
    {"n": "64", "step": "Click 'Download Episode 1'", "m": "clickable", "st": ["Download Episode 1"], "tf": None, "exp": "m64"},
    {"n": "65", "step": "VERIFY 'The Middle' is present", "ver": True, "res": True},
    {"n": "66", "step": "Click 'Play Episode 2'", "m": "clickable", "st": ["Play Episode 2"], "tf": None, "exp": "m66"},
    {"n": "67", "step": "Click 'Resume from 15:00'", "m": "clickable", "st": ["Resume from 15:00"], "tf": None, "exp": "m67"},
    {"n": "68", "step": "Click 'Play from beginning'", "m": "clickable", "st": ["Play from beginning"], "tf": None, "exp": "m68"},
    {"n": "69", "step": "Click 'Rate this title'", "m": "clickable", "st": ["Rate this title"], "tf": None, "exp": "m69"},
    {"n": "70", "step": "Click 'Remove from My List'", "m": "clickable", "st": ["Remove from My List"], "tf": None, "exp": "m70"},

    # Audio Player (71-79)
    {"n": "71", "step": "Click 'Save to Your Library'", "m": "clickable", "st": ["Save to Your Library"], "tf": None, "exp": "m72"},
    {"n": "72", "step": "Click 'Enable shuffle'", "m": "clickable", "st": ["Enable shuffle"], "tf": None, "exp": "m73"},
    {"n": "73", "step": "Click 'Previous track'", "m": "clickable", "st": ["Previous track"], "tf": None, "exp": "m74"},
    {"n": "74", "step": "Click 'Pause/Play'", "m": "clickable", "st": ["Pause/Play"], "tf": None, "exp": "m75"},
    {"n": "75", "step": "Click 'Next track'", "m": "clickable", "st": ["Next track"], "tf": None, "exp": "m76"},
    {"n": "76", "step": "Click 'Enable repeat'", "m": "clickable", "st": ["Enable repeat"], "tf": None, "exp": "m77"},
    {"n": "77", "step": "Click 'Lyrics'", "m": "clickable", "st": ["Lyrics"], "tf": None, "exp": "m78"},
    {"n": "78", "step": "Click 'Queue'", "m": "clickable", "st": ["Queue"], "tf": None, "exp": "m79"},
    {"n": "79", "step": "Click 'Connect to a device'", "m": "clickable", "st": ["Connect to a device"], "tf": None, "exp": "m80"},

    # Search & Discovery (81-90)
    {"n": "81", "step": "Fill 'Movies, shows, and more' with 'Matrix'", "m": "input", "st": ["Movies, shows, and more"], "tf": "movies, shows, and more", "exp": "m81"},
    {"n": "82", "step": "Click 'Clear Search'", "m": "clickable", "st": ["Clear Search"], "tf": None, "exp": "m82"},
    {"n": "83", "step": "Click 'Filter by Genre'", "m": "clickable", "st": ["Filter by Genre"], "tf": None, "exp": "m83"},
    {"n": "84", "step": "Click the checkbox for 'Action'", "m": "clickable", "st": ["Action"], "tf": None, "exp": "m84"},
    {"n": "85", "step": "Check 'Comedy'", "m": "clickable", "st": ["Comedy"], "tf": None, "exp": "m85"},
    {"n": "86", "step": "Check 'Sci-Fi'", "m": "clickable", "st": ["Sci-Fi"], "tf": None, "exp": "m86"},
    {"n": "87", "step": "Click 'Apply Filters'", "m": "clickable", "st": ["Apply Filters"], "tf": None, "exp": "m87"},
    {"n": "88", "step": "Click 'Podcasts'", "m": "clickable", "st": ["Podcasts"], "tf": None, "exp": "m88"},
    {"n": "89", "step": "Click 'Audiobooks'", "m": "clickable", "st": ["Audiobooks"], "tf": None, "exp": "m89"},
    {"n": "90", "step": "Click 'Live Radio'", "m": "clickable", "st": ["Live Radio"], "tf": None, "exp": "m90"},

    # Edge Cases, Ads & Popups (91-100)
    {"n": "91", "step": "VERIFY 'Ad ends in 5' is present", "ver": True, "res": True},
    {"n": "92", "step": "Click 'Skip Ad'", "m": "clickable", "st": ["Skip Ad"], "tf": None, "exp": "m92"},
    {"n": "93", "step": "Click 'Learn More'", "m": "clickable", "st": ["Learn More"], "tf": None, "exp": "m93"},
    {"n": "94", "step": "VERIFY 'Are you still watching?' is present", "ver": True, "res": True},
    {"n": "95", "step": "Click 'Continue Watching'", "m": "clickable", "st": ["Continue Watching"], "tf": None, "exp": "m95"},
    {"n": "96", "step": "Click 'Go to Homepage'", "m": "clickable", "st": ["Go to Homepage"], "tf": None, "exp": "m96"},
    {"n": "97", "step": "VERIFY 'inappropriate for some users' is present", "ver": True, "res": True},
    {"n": "98", "step": "Click 'I understand and wish to proceed'", "m": "clickable", "st": ["I understand and wish to proceed"], "tf": None, "exp": "m98"},
    {"n": "99", "step": "Click 'Go back'", "m": "clickable", "st": ["Go back"], "tf": None, "exp": "m99"},
    {"n": "100", "step": "Click 'Claim Free Premium' if exists", "m": "clickable", "st": ["Claim Free Premium"], "tf": None, "exp": None}, # Hidden, should skip gracefully
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("🎬 MEDIA & STREAMING HELL: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(MEDIA_DOM)

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