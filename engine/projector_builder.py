import os
import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/projector-throw-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4").strip()
CUSTOM_PROJECTOR = os.environ.get("CUSTOM_PROJECTOR", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_projectors.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (Model Name, Throw Ratio Min, Throw Ratio Max, ANSI Lumens, Throw Type, Native Resolution)
SEED_PROJECTORS = [
    ("Epson Home Cinema 5050UB", 1.35, 2.84, 2600, "Standard Long Throw", "4K PRO-UHD"),
    ("BenQ TK700STi 4K Gaming", 0.90, 1.08, 3000, "Short Throw", "4K UHD (3840x2160)"),
    ("Hisense PX3-Pro TriChroma Laser", 0.22, 0.22, 3000, "Ultra Short Throw (UST)", "4K UHD"),
    ("XGIMI Horizon Ultra 4K Dolby Vision", 1.20, 1.50, 2300, "Standard Throw", "4K UHD"),
    ("Epson Pro Cinema LS12000 4K Laser", 1.35, 2.84, 2700, "Standard Long Throw", "4K PRO-UHD"),
    ("BenQ HT3560 CinePrime 4K", 1.13, 1.46, 2200, "Standard Throw", "4K UHD"),
    ("AWOL Vision LTV-3500 Pro Tri-Laser", 0.25, 0.25, 3500, "Ultra Short Throw (UST)", "4K UHD"),
    ("Optoma UHD55 Smart 4K", 1.21, 1.59, 3600, "Standard Throw", "4K UHD"),
    ("BenQ X3100i 4LED Gaming", 1.15, 1.50, 3300, "Standard Throw", "4K UHD"),
    ("Epson EpiqVision Ultra LS800", 0.16, 0.16, 4000, "Ultra Short Throw (UST)", "4K PRO-UHD"),
    ("NexiGo Aurora Pro MKII 4K Laser", 0.23, 0.23, 2400, "Ultra Short Throw (UST)", "4K UHD"),
    ("Anker Nebula Cosmos 4K SE", 1.20, 1.20, 1800, "Standard Portable Throw", "4K UHD"),
    ("ViewSonic PX748-4K High Brightness", 1.13, 1.47, 4000, "Standard Throw", "4K UHD"),
    ("LG CineBeam Q HU710PB 4K Laser", 1.20, 1.20, 500, "Compact Standard Throw", "4K UHD"),
    ("Formovie Theater Premium 4K UST", 0.21, 0.21, 2800, "Ultra Short Throw (UST)", "4K UHD"),
    ("Sony VPL-XW5000ES Bravia 4K Laser", 1.38, 2.21, 2000, "Standard Long Throw", "Native 4K SXRD"),
    ("JVC DLA-NP5 D-ILA 4K Home Theater", 1.43, 2.92, 1900, "Standard Long Throw", "Native 4K D-ILA"),
    ("BenQHT4550i 4LED Home Theater", 1.15, 1.50, 3200, "Standard Throw", "4K UHD"),
    ("Optoma GT2100HDR Short Throw Laser", 0.49, 0.49, 4200, "Short Throw", "1080p / 4K Input"),
    ("Epson Home Cinema 3800 4K", 1.32, 2.15, 3000, "Standard Throw", "4K PRO-UHD"),
    ("Valerion VisionMaster Pro 2 Triple Laser", 0.90, 1.50, 3000, "Optical Zoom Throw", "4K UHD"),
    ("Samsung The Premiere LSP9T 4K Laser", 0.19, 0.19, 2800, "Ultra Short Throw (UST)", "4K UHD"),
    ("JMGO N1S Ultra 4K Triple Laser", 1.20, 1.20, 3000, "Gimbal Standard Throw", "4K UHD"),
    ("BenQ TH685P 120Hz Gaming", 1.12, 1.46, 3500, "Standard Throw", "1080p / 4K HDR"),
    ("ViewSonic X2-4K Xbox Certified", 0.69, 0.83, 2900, "Short Throw", "4K UHD"),
    ("Hisense C2 Ultra TriChroma Gimbal", 0.90, 1.50, 3000, "Optical Zoom Throw", "4K UHD"),
    ("Epson Home Cinema 2350 Smart Gaming", 1.32, 2.12, 2800, "Standard Throw", "4K PRO-UHD"),
    ("Optoma UHZ50 Smart 4K Laser", 1.21, 1.59, 3000, "Standard Throw", "4K UHD"),
    ("BenQ TK860i 4K HDR Sports", 1.13, 1.47, 3300, "Standard Throw", "4K UHD"),
    ("LG ProBeam BU53RG 4K Short Throw", 0.94, 1.14, 5000, "Short Throw", "4K UHD")
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=1.2):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_projector_queries():
    """Mengambil model proyektor yang sedang dicari di Google Autocomplete US."""
    discovered = []
    brands = ["epson ", "benq ", "optoma ", "hisense ", "xgimi ", "viewsonic ", "awol vision "]
    for brand in brands:
        try:
            q = f"{brand}throw distance"
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(q)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = re.sub(r"\b(throw|distance|calculator|chart|screen|size|manual|specs)\b", "", suggestion, flags=re.IGNORECASE).strip()
                    if 5 <= len(cleaned) <= 42:
                        discovered.append((cleaned.title(), 1.20, 1.50, 2800, "Standard Throw", "4K UHD"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_optical_data(proj_tuple):
    """Mesin Fisika Optik Otomatis (100% bebas gagal) jika Gemini API limit atau kosong."""
    model_name, tr_min, tr_max, lumens, throw_type, resolution = proj_tuple
    is_ust = tr_min < 0.45
    is_short = 0.45 <= tr_min < 1.0

    # Geometri layar 120 inci 16:9: Lebar = 104.6 inci (8.716 kaki), Tinggi = 58.8 inci (4.903 kaki)
    width_120_ft = 8.716
    dist_min_120_ft = round(width_120_ft * tr_min, 1)
    dist_max_120_ft = round(width_120_ft * tr_max, 1)

    if is_ust:
        screen_rec = "120-Inch UST Fresnel / Lenticular ALR Projector Screen Fixed Frame"
        screen_price = "$499 - $899"
        mount_rec = "Ultra Short Throw Projector Telescopic Sliding Tray & Media Stand"
        mount_price = "$89 - $199"
        hdmi_rec = "10ft 48Gbps 8K Ultra High Speed Braided HDMI 2.1 Cable"
        hdmi_price = "$19 - $35"
    elif is_short:
        screen_rec = "120-Inch 4K CineGrey 1.1 Gain Fixed Frame Projector Screen"
        screen_price = "$269 - $499"
        mount_rec = "Low-Profile Micro-Adjustable Universal Projector Ceiling Mount"
        mount_price = "$34 - $69"
        hdmi_rec = "25ft Active Optical Fiber 48Gbps 8K HDMI 2.1 In-Wall CL3 Cable"
        hdmi_price = "$45 - $79"
    else:
        screen_rec = "120-Inch 4K Acoustic Transparent / CineWhite Fixed Frame Screen"
        screen_price = "$249 - $479"
        mount_rec = "Heavy-Duty Geared Precision Projector Ceiling Mount with Extension Pole"
        mount_price = "$42 - $89"
        hdmi_rec = "50ft Active Optical Fiber 48Gbps 8K60/4K120 HDMI 2.1 In-Wall Cable"
        hdmi_price = "$59 - $99"

    dist_summary = (
        f"{dist_min_120_ft} ft ({round(dist_min_120_ft * 12)} inches)"
        if tr_min == tr_max
        else f"between {dist_min_120_ft} ft and {dist_max_120_ft} ft"
    )

    return {
        "model_name": model_name,
        "seo_title": f"{model_name} Throw Distance & Screen Size Calculator (2026)",
        "meta_description": f"Interactive {model_name} throw distance calculator. Calculate exact lens-to-screen distance ({dist_summary} for 120\"), ceiling mount offset, and ALR screen size.",
        "specs": {
            "throw_ratio_min": tr_min,
            "throw_ratio_max": tr_max,
            "ansi_lumens": lumens,
            "throw_type": throw_type,
            "native_resolution": resolution
        },
        "optical_verdict": f"The {model_name} features a {tr_min}:1 to {tr_max}:1 optical throw ratio ({throw_type}) and {lumens} ANSI lumens output. To project a standard 120-inch diagonal 16:9 image (104.6\" wide × 58.8\" high), position the front lens element {dist_summary} away from the screen surface.",
        "hardware_bundle": [
            {
                "category_badge": "Projector Unit",
                "title": f"{model_name} Home Theater Projector",
                "price_range": "$699 - $2,499",
                "amazon_query": f"{model_name} Projector",
                "pro_tip": f"Delivers {lumens} ANSI lumens in {resolution} resolution. Always enable Eco/Cinema lamp mode after initial calibration for lower fan noise."
            },
            {
                "category_badge": "Matched Screen Surface",
                "title": screen_rec,
                "price_range": screen_price,
                "amazon_query": screen_rec,
                "pro_tip": "Matched specifically to the optical incidence angle of this lens to maximize contrast and reject ceiling scatter."
            },
            {
                "category_badge": "Mounting Hardware",
                "title": mount_rec,
                "price_range": mount_price,
                "amazon_query": mount_rec,
                "pro_tip": "Always square the physical lens housing perpendicular to the screen center before touching digital keystone."
            },
            {
                "category_badge": "Zero-Loss Signal Run",
                "title": hdmi_rec,
                "price_range": hdmi_price,
                "amazon_query": hdmi_rec,
                "pro_tip": "Directional Active Optical Fiber (AOC) prevents 4K HDR 10-bit handshake dropouts over long ceiling runs."
            }
        ],
        "calibration_checklist": [
            f"Position the {model_name} lens {dist_summary} from the wall for a 120-inch 16:9 image before drilling ceiling mount holes.",
            "Avoid using Digital Keystone Correction; it crops native 4K pixel resolution and increases gaming input lag. Use optical zoom or physical mount height instead.",
            "Install a CL3-rated Active Optical HDMI 2.1 cable in the wall/ceiling with the 'Source' plug connected to your AV Receiver and 'Display' plug at the projector.",
            f"Pair the {lumens}-lumen light engine with a 1.0 to 1.1 gain matte white screen in dark rooms, or a 0.8 gain ALR screen in rooms with ambient window light."
        ],
        "faqs": [
            {
                "q": f"How far back does the {model_name} need to be for a 120-inch screen?",
                "a": f"With a throw ratio of {tr_min}:1 to {tr_max}:1 and a 120-inch 16:9 screen width of 104.6 inches (8.72 feet), the {model_name} lens must be placed {dist_summary} from the projection screen."
            },
            {
                "q": f"What distance is needed for a 100-inch screen on the {model_name}?",
                "a": f"A 100-inch 16:9 screen measures 87.2 inches (7.26 feet) wide. Multiplying by the throw ratio gives a required throw distance of {round(7.26 * tr_min, 1)} ft to {round(7.26 * tr_max, 1)} ft."
            },
            {
                "q": f"What is the ideal seating distance for a 120-inch screen with the {model_name}?",
                "a": f"Following SMPTE (30-degree field of view) and THX (40-degree cinema immersion) guidelines, the optimal viewing distance for a 120-inch 4K screen is between 11.8 feet and 16.0 feet."
            }
        ]
    }


def generate_projector_data(proj_tuple):
    """Memanggil Gemini 2.5 Flash API; jika gagal otomatis memakai Deterministic Optical Engine."""
    if not GEMINI_API_KEY:
        return build_deterministic_optical_data(proj_tuple)

    model_name, tr_min, tr_max, lumens, throw_type, resolution = proj_tuple
    prompt = f"""
You are a CEDIA Certified Home Theater & Optical Calibration Engineer. Create an accurate 2026 throw distance, screen sizing, and hardware setup guide for: "{model_name}".
Baseline reference specs: Throw Ratio Min={tr_min}, Throw Ratio Max={tr_max}, Brightness={lumens} ANSI Lumens, Type={throw_type}, Resolution={resolution}.
Return ONLY a valid JSON object matching this exact schema:
{{
  "model_name": "{model_name}",
  "seo_title": "{model_name} Throw Distance & Screen Size Calculator (2026)",
  "meta_description": "Calculate exact lens-to-screen throw distance, screen dimensions, and ceiling mount placement for the {model_name}.",
  "specs": {{
    "throw_ratio_min": {tr_min},
    "throw_ratio_max": {tr_max},
    "ansi_lumens": {lumens},
    "throw_type": "{throw_type}",
    "native_resolution": "{resolution}"
  }},
  "optical_verdict": "3-sentence technical summary stating exact throw ratio, ANSI lumens, and exact distance in feet for a 120-inch 16:9 screen.",
  "hardware_bundle": [
    {{
      "category_badge": "Projector Unit",
      "title": "{model_name}",
      "price_range": "$799 - $2,499",
      "amazon_query": "{model_name} projector",
      "pro_tip": "1-sentence calibration tip"
    }},
    {{
      "category_badge": "Matched Screen Surface",
      "title": "Exact 120-Inch 4K Screen recommendation",
      "price_range": "$249 - $699",
      "amazon_query": "120 inch 4K ALR fixed frame projector screen",
      "pro_tip": "1-sentence screen gain tip"
    }},
    {{
      "category_badge": "Mounting Hardware",
      "title": "Exact Ceiling Mount or UST Stand",
      "price_range": "$39 - $129",
      "amazon_query": "universal micro adjustable projector ceiling mount",
      "pro_tip": "1-sentence alignment tip"
    }},
    {{
      "category_badge": "Fiber HDMI 2.1 Interconnect",
      "title": "Active Optical 48Gbps 8K HDMI 2.1 Cable",
      "price_range": "$39 - $89",
      "amazon_query": "50ft active optical fiber 48gbps hdmi 2.1 cable",
      "pro_tip": "1-sentence wiring tip"
    }}
  ],
  "calibration_checklist": [
    "Step 1 optical placement tip",
    "Step 2 keystone vs lens shift tip",
    "Step 3 HDMI cabling tip",
    "Step 4 ambient light & screen gain tip"
  ],
  "faqs": [
    {{"q": "How far back does the {model_name} need to be for a 120-inch screen?", "a": "Exact distance in feet and inches."}},
    {{"q": "What distance is required for a 100-inch screen on the {model_name}?", "a": "Exact distance in feet and inches."}},
    {{"q": "Can I ceiling mount the {model_name}?", "a": "Detailed mounting and offset answer."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")

    return build_deterministic_optical_data(proj_tuple)


def build_projector_html_page(data, slug, mon_cfg):
    model_name = data.get("model_name", "4K Projector")
    sp = data.get("specs", {})
    tr_min = round(safe_float(sp.get("throw_ratio_min", 1.20), 1.20), 2)
    tr_max = round(safe_float(sp.get("throw_ratio_max", tr_min), tr_min), 2)
    if tr_max < tr_min:
        tr_max = tr_min
    lumens = int(safe_float(sp.get("ansi_lumens", 2600), 2600))
    throw_type = sp.get("throw_type", "Standard Throw")
    resolution = sp.get("native_resolution", "4K UHD")

    promo = mon_cfg.get("header_promo", {})
    promo_url = build_amazon_url(promo.get("search_query", "120+Inch+4K+ALR+Projector+Screen"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{model_name} Throw Distance & Screen Size Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "4K Projector")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-violet-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-violet-500/10 text-violet-400 border border-violet-500/20 px-2.5 py-0.5 rounded">{item.get('category_badge', 'AV Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$99+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🎬 {item.get('pro_tip', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-violet-500 hover:bg-violet-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build quick reference distance table for 80", 100", 110", 120", 135", 150"
    size_rows_html = ""
    for diag in [80, 100, 110, 120, 135, 150]:
        w_in = round(diag * 0.8716, 1)
        h_in = round(diag * 0.4903, 1)
        d_min_ft = round((w_in * tr_min) / 12.0, 1)
        d_max_ft = round((w_in * tr_max) / 12.0, 1)
        dist_cell = f"{d_min_ft} ft ({round(d_min_ft*12)}\")" if tr_min == tr_max else f"{d_min_ft} ft – {d_max_ft} ft"
        size_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{diag}\" Diagonal</td>
          <td class="py-3 px-4 text-zinc-300">{w_in}\" W × {h_in}\" H</td>
          <td class="py-3 px-4 font-bold text-violet-400">{dist_cell}</td>
          <td class="py-3 px-4 text-emerald-400">{round(diag * 0.098, 1)} ft – {round(diag * 0.133, 1)} ft</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("calibration_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-violet-500 rounded cursor-pointer cal-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', model_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', model_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-violet-500 text-zinc-950 px-2 py-0.5 rounded font-black">THROW</span>CalcIndex
      </a>
      <a href="{promo_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-violet-500 hover:bg-violet-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {promo.get('cta_text', 'Shop 4K ALR Screens →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-violet-500 text-zinc-950 px-3 py-1 rounded-full">{throw_type}</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Throw Ratio: {tr_min}:1 – {tr_max}:1</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">{lumens} ANSI Lumens | {resolution}</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', model_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-violet-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>CEDIA Optical Summary:</strong> {data.get('optical_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE THROW DISTANCE & SCREEN SIZING CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {model_name} Throw Distance & Screen Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Slide your target screen diagonal size and aspect ratio to compute exact lens-to-screen throw distance, viewing dimensions, and required HDMI cable run.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="diagSlider" class="text-zinc-300">Target Screen Diagonal Size (Inches)</label>
              <span class="text-violet-400 font-bold"><span id="diagVal">120</span>" Diagonal</span>
            </div>
            <input id="diagSlider" type="range" min="65" max="180" step="5" value="120" class="w-full accent-violet-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="aspectSelect" class="text-zinc-300">Projection Aspect Ratio</label>
              <span class="text-xs text-zinc-400">Native Geometry</span>
            </div>
            <select id="aspectSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-violet-500">
              <option value="16:9" selected>16:9 HDTV / 4K UHD (Standard)</option>
              <option value="2.39:1">2.39:1 CinemaScope Widescreen</option>
              <option value="16:10">16:10 WUXGA Commercial</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-violet-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-violet-400 font-bold">Required Lens Distance</span>
            <div id="throwDistOut" class="text-xl sm:text-2xl font-black text-white mt-1">0 ft</div>
            <p class="text-xs text-zinc-500 mt-1">Optical Zoom Min – Max Range</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Screen Width × Height</span>
            <div id="screenDimOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">105" × 59"</div>
            <p id="seatDistOut" class="text-xs text-zinc-400 mt-1">THX Seating: 12.0 ft</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-violet-950/40 border border-violet-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div class="text-sm text-violet-100 font-medium">
          📐 Recommended Screen & Cable Run: <strong class="text-violet-300"><span id="recScreenText">120</span>" 4K ALR Screen</strong> + <strong class="text-emerald-300"><span id="recHdmiText">35</span>ft Fiber HDMI 2.1</strong>
        </div>
        <a id="dynamicScreenBtn" href="{promo_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-violet-500 hover:bg-violet-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop <span id="btnDiagText">120</span>" 4K Screen on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HIGH-TICKET HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {model_name} Home Theater Hardware Bundle</h2>
        <span class="text-xs text-zinc-400">Matched Optical & HDMI 2.1 Components</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- THROW DISTANCE CHART TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">{model_name} Throw Distance Chart (16:9 Aspect Ratio)</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">Screen Diagonal</th>
              <th class="py-3.5 px-4">Viewing Width × Height</th>
              <th class="py-3.5 px-4 text-violet-400">Lens Throw Distance</th>
              <th class="py-3.5 px-4 text-emerald-400">THX / SMPTE Seating Range</th>
            </tr>
          </thead>
          <tbody>{size_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- CALIBRATION CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Optical Installation & Calibration Checklist</h2>
        <span id="calBadge" class="text-xs font-bold bg-zinc-800 text-violet-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({model_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} ThrowCalcIndex. Independent Home Theater Optical Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const trMin = {tr_min};
    const trMax = {tr_max};
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const diagSlider = document.getElementById('diagSlider');
    const aspectSelect = document.getElementById('aspectSelect');
    const diagVal = document.getElementById('diagVal');
    const throwDistOut = document.getElementById('throwDistOut');
    const screenDimOut = document.getElementById('screenDimOut');
    const seatDistOut = document.getElementById('seatDistOut');
    const recScreenText = document.getElementById('recScreenText');
    const recHdmiText = document.getElementById('recHdmiText');
    const btnDiagText = document.getElementById('btnDiagText');
    const dynamicScreenBtn = document.getElementById('dynamicScreenBtn');

    function recalculateOptics() {{
      const diag = parseInt(diagSlider.value, 10);
      const aspect = aspectSelect.value;

      diagVal.textContent = diag;
      recScreenText.textContent = diag;
      btnDiagText.textContent = diag;

      let wFactor = 0.8716;
      let hFactor = 0.4903;
      if (aspect === '2.39:1') {{
        wFactor = 0.9218;
        hFactor = 0.3857;
      }} else if (aspect === '16:10') {{
        wFactor = 0.8480;
        hFactor = 0.5300;
      }}

      const widthIn = diag * wFactor;
      const heightIn = diag * hFactor;
      const distMinFt = (widthIn * trMin) / 12.0;
      const distMaxFt = (widthIn * trMax) / 12.0;

      if (Math.abs(trMax - trMin) < 0.02) {{
        throwDistOut.textContent = `${{distMinFt.toFixed(1)}} ft (${{Math.round(distMinFt * 12)}}")`;
      }} else {{
        throwDistOut.textContent = `${{distMinFt.toFixed(1)}} – ${{distMaxFt.toFixed(1)}} ft`;
      }}

      screenDimOut.textContent = `${{Math.round(widthIn)}}" W × ${{Math.round(heightIn)}}" H`;
      seatDistOut.textContent = `Ideal Seating: ${{(diag * 0.10).toFixed(1)}} – ${{(diag * 0.13).toFixed(1)}} ft`;

      const cableRunFt = distMaxFt < 3 ? 10 : Math.ceil((distMaxFt + 15) / 10) * 10;
      recHdmiText.textContent = cableRunFt;

      const screenTypeQuery = trMin < 0.45 ? 'UST+ALR+Projector+Screen' : '4K+ALR+Fixed+Frame+Projector+Screen';
      dynamicScreenBtn.href = `https://${{amzDomain}}/s?k=${{diag}}+Inch+${{screenTypeQuery}}&tag=${{amzTag}}`;
    }}

    diagSlider.addEventListener('input', recalculateOptics);
    aspectSelect.addEventListener('change', recalculateOptics);
    recalculateOptics();

    const checks = document.querySelectorAll('.cal-check');
    const badge = document.getElementById('calBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    promo = mon_cfg.get("header_promo", {})
    promo_url = build_amazon_url(promo.get("search_query", "120+Inch+4K+ALR+Projector+Screen"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-violet-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-violet-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('throw_ratio_badge', '1.2:1 Throw')}</span>
            <span class="text-xs text-zinc-400">{item.get('lumens', 2600)} Lumens</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-violet-400 transition">{item['model_name']} Throw Distance Calculator</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-violet-400">Open Screen & Distance Calculator →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ThrowCalcIndex — 4K Projector Throw Distance & Screen Size Calculators (2026)</title>
  <meta name="description" content="Interactive projector throw distance, screen dimension, and ceiling mount calculators for Epson, BenQ, Hisense, Optoma, XGIMI, and Sony 4K projectors.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="ThrowCalcIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-violet-500 text-zinc-950 px-2 py-0.5 rounded font-black">THROW</span>CalcIndex
      </div>
      <a href="{promo_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-violet-500 hover:bg-violet-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {promo.get('cta_text', 'Shop 4K ALR Projector Screens →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">4K Projector Throw Distance & Screen Sizing Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your projector model below to calculate exact lens-to-screen throw distance, 100"–150" screen dimensions, and required HDMI 2.1 cable run.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search projector model (e.g. Epson 5050UB, BenQ TK700STi, Hisense PX3, UST, Short Throw...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-violet-500">
      </div>
    </div>

    <div id="projGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} ThrowCalcIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('projGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>ThrowCalcIndex 4K Projector Optical Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Home Theater Projector Throw Distance & Screen Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_PROJECTOR:
        candidates.append((CUSTOM_PROJECTOR.strip(), 1.20, 1.50, 2800, "Standard Throw", "4K UHD"))
    candidates.extend(SEED_PROJECTORS)
    candidates.extend(discover_google_projector_queries())

    new_urls = []
    count = 0

    for proj_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        model_name = proj_tuple[0]
        slug = slugify(f"{model_name}-throw-distance-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating optical calculator for: {model_name}...")
        try:
            data = generate_projector_data(proj_tuple)
            build_projector_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})
            tr_min = round(safe_float(sp.get("throw_ratio_min", proj_tuple[1]), proj_tuple[1]), 2)
            tr_max = round(safe_float(sp.get("throw_ratio_max", proj_tuple[2]), proj_tuple[2]), 2)
            badge = f"{tr_min}:1 UST" if tr_min < 0.45 else f"{tr_min}–{tr_max}:1 Throw"

            published.append({
                "model_name": data.get("model_name", model_name),
                "slug": slug,
                "title": data.get("seo_title", f"{model_name} Throw Distance Calculator"),
                "description": data.get("meta_description", ""),
                "throw_ratio_badge": badge,
                "lumens": int(safe_float(sp.get("ansi_lumens", proj_tuple[3]), proj_tuple[3])),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed generating {model_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new projector throw calculator pages.")


if __name__ == "__main__":
    main()
