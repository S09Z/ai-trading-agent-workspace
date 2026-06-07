"""
Stock universe for DiscoveryAgent — ~400 tickers across NASDAQ / NYSE.
Covers major sectors: Tech, Semis, SaaS, AI, Biotech, EV, Energy, Fintech.
"""
from typing import TypedDict


class StockInfo(TypedDict):
    ticker: str
    company: str
    sector: str
    business: str


UNIVERSE: list[StockInfo] = [
    # ── Big Tech / Platform ───────────────────────────────────────────────────
    {"ticker": "AAPL",  "company": "Apple",            "sector": "Big Tech",     "business": "Consumer electronics, iOS ecosystem, App Store, Services"},
    {"ticker": "MSFT",  "company": "Microsoft",        "sector": "Big Tech",     "business": "Cloud (Azure), Office 365, Teams, AI (Copilot), LinkedIn"},
    {"ticker": "GOOGL", "company": "Alphabet",         "sector": "Big Tech",     "business": "Search ads, YouTube, Cloud (GCP), AI (Gemini), Waymo"},
    {"ticker": "GOOG",  "company": "Alphabet Class C", "sector": "Big Tech",     "business": "Same as GOOGL — non-voting shares"},
    {"ticker": "META",  "company": "Meta Platforms",   "sector": "Big Tech",     "business": "Social media (Facebook, Instagram, WhatsApp), AR/VR (Quest)"},
    {"ticker": "AMZN",  "company": "Amazon",           "sector": "Big Tech",     "business": "E-commerce, Cloud (AWS #1), Ads, Prime, Alexa"},
    {"ticker": "NFLX",  "company": "Netflix",          "sector": "Big Tech",     "business": "Streaming entertainment, ad-supported tier, live events"},

    # ── Semiconductors — Chips ────────────────────────────────────────────────
    {"ticker": "NVDA",  "company": "NVIDIA",           "sector": "Semiconductors", "business": "AI GPU (H100/B200), data center, CUDA ecosystem, robotics"},
    {"ticker": "AMD",   "company": "Advanced Micro Devices", "sector": "Semiconductors", "business": "CPU (EPYC), GPU (Instinct), AI inference chips"},
    {"ticker": "INTC",  "company": "Intel",            "sector": "Semiconductors", "business": "x86 CPU, foundry (IFS), competing with TSMC"},
    {"ticker": "AVGO",  "company": "Broadcom",         "sector": "Semiconductors", "business": "Networking chips, custom AI silicon, VMware (cloud software)"},
    {"ticker": "QCOM",  "company": "Qualcomm",         "sector": "Semiconductors", "business": "Mobile SoC (Snapdragon), 5G modems, automotive chips"},
    {"ticker": "TXN",   "company": "Texas Instruments","sector": "Semiconductors", "business": "Analog/embedded chips — industrial, automotive, IoT"},
    {"ticker": "MRVL",  "company": "Marvell Technology","sector": "Semiconductors","business": "Data center networking chips, custom AI silicon (Amazon, Google)"},
    {"ticker": "MU",    "company": "Micron Technology","sector": "Semiconductors", "business": "DRAM, NAND flash memory — AI server memory (HBM)"},
    {"ticker": "ON",    "company": "ON Semiconductor", "sector": "Semiconductors", "business": "Power semiconductors for EV and industrial"},
    {"ticker": "MCHP",  "company": "Microchip Technology","sector": "Semiconductors","business": "Microcontrollers, FPGAs, analog — industrial/auto"},
    {"ticker": "ADI",   "company": "Analog Devices",   "sector": "Semiconductors", "business": "High-performance analog/mixed-signal chips"},
    {"ticker": "SWKS",  "company": "Skyworks Solutions","sector": "Semiconductors","business": "RF chips for smartphones (Apple supplier)"},
    {"ticker": "MPWR",  "company": "Monolithic Power", "sector": "Semiconductors", "business": "Power management ICs for AI servers, EVs"},
    {"ticker": "NXPI",  "company": "NXP Semiconductors","sector": "Semiconductors","business": "Automotive chips, IoT, secure identity"},
    {"ticker": "SMCI",  "company": "Super Micro Computer","sector": "Semiconductors","business": "AI server hardware, GPU racks (NVIDIA partner)"},
    {"ticker": "TSM",   "company": "TSMC",             "sector": "Semiconductors", "business": "Foundry — manufactures chips for Apple, NVIDIA, AMD"},
    {"ticker": "ASML",  "company": "ASML Holding",     "sector": "Semiconductors", "business": "EUV lithography machines — monopoly in advanced chip production"},
    {"ticker": "AMAT",  "company": "Applied Materials","sector": "Semiconductors", "business": "Semiconductor manufacturing equipment (CVD, PVD)"},
    {"ticker": "LRCX",  "company": "Lam Research",     "sector": "Semiconductors", "business": "Etch/deposition equipment for chip fabrication"},
    {"ticker": "KLAC",  "company": "KLA Corporation",  "sector": "Semiconductors", "business": "Semiconductor process control / inspection equipment"},
    {"ticker": "STX",   "company": "Seagate Technology","sector": "Semiconductors","business": "Hard disk drives, cloud storage"},
    {"ticker": "WDC",   "company": "Western Digital",  "sector": "Semiconductors", "business": "NAND flash, HDDs, cloud storage"},
    {"ticker": "WOLF",  "company": "Wolfspeed",        "sector": "Semiconductors", "business": "Silicon carbide (SiC) chips for EV powertrains"},

    # ── Software / SaaS / Enterprise ─────────────────────────────────────────
    {"ticker": "ADBE",  "company": "Adobe",            "sector": "Software",     "business": "Creative Cloud, Acrobat, AI tools (Firefly), digital media"},
    {"ticker": "CRM",   "company": "Salesforce",       "sector": "Software",     "business": "CRM, Einstein AI, Slack, MuleSoft — enterprise cloud"},
    {"ticker": "ORCL",  "company": "Oracle",           "sector": "Software",     "business": "Database (OCI cloud), ERP, NetSuite, AI infrastructure"},
    {"ticker": "IBM",   "company": "IBM",              "sector": "Software",     "business": "Enterprise IT, consulting, hybrid cloud, watsonx AI"},
    {"ticker": "NOW",   "company": "ServiceNow",       "sector": "Software",     "business": "IT workflow automation, AI-powered enterprise platform"},
    {"ticker": "WDAY",  "company": "Workday",          "sector": "Software",     "business": "HR and finance cloud SaaS (HCM, ERP)"},
    {"ticker": "TEAM",  "company": "Atlassian",        "sector": "Software",     "business": "Developer tools (Jira, Confluence, Bitbucket)"},
    {"ticker": "HUBS",  "company": "HubSpot",          "sector": "Software",     "business": "Marketing/CRM SaaS for SMBs, AI-powered"},
    {"ticker": "VEEV",  "company": "Veeva Systems",    "sector": "Software",     "business": "Cloud software for life sciences / pharma"},
    {"ticker": "COUP",  "company": "Coupa Software",   "sector": "Software",     "business": "Business spend management (BSM) SaaS"},
    {"ticker": "ZM",    "company": "Zoom Video",       "sector": "Software",     "business": "Video conferencing, Zoom AI Companion"},
    {"ticker": "DOCU",  "company": "DocuSign",         "sector": "Software",     "business": "E-signature, contract lifecycle management"},
    {"ticker": "TWLO",  "company": "Twilio",           "sector": "Software",     "business": "Cloud communications API (SMS, voice, email)"},
    {"ticker": "MDB",   "company": "MongoDB",          "sector": "Software",     "business": "NoSQL document database, Atlas cloud platform"},
    {"ticker": "ESTC",  "company": "Elastic",          "sector": "Software",     "business": "Search & observability platform (Elasticsearch)"},
    {"ticker": "GTLB",  "company": "GitLab",           "sector": "Software",     "business": "DevSecOps platform, AI code assistant"},
    {"ticker": "DDOG",  "company": "Datadog",          "sector": "Software",     "business": "Cloud observability, APM, log management, AI monitoring"},
    {"ticker": "SMAR",  "company": "Smartsheet",       "sector": "Software",     "business": "Work management / project collaboration SaaS"},

    # ── Cloud Security / Cybersecurity ────────────────────────────────────────
    {"ticker": "CRWD",  "company": "CrowdStrike",      "sector": "Cybersecurity","business": "Endpoint security, XDR, Falcon platform (AI-native)"},
    {"ticker": "ZS",    "company": "Zscaler",          "sector": "Cybersecurity","business": "Zero-trust network security (SASE, cloud proxy)"},
    {"ticker": "OKTA",  "company": "Okta",             "sector": "Cybersecurity","business": "Identity & access management (SSO, MFA)"},
    {"ticker": "PANW",  "company": "Palo Alto Networks","sector": "Cybersecurity","business": "Firewall, SASE, SOC automation, Cortex XDR"},
    {"ticker": "FTNT",  "company": "Fortinet",         "sector": "Cybersecurity","business": "Network security, FortiGate firewall, SD-WAN"},
    {"ticker": "NET",   "company": "Cloudflare",       "sector": "Cybersecurity","business": "CDN, DDoS protection, zero-trust, AI gateway"},
    {"ticker": "S",     "company": "SentinelOne",      "sector": "Cybersecurity","business": "AI-powered endpoint detection & response (EDR)"},
    {"ticker": "TENB",  "company": "Tenable",          "sector": "Cybersecurity","business": "Vulnerability management (Nessus)"},
    {"ticker": "CYBR",  "company": "CyberArk",         "sector": "Cybersecurity","business": "Privileged access management (PAM)"},

    # ── AI / Data Infrastructure ──────────────────────────────────────────────
    {"ticker": "PLTR",  "company": "Palantir",         "sector": "AI / Data",    "business": "AI platform (AIP), government/defense analytics, Foundry"},
    {"ticker": "AI",    "company": "C3.ai",            "sector": "AI / Data",    "business": "Enterprise AI applications, government contracts"},
    {"ticker": "SNOW",  "company": "Snowflake",        "sector": "AI / Data",    "business": "Cloud data warehouse, Snowpark, AI/ML workloads"},
    {"ticker": "DBX",   "company": "Dropbox",          "sector": "AI / Data",    "business": "Cloud storage, Dash AI document search"},
    {"ticker": "SOUN",  "company": "SoundHound AI",    "sector": "AI / Data",    "business": "Voice AI platform for automotive and restaurants"},
    {"ticker": "BBAI",  "company": "BigBear.ai",       "sector": "AI / Data",    "business": "AI decision intelligence for defense/gov"},
    {"ticker": "IREN",  "company": "Iris Energy",      "sector": "AI / Data",    "business": "Bitcoin mining + AI cloud compute (GPU rental)"},
    {"ticker": "CORZ",  "company": "Core Scientific",  "sector": "AI / Data",    "business": "Bitcoin mining + HPC/AI data center infrastructure"},
    {"ticker": "TEM",   "company": "Tempus AI",        "sector": "AI / Data",    "business": "AI-driven precision medicine, genomics data platform"},

    # ── Cloud Infrastructure / Data Center REITs ──────────────────────────────
    {"ticker": "EQIX",  "company": "Equinix",          "sector": "Infrastructure","business": "Global data center REIT, interconnection hubs"},
    {"ticker": "AMT",   "company": "American Tower",   "sector": "Infrastructure","business": "Cell tower REIT, 5G infrastructure globally"},
    {"ticker": "DLR",   "company": "Digital Realty",   "sector": "Infrastructure","business": "Data center REIT (hyperscale + colocation)"},
    {"ticker": "CCI",   "company": "Crown Castle",     "sector": "Infrastructure","business": "US cell tower and small cell REIT"},
    {"ticker": "CSCO",  "company": "Cisco",            "sector": "Infrastructure","business": "Enterprise networking, cybersecurity, Splunk"},

    # ── Internet / E-commerce / Consumer Tech ────────────────────────────────
    {"ticker": "SHOP",  "company": "Shopify",          "sector": "E-commerce",   "business": "E-commerce platform for SMBs, Shopify Payments, fulfillment"},
    {"ticker": "ETSY",  "company": "Etsy",             "sector": "E-commerce",   "business": "Online marketplace for handmade/vintage goods"},
    {"ticker": "EBAY",  "company": "eBay",             "sector": "E-commerce",   "business": "Online marketplace, collectibles, payments"},
    {"ticker": "PINS",  "company": "Pinterest",        "sector": "Internet",     "business": "Visual discovery / social commerce, AI-powered ads"},
    {"ticker": "SNAP",  "company": "Snap",             "sector": "Internet",     "business": "Ephemeral social media (Snapchat), AR Spectacles, ads"},
    {"ticker": "UBER",  "company": "Uber",             "sector": "Internet",     "business": "Ride-hailing, Uber Eats, autonomous vehicle partnerships"},
    {"ticker": "LYFT",  "company": "Lyft",             "sector": "Internet",     "business": "Ride-hailing (US/Canada only)"},
    {"ticker": "ABNB",  "company": "Airbnb",           "sector": "Internet",     "business": "Short-term rental marketplace, Experiences"},
    {"ticker": "BKNG",  "company": "Booking Holdings","sector": "Internet",     "business": "Online travel (Booking.com, Priceline, Kayak)"},
    {"ticker": "EXPE",  "company": "Expedia",          "sector": "Internet",     "business": "Online travel (Expedia, Hotels.com, Vrbo)"},
    {"ticker": "DASH",  "company": "DoorDash",         "sector": "Internet",     "business": "Food delivery, DashPass, international expansion"},
    {"ticker": "RBLX",  "company": "Roblox",           "sector": "Internet",     "business": "User-generated gaming metaverse, young demographic"},
    {"ticker": "RDDT",  "company": "Reddit",           "sector": "Internet",     "business": "Social news aggregator, AI data licensing, ads"},

    # ── Fintech / Payments / Crypto ───────────────────────────────────────────
    {"ticker": "V",     "company": "Visa",             "sector": "Fintech",      "business": "Global payments network, card processing"},
    {"ticker": "MA",    "company": "Mastercard",       "sector": "Fintech",      "business": "Global payments network, card processing"},
    {"ticker": "AXP",   "company": "American Express", "sector": "Fintech",      "business": "Charge cards, travel rewards, high-income consumers"},
    {"ticker": "PYPL",  "company": "PayPal",           "sector": "Fintech",      "business": "Digital payments, Venmo, Braintree, BNPL"},
    {"ticker": "SQ",    "company": "Block (Square)",   "sector": "Fintech",      "business": "Merchant payments, Cash App, Bitcoin services"},
    {"ticker": "AFRM",  "company": "Affirm",           "sector": "Fintech",      "business": "Buy now pay later (BNPL), Amazon/Shopify partner"},
    {"ticker": "SOFI",  "company": "SoFi Technologies","sector": "Fintech",      "business": "Digital bank, student loans, investing, crypto"},
    {"ticker": "COIN",  "company": "Coinbase",         "sector": "Fintech",      "business": "Crypto exchange, custody, Base L2 blockchain"},
    {"ticker": "MSTR",  "company": "MicroStrategy",    "sector": "Fintech",      "business": "Bitcoin treasury strategy, software analytics"},
    {"ticker": "HOOD",  "company": "Robinhood",        "sector": "Fintech",      "business": "Commission-free trading app, crypto, retirement"},
    {"ticker": "NDAQ",  "company": "Nasdaq Inc.",      "sector": "Fintech",      "business": "Exchange operator, market technology, financial data"},
    {"ticker": "ICE",   "company": "Intercontinental Exchange","sector": "Fintech","business": "NYSE operator, mortgage tech (ICE), derivatives"},
    {"ticker": "ADYEY", "company": "Adyen",            "sector": "Fintech",      "business": "Global payment processing for large enterprises"},

    # ── Healthcare / Biotech ──────────────────────────────────────────────────
    {"ticker": "AMGN",  "company": "Amgen",            "sector": "Biotech",      "business": "Biologics (oncology, rare disease), obesity drug pipeline"},
    {"ticker": "GILD",  "company": "Gilead Sciences",  "sector": "Biotech",      "business": "Antiviral drugs (HIV, hepatitis), oncology"},
    {"ticker": "BIIB",  "company": "Biogen",           "sector": "Biotech",      "business": "Neurology drugs (Alzheimer's — Leqembi), MS treatments"},
    {"ticker": "REGN",  "company": "Regeneron",        "sector": "Biotech",      "business": "Biologics (Dupixent, EYLEA), oncology"},
    {"ticker": "VRTX",  "company": "Vertex Pharma",    "sector": "Biotech",      "business": "Cystic fibrosis (Trikafta), gene editing (CRISPR)"},
    {"ticker": "MRNA",  "company": "Moderna",          "sector": "Biotech",      "business": "mRNA platform, COVID vaccines, cancer vaccines"},
    {"ticker": "BNTX",  "company": "BioNTech",         "sector": "Biotech",      "business": "mRNA cancer immunotherapy, BNT111, COVID partnership"},
    {"ticker": "ILMN",  "company": "Illumina",         "sector": "Biotech",      "business": "DNA sequencing machines — genomics research & clinical"},
    {"ticker": "NTRA",  "company": "Natera",           "sector": "Biotech",      "business": "Cell-free DNA testing (prenatal, cancer screening)"},
    {"ticker": "EXAS",  "company": "Exact Sciences",   "sector": "Biotech",      "business": "Cancer screening (Cologuard), Oncotype DX"},
    {"ticker": "PACB",  "company": "Pacific Biosciences","sector": "Biotech",    "business": "Long-read DNA sequencing (SMRT technology)"},
    {"ticker": "BEAM",  "company": "Beam Therapeutics","sector": "Biotech",      "business": "Base editing gene therapy (hematology, oncology)"},
    {"ticker": "EDIT",  "company": "Editas Medicine",  "sector": "Biotech",      "business": "CRISPR-based gene editing therapies"},
    {"ticker": "CRSP",  "company": "CRISPR Therapeutics","sector": "Biotech",    "business": "CRISPR gene editing (Casgevy — sickle cell cure)"},
    {"ticker": "NVAX",  "company": "Novavax",          "sector": "Biotech",      "business": "Protein-based vaccines (COVID, flu)"},
    {"ticker": "SRPT",  "company": "Sarepta Therapeutics","sector": "Biotech",   "business": "Gene therapy for Duchenne muscular dystrophy"},
    {"ticker": "BLUE",  "company": "bluebird bio",     "sector": "Biotech",      "business": "Gene therapy for severe genetic diseases"},
    {"ticker": "FATE",  "company": "Fate Therapeutics","sector": "Biotech",      "business": "iPSC-derived cell therapies for cancer"},

    # ── Medical Devices / Health Tech ────────────────────────────────────────
    {"ticker": "ISRG",  "company": "Intuitive Surgical","sector": "Med Devices",  "business": "Robotic surgery (da Vinci), #1 surgical robot market"},
    {"ticker": "DXCM",  "company": "Dexcom",           "sector": "Med Devices",  "business": "Continuous glucose monitoring (CGM) for diabetics"},
    {"ticker": "IDXX",  "company": "IDEXX Laboratories","sector": "Med Devices",  "business": "Veterinary diagnostics and software"},
    {"ticker": "ALGN",  "company": "Align Technology",  "sector": "Med Devices",  "business": "Invisalign clear aligners, iTero 3D scanners"},
    {"ticker": "HOLX",  "company": "Hologic",          "sector": "Med Devices",  "business": "Women's health diagnostics, mammography, surgical"},
    {"ticker": "TMDX",  "company": "TransMedics",      "sector": "Med Devices",  "business": "Organ Care System (OCS) — warm organ transport for transplant"},
    {"ticker": "AXNX",  "company": "Axonics",          "sector": "Med Devices",  "business": "Sacral neuromodulation for bladder/bowel disorders"},
    {"ticker": "PODD",  "company": "Insulet",          "sector": "Med Devices",  "business": "Omnipod insulin pump (tubeless, wearable)"},
    {"ticker": "NVCR",  "company": "Novocure",         "sector": "Med Devices",  "business": "Tumor Treating Fields (TTFields) for brain/lung cancer"},
    {"ticker": "IRTC",  "company": "iRhythm Technologies","sector": "Med Devices","business": "Zio patch cardiac monitoring (ECG wearable)"},

    # ── EV / Automotive / Mobility ────────────────────────────────────────────
    {"ticker": "TSLA",  "company": "Tesla",            "sector": "EV",           "business": "EV, Full Self-Driving (FSD), Robotaxi, Megapack, xAI"},
    {"ticker": "RIVN",  "company": "Rivian",           "sector": "EV",           "business": "Electric trucks/SUVs (R1T, R1S), Amazon delivery vans"},
    {"ticker": "LCID",  "company": "Lucid Group",      "sector": "EV",           "business": "Luxury EV sedans (Air), Saudi Arabia backing (PIF)"},
    {"ticker": "NIO",   "company": "NIO",              "sector": "EV",           "business": "Chinese premium EV, battery-swap network"},
    {"ticker": "XPEV",  "company": "XPeng",            "sector": "EV",           "business": "Chinese EV with advanced ADAS, Mona series"},
    {"ticker": "LI",    "company": "Li Auto",          "sector": "EV",           "business": "Chinese EREV (extended-range EV) SUVs"},
    {"ticker": "F",     "company": "Ford",             "sector": "Automotive",   "business": "ICE + EV (F-150 Lightning, Mustang Mach-E), Blue/Model e"},
    {"ticker": "GM",    "company": "General Motors",   "sector": "Automotive",   "business": "ICE + EV (Ultium platform), Cruise robotaxi"},
    {"ticker": "TM",    "company": "Toyota",           "sector": "Automotive",   "business": "Hybrid (Prius), solid-state battery R&D, #1 automaker"},
    {"ticker": "STLA",  "company": "Stellantis",       "sector": "Automotive",   "business": "Jeep, Ram, Dodge, Alfa Romeo, Peugeot"},

    # ── Energy — Oil & Gas ────────────────────────────────────────────────────
    {"ticker": "OXY",   "company": "Occidental Petroleum","sector": "Energy",    "business": "US oil & gas E&P, Berkshire Hathaway major stake"},
    {"ticker": "DVN",   "company": "Devon Energy",     "sector": "Energy",       "business": "US shale oil & gas (Permian, Anadarko)"},
    {"ticker": "FANG",  "company": "Diamondback Energy","sector": "Energy",      "business": "Permian Basin pure-play oil & gas E&P"},
    {"ticker": "HAL",   "company": "Halliburton",      "sector": "Energy",       "business": "Oilfield services, fracking, drilling tech"},
    {"ticker": "SLB",   "company": "SLB (Schlumberger)","sector": "Energy",      "business": "Global oilfield services, digital oil & gas platform"},
    {"ticker": "NOG",   "company": "Northern Oil & Gas","sector": "Energy",      "business": "Non-op mineral rights in Permian/Bakken"},
    {"ticker": "CTRA",  "company": "Coterra Energy",   "sector": "Energy",       "business": "Natural gas (Marcellus) and oil (Permian) E&P"},
    {"ticker": "AR",    "company": "Antero Resources", "sector": "Energy",       "business": "Appalachian natural gas and NGLs"},
    {"ticker": "RRC",   "company": "Range Resources",  "sector": "Energy",       "business": "Marcellus natural gas E&P"},
    {"ticker": "LNG",   "company": "Cheniere Energy",  "sector": "Energy",       "business": "US #1 LNG exporter (Sabine Pass, Corpus Christi)"},
    {"ticker": "VST",   "company": "Vistra Corp",      "sector": "Energy",       "business": "Power generation (nuclear + gas), data center demand play"},
    {"ticker": "CEG",   "company": "Constellation Energy","sector": "Energy",    "business": "Nuclear power fleet #1 US, AI data center contracts"},
    {"ticker": "NEE",   "company": "NextEra Energy",   "sector": "Energy",       "business": "Largest US utility, wind & solar renewable developer"},
    {"ticker": "XOM",   "company": "ExxonMobil",       "sector": "Energy",       "business": "Integrated oil major, Permian, LNG, carbon capture"},
    {"ticker": "CVX",   "company": "Chevron",          "sector": "Energy",       "business": "Integrated oil major, Tengiz, LNG, hydrogen"},

    # ── Nuclear / Clean Energy ────────────────────────────────────────────────
    {"ticker": "OKLO",  "company": "Oklo",             "sector": "Nuclear",      "business": "Small modular reactors (Aurora microreactor) — pre-revenue, Sam Altman backed"},
    {"ticker": "SMR",   "company": "NuScale Power",    "sector": "Nuclear",      "business": "Small modular reactors — pre-revenue, first NRC-approved SMR design"},
    {"ticker": "CCJ",   "company": "Cameco",           "sector": "Nuclear",      "business": "Uranium mining — fuels nuclear renaissance"},
    {"ticker": "LEU",   "company": "Centrus Energy",   "sector": "Nuclear",      "business": "Enriched uranium supplier for US nuclear fleet"},
    {"ticker": "BWX",   "company": "BWX Technologies", "sector": "Nuclear",      "business": "Nuclear components for US Navy + commercial reactors"},
    {"ticker": "UUUU",  "company": "Energy Fuels",     "sector": "Nuclear",      "business": "US uranium and rare earth mining"},
    {"ticker": "DNN",   "company": "Denison Mines",    "sector": "Nuclear",      "business": "Uranium development (Athabasca Basin, Canada)"},
    {"ticker": "BWXT",  "company": "BWX Technologies", "sector": "Nuclear",      "business": "Nuclear propulsion for US Navy, SMR components"},

    # ── Consumer / Retail / Restaurants ──────────────────────────────────────
    {"ticker": "COST",  "company": "Costco",           "sector": "Consumer",     "business": "Membership warehouse retail, private label Kirkland"},
    {"ticker": "WMT",   "company": "Walmart",          "sector": "Consumer",     "business": "Mass retail, Walmart+, grocery, Sam's Club, advertising"},
    {"ticker": "TGT",   "company": "Target",           "sector": "Consumer",     "business": "Discount retail, owned brands, same-day delivery"},
    {"ticker": "LULU",  "company": "Lululemon",        "sector": "Consumer",     "business": "Premium activewear, Mirror fitness, DTC expansion"},
    {"ticker": "NKE",   "company": "Nike",             "sector": "Consumer",     "business": "Athletic footwear/apparel, DTC digital, Jordan brand"},
    {"ticker": "ROST",  "company": "Ross Stores",      "sector": "Consumer",     "business": "Off-price retail (Ross Dress for Less, dd's)"},
    {"ticker": "TJX",   "company": "TJX Companies",   "sector": "Consumer",     "business": "Off-price retail (TJ Maxx, Marshalls, HomeGoods)"},
    {"ticker": "SBUX",  "company": "Starbucks",        "sector": "Consumer",     "business": "Coffee retail chain, loyalty rewards, China expansion"},
    {"ticker": "MCD",   "company": "McDonald's",       "sector": "Consumer",     "business": "Fast food franchise, digital ordering, CosMc's"},
    {"ticker": "CMG",   "company": "Chipotle",         "sector": "Consumer",     "business": "Fast-casual Mexican, Chipotlane drive-through, loyalty"},
    {"ticker": "DPZ",   "company": "Domino's Pizza",   "sector": "Consumer",     "business": "Pizza delivery franchise, tech-led ordering"},
    {"ticker": "YUM",   "company": "Yum! Brands",      "sector": "Consumer",     "business": "KFC, Pizza Hut, Taco Bell franchise (global)"},
    {"ticker": "DKNG",  "company": "DraftKings",       "sector": "Consumer",     "business": "Online sports betting and gaming"},
    {"ticker": "PENN",  "company": "PENN Entertainment","sector": "Consumer",    "business": "Casinos + ESPN Bet online sports betting"},

    # ── Media / Entertainment / Gaming ────────────────────────────────────────
    {"ticker": "DIS",   "company": "Walt Disney",      "sector": "Media",        "business": "Disney+, ESPN, theme parks, Marvel, Star Wars, Pixar"},
    {"ticker": "PARA",  "company": "Paramount Global", "sector": "Media",        "business": "Paramount+, CBS, MTV, Nickelodeon — merger talks"},
    {"ticker": "WBD",   "company": "Warner Bros Discovery","sector": "Media",    "business": "HBO Max, CNN, Warner Bros films, sports"},
    {"ticker": "SPOT",  "company": "Spotify",          "sector": "Media",        "business": "Music/podcast streaming #1 globally, audiobooks"},
    {"ticker": "EA",    "company": "Electronic Arts",  "sector": "Gaming",       "business": "Video games (FIFA/EA FC, Madden, Apex Legends)"},
    {"ticker": "TTWO",  "company": "Take-Two Interactive","sector": "Gaming",    "business": "Grand Theft Auto (GTA 6), NBA 2K, Zynga mobile"},
    {"ticker": "NTDOY", "company": "Nintendo",         "sector": "Gaming",       "business": "Switch console, Mario, Zelda, Pokemon IP"},
    {"ticker": "U",     "company": "Unity Software",   "sector": "Gaming",       "business": "Game engine (Unity), real-time 3D for gaming/industrial"},

    # ── Telecom ───────────────────────────────────────────────────────────────
    {"ticker": "TMUS",  "company": "T-Mobile US",      "sector": "Telecom",      "business": "US wireless carrier #2, 5G network leadership"},
    {"ticker": "VZ",    "company": "Verizon",          "sector": "Telecom",      "business": "US wireless, broadband (Fios), business services"},
    {"ticker": "T",     "company": "AT&T",             "sector": "Telecom",      "business": "US wireless, fiber broadband (AT&T Fiber)"},

    # ── ETF / Index ───────────────────────────────────────────────────────────
    {"ticker": "SPY",   "company": "SPDR S&P 500 ETF", "sector": "ETF",          "business": "Tracks S&P 500 — broad US large-cap market benchmark"},
    {"ticker": "QQQ",   "company": "Invesco NASDAQ-100 ETF","sector": "ETF",      "business": "Tracks NASDAQ-100 — top 100 non-financial NASDAQ stocks"},
    {"ticker": "IWM",   "company": "iShares Russell 2000 ETF","sector": "ETF",   "business": "Tracks Russell 2000 — US small-cap stocks"},
    {"ticker": "ARKK",  "company": "ARK Innovation ETF","sector": "ETF",         "business": "Actively managed — disruptive innovation (Cathie Wood)"},
    {"ticker": "SOXX",  "company": "iShares Semiconductor ETF","sector": "ETF",  "business": "Tracks Philadelphia Semiconductor Index (SOX)"},
    {"ticker": "XLE",   "company": "Energy Select Sector SPDR","sector": "ETF",  "business": "Tracks S&P 500 energy sector (XOM, CVX, SLB, etc.)"},
    {"ticker": "XLK",   "company": "Technology Select Sector SPDR","sector": "ETF","business": "Tracks S&P 500 technology sector"},
    {"ticker": "XLF",   "company": "Financial Select Sector SPDR","sector": "ETF","business": "Tracks S&P 500 financial sector"},
    {"ticker": "XBI",   "company": "SPDR S&P Biotech ETF","sector": "ETF",       "business": "Equal-weight biotech ETF — high beta sector play"},

    # ── Macro Instruments ─────────────────────────────────────────────────────
    {"ticker": "USO",   "company": "US Oil Fund",      "sector": "Macro",        "business": "Crude oil price proxy (WTI futures) — tracks oil market"},
    {"ticker": "GLD",   "company": "SPDR Gold Trust",  "sector": "Macro",        "business": "Gold price proxy — safe haven, inflation hedge"},
    {"ticker": "TLT",   "company": "iShares 20yr Treasury ETF","sector": "Macro","business": "Long-term US bond — inverse to interest rates, Fed policy"},
    {"ticker": "DXY",   "company": "US Dollar Index",  "sector": "Macro",        "business": "USD strength vs basket of currencies — affects commodities, EM"},
    {"ticker": "BTC-USD","company": "Bitcoin",         "sector": "Macro",        "business": "Crypto reserve asset, ETF inflows, institutional adoption"},
    {"ticker": "GDX",   "company": "VanEck Gold Miners ETF","sector": "Macro",   "business": "Gold mining stocks — leveraged bet on gold price"},
    {"ticker": "SHY",   "company": "iShares 1-3yr Treasury ETF","sector": "Macro","business": "Short-term bond — most sensitive to Fed rate decisions"},
]

# ── Convenience lookups ───────────────────────────────────────────────────────

UNIVERSE_BY_TICKER: dict[str, StockInfo] = {s["ticker"]: s for s in UNIVERSE}

UNIVERSE_TICKERS: list[str] = [s["ticker"] for s in UNIVERSE]

SECTORS: list[str] = sorted({s["sector"] for s in UNIVERSE})

def by_sector(sector: str) -> list[StockInfo]:
    """Return all stocks in a given sector."""
    return [s for s in UNIVERSE if s["sector"] == sector]
