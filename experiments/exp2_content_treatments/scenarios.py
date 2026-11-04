"""Thirty purchase-decision scenarios for the content-treatment experiment.

Every brand, business, place, evaluator and person generated from these pools
is fictional. Brands are assembled per scenario by build_corpus.py; each pool
below supplies the attributes a brand page can draw on.

Metric templates accept {pct} (60-97), {rating} (4.2-4.8) and {num:lo-hi}.
"""

S = []


def scenario(**kw):
    kw.setdefault("plural", kw["category"] + "s")
    kw.setdefault("kind", "software")
    kw.setdefault("town", "")
    S.append(kw)


scenario(id="pm_agency", vertical="B2B software", category="project management tool",
         query="What's the best project management tool for a 15-person marketing agency that runs many client projects at once?",
         need="agencies juggling several client projects",
         features=["Kanban and timeline views", "client-facing portals", "built-in time tracking", "workload planning",
                   "proofing and approval workflows", "recurring task templates", "budget tracking per project", "guest access for freelancers"],
         extras=["Slack and Google Drive integrations", "a mobile app for iOS and Android", "single sign-on on higher tiers", "a public API", "two-factor authentication"],
         best_for=["small creative teams that want simple boards", "agencies that bill clients by the hour", "teams that need detailed workload planning",
                   "fast-growing teams that want automation", "budget-conscious teams moving off spreadsheets"],
         price=("${p} per user per month", 6, 24), unit="teams",
         metrics=["a {pct}% annual customer retention rate", "an average onboarding time of {num:2-9} days", "{pct}% of tasks completed on schedule across customer workspaces"],
         anti_fit=["large enterprises that need on-premise hosting", "software teams that need sprint planning", "solo freelancers who only need a to-do list", "teams that require offline access"],
         weak=["reporting dashboard", "mobile app", "Gantt chart editor", "automation builder"], criterion="ease of use")

scenario(id="crm_realestate", vertical="B2B software", category="CRM",
         query="Which CRM should a small real-estate team of 6 agents use to track leads and follow-ups?",
         need="small real-estate teams managing leads",
         features=["lead capture from listing sites", "automated follow-up reminders", "a visual deal pipeline", "built-in email and SMS",
                   "contact deduplication", "transaction checklists", "call logging", "a shared team inbox"],
         extras=["Gmail and Outlook sync", "a mobile app", "a Zapier integration", "MLS listing import", "an e-signature integration"],
         best_for=["solo agents who want a simple contact list", "small brokerages that track many leads", "teams that rely on text messaging",
                   "agents who want marketing automation", "teams moving off spreadsheets"],
         price=("${p} per user per month", 12, 59), unit="agents",
         metrics=["a {pct}% faster lead response time reported by customers", "an average of {num:3-9} hours saved per agent each week", "{pct}% customer retention after the first year"],
         anti_fit=["large enterprises needing custom objects", "e-commerce stores", "agents who never use email", "teams that need offline access"],
         weak=["reporting", "mobile app", "email templates", "calendar sync"], criterion="lead management")

scenario(id="email_ecom", vertical="B2B software", category="email marketing platform",
         query="What's a good email marketing platform for a small online store selling handmade candles?",
         need="small online stores",
         features=["a drag-and-drop email builder", "abandoned-cart emails", "Shopify product sync", "audience segmentation",
                   "A/B testing of subject lines", "SMS campaigns", "signup forms and pop-ups", "revenue attribution reports"],
         extras=["a free plan for small lists", "pre-built e-commerce templates", "24/7 chat support", "deliverability monitoring", "GDPR consent tools"],
         best_for=["creators sending simple newsletters", "online stores that want automated flows", "brands combining email and SMS",
                   "growing stores that need detailed analytics", "budget-conscious shops with small lists"],
         price=("${p} per month for up to 1,000 contacts", 9, 35), unit="online stores",
         metrics=["an average open rate of {num:35-52}% across customer campaigns", "{pct}% inbox placement in independent deliverability tests", "an average of {num:8-25} minutes to build a campaign"],
         anti_fit=["large retailers needing enterprise data warehouses", "B2B companies running account-based marketing", "senders who only need transactional email", "teams that need on-premise deployment"],
         weak=["template library", "reporting", "SMS pricing", "automation editor"], criterion="e-commerce features")

scenario(id="accounting_freelance", vertical="B2B software", category="accounting software", plural="accounting tools",
         query="Which accounting software is best for a freelance designer who invoices international clients?",
         need="freelancers invoicing clients abroad",
         features=["multi-currency invoicing", "automatic bank feeds", "receipt scanning", "estimated tax reminders",
                   "expense categorization", "online payment links", "time-to-invoice conversion", "simple profit and loss reports"],
         extras=["a mobile app", "Stripe and PayPal integrations", "accountant access", "a 30-day free trial", "data export to spreadsheets"],
         best_for=["freelancers who want quick invoicing", "small businesses with employees", "sole traders who need tax-ready reports",
                   "consultants billing by the hour", "users who mostly track expenses"],
         price=("${p} per month", 8, 30), unit="freelancers and small businesses",
         metrics=["invoices paid an average of {num:4-12} days faster", "{pct}% of transactions categorized automatically", "{num:3-10} hours saved per month on bookkeeping"],
         anti_fit=["companies needing full payroll", "businesses with inventory", "large firms with multiple entities", "users who need on-premise software"],
         weak=["payroll", "inventory tracking", "report customization", "mobile receipt capture"], criterion="invoicing")

scenario(id="password_smb", vertical="B2B software", category="password manager",
         query="What password manager should a 20-person company use to share logins securely?",
         need="small companies sharing credentials",
         features=["shared team vaults", "end-to-end encryption", "single sign-on support", "admin access controls",
                   "breach monitoring", "passkey support", "secure sharing links", "audit logs"],
         extras=["browser extensions for all major browsers", "mobile apps", "a published independent security audit", "emergency access", "SCIM provisioning"],
         best_for=["individuals and families", "small teams that need simple sharing", "regulated companies needing audit trails",
                   "IT teams managing many users", "budget-conscious startups"],
         price=("${p} per user per month", 2, 8), unit="businesses",
         metrics=["{num:2-6} independent security audits published", "{pct}% of customers rating setup as easy", "an average deployment time of {num:1-5} days"],
         anti_fit=["enterprises needing on-premise vaults", "users who only want a free personal tool", "teams needing secrets management for servers", "organizations requiring hardware-only storage"],
         weak=["admin console", "Linux app", "reporting", "import tools"], criterion="security")

scenario(id="helpdesk_saas", vertical="B2B software", category="help desk tool",
         query="Which help desk software is best for a SaaS startup with a 4-person support team?",
         need="small SaaS support teams",
         features=["a shared inbox for email and chat", "a knowledge base builder", "AI-suggested replies", "SLA tracking",
                   "customer satisfaction surveys", "ticket routing rules", "an in-app chat widget", "bug tracker integrations"],
         extras=["a free tier for small teams", "a Slack integration", "a public API", "multilingual support", "a SOC 2 report"],
         best_for=["startups that want a simple shared inbox", "teams with heavy live-chat volume", "companies building self-service help centers",
                   "support teams that need strict SLAs", "growing teams that want automation"],
         price=("${p} per agent per month", 10, 69), unit="support teams",
         metrics=["a {num:20-45}% reduction in first-response time reported by customers", "an average CSAT of {pct}% across customer accounts", "a median setup time of {num:15-60} minutes"],
         anti_fit=["large call centers with phone queues", "teams needing on-premise deployment", "companies wanting a full CRM", "retailers needing in-store tools"],
         weak=["phone support", "reporting", "mobile app", "workflow automation"], criterion="ease of use")

scenario(id="hosting_django", vertical="Developer tools", category="cloud hosting platform",
         query="What's the best hosting platform to deploy a small Django app with a Postgres database?",
         need="small web apps with a database",
         features=["one-click Postgres databases", "git-based deployments", "automatic HTTPS", "preview environments for pull requests",
                   "autoscaling", "background workers", "built-in logs and metrics", "managed Redis"],
         extras=["a free hobby tier", "data centers in Europe and the US", "a CLI tool", "daily database backups", "Docker support"],
         best_for=["hobby projects and prototypes", "startups that want zero DevOps", "teams that need fine-grained infrastructure control",
                   "apps with spiky traffic", "budget-conscious developers"],
         price=("${p} per month for a basic app with a database", 5, 25), unit="developers",
         metrics=["{num:99.90-99.99}% uptime over the last 12 months", "a median deploy time of {num:30-120} seconds", "{num:4-14} regions available"],
         anti_fit=["enterprises needing dedicated hardware", "teams running GPU workloads", "apps that require Windows servers", "organizations needing on-premise hosting"],
         weak=["database tooling", "pricing transparency", "region choice", "logging"], criterion="developer experience")

scenario(id="monitoring_mobile", vertical="Developer tools", category="error monitoring service",
         query="Which error monitoring tool should a small team use for a React Native mobile app?",
         need="small mobile teams",
         features=["crash reporting with stack traces", "a React Native SDK", "release health tracking", "performance tracing",
                   "session replay", "alert routing to Slack", "source map uploads", "user impact analysis"],
         extras=["a free developer plan", "a GitHub integration", "EU data residency", "an open-source SDK", "PII scrubbing"],
         best_for=["web teams monitoring front-end errors", "mobile teams shipping frequent releases", "backend teams needing log aggregation",
                   "large organizations with many services", "budget-conscious indie developers"],
         price=("${p} per month for small teams", 19, 89), unit="engineering teams",
         metrics=["{pct}% of crashes grouped automatically", "a median alert latency of {num:5-40} seconds", "{num:12-40} supported platforms"],
         anti_fit=["teams needing full infrastructure monitoring", "companies that require on-premise deployment", "teams with no mobile apps", "organizations needing security event monitoring"],
         weak=["session replay", "dashboard customization", "pricing at high volume", "log search"], criterion="mobile support")

scenario(id="headphones_commute", vertical="Consumer electronics", kind="product", category="pair of noise-cancelling headphones",
         plural="noise-cancelling headphones",
         query="What are the best noise-cancelling headphones for a daily train commute, under $300?",
         need="commuters who want quiet",
         features=["adaptive noise cancellation", "30-hour battery life", "multipoint Bluetooth", "a foldable design",
                   "clear call microphones", "a transparency mode", "USB-C fast charging", "memory-foam ear cushions"],
         extras=["a hard carrying case", "a two-year warranty", "an app with a custom EQ", "free returns within 30 days", "replaceable ear pads"],
         best_for=["frequent flyers", "daily commuters", "people who take many calls", "gym-goers who want a secure fit", "listeners on a budget"],
         price=("${p}", 149, 299), unit="customers",
         metrics=["up to {num:24-40} hours of battery life in independent tests", "noise reduction of up to {num:28-42} dB in lab tests", "an average rating of {rating} stars from verified buyers"],
         anti_fit=["audiophiles who want wired studio sound", "runners who need a waterproof fit", "people who want the lightest possible earbuds", "gamers who need a boom mic"],
         weak=["call quality in wind", "touch controls", "bass response", "case size"], criterion="noise cancellation")

scenario(id="vacuum_pets", vertical="Consumer electronics", kind="product", category="robot vacuum",
         query="Which robot vacuum is best for a home with two shedding dogs and mostly hardwood floors?",
         need="homes with pet hair",
         features=["tangle-free rubber brushes", "a self-emptying base", "lidar mapping", "obstacle avoidance for pet waste",
                   "a large dustbin", "a mopping attachment", "app-based room scheduling", "HEPA filtration"],
         extras=["a one-year warranty", "voice assistant support", "spare brushes in the box", "free shipping", "a 60-day trial"],
         best_for=["small apartments", "homes with pets", "large multi-floor homes", "people who want to vacuum and mop in one", "shoppers on a budget"],
         price=("${p}", 199, 699), unit="households",
         metrics=["{num:88-98}% pet-hair pickup in independent tests", "up to {num:90-180} minutes of runtime", "an average rating of {rating} stars from verified buyers"],
         anti_fit=["homes with deep shag carpets", "people who want no app setup", "budgets under $150", "homes with many high thresholds"],
         weak=["mopping", "app reliability", "edge cleaning", "noise level"], criterion="pet hair pickup")

scenario(id="laptop_students", vertical="Consumer electronics", kind="product", category="laptop",
         query="What's the best budget laptop for a university student who writes papers and does light photo editing?",
         need="students on a budget",
         features=["a 14-inch high-resolution display", "all-day battery life", "16 GB of RAM", "a backlit keyboard",
                   "a lightweight aluminum chassis", "fast SSD storage", "a fingerprint reader", "Wi-Fi 7 support"],
         extras=["a student discount", "a two-year warranty", "free returns", "pre-installed office apps", "a USB-C charger that also charges phones"],
         best_for=["students on a tight budget", "creative students who edit photos", "students who need maximum portability",
                   "gamers on a budget", "students who want a 2-in-1 tablet mode"],
         price=("${p}", 549, 999), unit="students",
         metrics=["up to {num:12-22} hours of battery life in independent tests", "a display covering {num:95-100}% of the sRGB color space", "an average rating of {rating} stars from verified buyers"],
         anti_fit=["serious gamers", "video editors working in 4K", "people who need a 17-inch screen", "users who require Linux support"],
         weak=["speakers", "webcam", "port selection", "fan noise"], criterion="value for money")

scenario(id="ereader", vertical="Consumer electronics", kind="product", category="e-reader",
         query="Which e-reader is best for someone who reads in bed and borrows library books?",
         need="readers who borrow library books",
         features=["a warm adjustable front light", "library book borrowing", "a 7-inch glare-free screen", "waterproofing",
                   "weeks of battery life", "physical page-turn buttons", "note-taking with a stylus", "audiobooks over Bluetooth"],
         extras=["a protective cover", "a two-year warranty", "free returns", "no lock-screen ads", "USB-C charging"],
         best_for=["readers who borrow library books", "people who read by the pool", "students who annotate PDFs", "readers on a budget", "people who want one-handed reading"],
         price=("${p}", 99, 279), unit="readers",
         metrics=["up to {num:6-10} weeks of battery life", "a {num:212-330} ppi display", "an average rating of {rating} stars from verified buyers"],
         anti_fit=["people who mainly read comics in color", "readers who want a full tablet", "users locked into one bookstore", "people who want the cheapest option"],
         weak=["store selection", "PDF handling", "page-turn speed", "accessory prices"], criterion="reading comfort")

scenario(id="grinder_espresso", vertical="Home and kitchen", kind="product", category="coffee grinder",
         query="What's the best coffee grinder for a beginner making espresso at home?",
         need="espresso beginners",
         features=["stepless grind adjustment", "conical burrs", "low grind retention", "a single-dose hopper",
                   "a built-in timer", "a portafilter holder", "quiet operation", "easy burr cleaning"],
         extras=["a two-year warranty", "a cleaning brush", "free shipping", "replacement burrs", "a dosing cup"],
         best_for=["espresso beginners", "pour-over drinkers", "people who switch between brew methods", "small kitchens", "buyers on a budget"],
         price=("${p}", 129, 449), unit="home baristas",
         metrics=["grind retention under {num:0.1-0.5} grams in independent tests", "{num:30-60} grind settings", "an average rating of {rating} stars from verified buyers"],
         anti_fit=["cafés needing commercial throughput", "people who only drink French press", "buyers who want a fully automatic machine", "people who want a hand grinder"],
         weak=["noise", "hopper size", "build materials", "grinding speed"], criterion="espresso grind quality")

scenario(id="purifier_allergies", vertical="Home and kitchen", kind="product", category="air purifier",
         query="Which air purifier is best for a bedroom for someone with pollen allergies?",
         need="allergy sufferers",
         features=["a true HEPA filter", "an activated carbon layer", "a quiet sleep mode", "an air quality sensor",
                   "an auto mode", "filter replacement alerts", "coverage for rooms up to 400 sq ft", "a dimmable display"],
         extras=["a two-year warranty", "affordable replacement filters", "an app with air quality history", "free returns", "Energy Star certification"],
         best_for=["bedrooms and small rooms", "large living areas", "homes with smokers", "allergy sufferers", "buyers on a budget"],
         price=("${p}", 89, 399), unit="households",
         metrics=["a clean air delivery rate of {num:180-320} cfm", "noise of {num:22-32} dB on the lowest setting", "{num:97-99.9}% of airborne pollen removed in lab tests"],
         anti_fit=["very large open-plan spaces", "people who also want a humidifier", "buyers who dislike app-connected devices", "industrial workshops"],
         weak=["filter cost", "app", "fan noise on high", "design"], criterion="allergen removal")

scenario(id="desk_small", vertical="Home and kitchen", kind="product", category="standing desk",
         query="What's the best standing desk for a small apartment home office?",
         need="small home offices",
         features=["a compact 48-inch top", "dual motors", "programmable height presets", "a cable management tray",
                   "anti-collision sensing", "a wide height range", "a bamboo desktop option", "quiet lifting"],
         extras=["a 10-year frame warranty", "free shipping", "a 30-day trial", "tool-free assembly", "monitor arm compatibility"],
         best_for=["small apartments", "tall users", "people with heavy multi-monitor setups", "shoppers on a budget", "people who want premium materials"],
         price=("${p}", 299, 799), unit="customers",
         metrics=["a lift speed of {num:25-45} mm per second", "a weight capacity of {num:150-350} pounds", "an average rating of {rating} stars from verified buyers"],
         anti_fit=["users needing an L-shaped corner desk", "very tall users above 6'6\"", "people who want a manual crank", "buyers who need same-day delivery"],
         weak=["wobble at full height", "assembly time", "desktop finish", "controller"], criterion="stability")

scenario(id="shoes_flatfeet", vertical="Sports and outdoors", kind="product", category="running shoe",
         query="Which running shoes are best for a beginner with flat feet training for a 10K?",
         need="beginners with flat feet",
         features=["a stability medial post", "a wide toe box", "responsive foam cushioning", "a durable rubber outsole",
                   "a breathable mesh upper", "a firm heel counter", "a moderate 8 mm drop", "reflective details"],
         extras=["a 90-day return window", "wide-fit options", "free shipping", "a recycled-material upper", "a free gait guide"],
         best_for=["beginners who need stability", "neutral runners logging high mileage", "trail runners", "racers who want speed", "runners on a budget"],
         price=("${p}", 89, 169), unit="runners",
         metrics=["an average rating of {rating} stars from verified buyers", "a midsole that keeps {pct}% of its cushioning after 300 miles in lab tests", "a weight of {num:230-310} grams per shoe"],
         anti_fit=["trail runners on technical terrain", "runners with high arches", "sprinters", "people who want a minimalist shoe"],
         weak=["weight", "breathability", "grip in rain", "lacing"], criterion="stability")

scenario(id="tent_backpacking", vertical="Sports and outdoors", kind="product", category="backpacking tent",
         query="What's the best lightweight two-person backpacking tent for summer trips?",
         need="lightweight summer backpacking",
         features=["a trail weight under 3 pounds", "two doors and two vestibules", "a freestanding design", "color-coded clips for fast pitching",
                   "a full-coverage rainfly", "large mesh panels", "a compact packed size", "aluminum poles"],
         extras=["a lifetime warranty", "an optional footprint", "free repairs in the first year", "free returns", "a stuff sack"],
         best_for=["ultralight thru-hikers", "summer weekend backpackers", "campers who want more space", "four-season mountaineers", "budget-conscious beginners"],
         price=("${p}", 179, 499), unit="hikers",
         metrics=["a trail weight of {num:900-1400} grams", "a pitch time of {num:3-8} minutes in tests", "an average rating of {rating} stars from verified buyers"],
         anti_fit=["winter mountaineering", "car camping with large families", "people who want the cheapest option", "hikers who want a trekking-pole shelter"],
         weak=["floor durability", "interior height", "price", "stake quality"], criterion="weight-to-space ratio")

scenario(id="hotel_family", vertical="Travel and hospitality", kind="local", town="Port Alder", category="hotel",
         query="Which hotel in Port Alder is best for a family with two young kids?",
         need="families with young children",
         features=["interconnecting family rooms", "a heated outdoor pool", "free breakfast", "a kids' club",
                   "a quiet location near the beach", "a free airport shuttle", "kitchenettes in suites", "free parking"],
         extras=["free cancellation up to 48 hours", "babysitting on request", "free cribs", "a 24-hour front desk", "a loyalty program"],
         best_for=["couples on romantic getaways", "families with young children", "business travelers", "travelers on a budget", "guests who want nightlife nearby"],
         price=("rooms from ${p} per night", 119, 349), unit="guests",
         metrics=["a guest rating of {rating} out of 5 from verified stays", "{num:30-55}% of guests returning within two years", "{num:12-40} family rooms"],
         anti_fit=["travelers wanting nightlife", "guests who need a business center", "backpackers on tight budgets", "travelers without a car who want city sightseeing"],
         weak=["Wi-Fi speed", "restaurant hours", "room size", "parking availability"], criterion="family friendliness")

scenario(id="luggage_carryon", vertical="Travel and hospitality", kind="product", category="carry-on suitcase",
         query="What's the best carry-on suitcase for frequent business travel?",
         need="frequent business travelers",
         features=["a polycarbonate hard shell", "smooth spinner wheels", "a laptop compartment", "an ejectable battery pack",
                   "a TSA-approved lock", "compression straps", "an expandable zipper", "a size that fits most overhead bins"],
         extras=["a lifetime warranty", "free shipping", "a 100-day trial", "free personalization", "replaceable wheels"],
         best_for=["frequent business travelers", "family vacations", "budget travelers", "adventure travelers", "people who prefer soft-sided bags"],
         price=("${p}", 129, 449), unit="travelers",
         metrics=["a weight of {num:2.6-3.6} kg", "an average rating of {rating} stars from verified buyers", "{num:20000-60000} wheel test cycles passed"],
         anti_fit=["travelers who check bags for long trips", "backpackers", "people who need maximum capacity", "buyers under $100"],
         weak=["scratch resistance", "interior organization", "handle wobble", "weight"], criterion="durability")

scenario(id="bootcamp_career", vertical="Education", kind="service", category="online coding bootcamp",
         query="Which online coding bootcamp is best for a career changer with a full-time job?",
         need="career changers studying part-time",
         features=["a part-time evening schedule", "1-on-1 mentor sessions", "career coaching", "a portfolio project curriculum",
                   "a conditional job guarantee", "live code reviews", "a flexible pause option", "an active alumni community"],
         extras=["monthly payment plans", "a free prep course", "lifetime access to materials", "employer partnerships", "a 14-day refund window"],
         best_for=["career changers studying part-time", "full-time students who want speed", "beginners exploring coding", "people targeting data science roles", "learners on a budget"],
         price=("${p} total tuition", 3900, 15900), unit="graduates",
         metrics=["{num:62-88}% of graduates employed in tech within six months in an audited outcomes report", "an average of {num:20-60} hours of mentor time per student", "{num:40-180} hiring partners"],
         anti_fit=["people who want a university degree", "learners who need in-person classes", "experienced developers", "people who cannot commit 15 hours a week"],
         weak=["curriculum depth in algorithms", "class size", "career services outside the US", "refund terms"], criterion="career outcomes")

scenario(id="language_spanish", vertical="Education", category="language learning app",
         query="What's the best app for an adult beginner to learn conversational Spanish?",
         need="adult beginners focused on conversation",
         features=["speech recognition for pronunciation", "short daily lessons", "live tutor sessions", "spaced-repetition review",
                   "conversation practice with AI role-play", "offline lessons", "grammar explanations in English", "podcast-style listening practice"],
         extras=["a free tier", "a family plan", "a 7-day free trial", "progress certificates", "apps for phone and desktop"],
         best_for=["absolute beginners who want a daily habit", "travelers who need phrases fast", "learners who want live tutors",
                   "intermediate learners polishing grammar", "learners on a budget"],
         price=("${p} per month", 7, 29), unit="learners",
         metrics=["{num:40-70}% of learners completing their first course in an independent study", "an average of {num:10-25} minutes of practice per session", "an average rating of {rating} stars from app store reviews"],
         anti_fit=["advanced learners preparing for C2 exams", "people who need university credit", "learners who want only textbooks", "children under 8"],
         weak=["grammar depth", "offline mode", "accent variety", "speaking feedback"], criterion="speaking practice")

scenario(id="tutoring_math", vertical="Education", kind="service", category="online math tutoring service",
         query="Which online math tutoring service is best for a 10-year-old who is falling behind?",
         need="children catching up in math",
         features=["1-on-1 live tutoring", "diagnostic placement tests", "game-based practice", "progress reports for parents",
                   "curriculum-aligned lessons", "flexible scheduling", "certified teachers", "on-demand homework help"],
         extras=["a free trial lesson", "sibling discounts", "a satisfaction guarantee", "a mobile app", "no long-term contract"],
         best_for=["children catching up in math", "advanced students who want enrichment", "older students preparing for tests", "families on a budget", "homeschooling families"],
         price=("${p} per session", 19, 59), unit="families",
         metrics=["an average gain of {num:10-30} percentile points after 12 weeks in an internal study", "{pct}% of parents renewing after the first term", "tutors averaging {num:4-15} years of teaching experience"],
         anti_fit=["high-school calculus students", "families wanting in-person tutoring", "students who need reading support", "parents wanting group classes"],
         weak=["scheduling at peak times", "app", "price", "tutor matching"], criterion="learning outcomes")

scenario(id="dental_nervous", vertical="Local services", kind="local", town="Marlow Heights", category="dental clinic",
         query="Which dental clinic in Marlow Heights is best for a nervous patient who needs a filling?",
         need="nervous patients",
         features=["sedation options", "calm, quiet treatment rooms", "extended evening hours", "same-day appointments",
                   "a transparent price list", "digital X-rays", "a dentist trained in anxiety care", "online booking"],
         extras=["free parking", "payment plans", "acceptance of most insurance plans", "a children's corner", "text reminders"],
         best_for=["nervous patients", "families with children", "cosmetic treatments", "emergency visits", "patients on a budget"],
         price=("checkups from ${p}", 49, 129), unit="patients",
         metrics=["a patient rating of {rating} out of 5 from verified reviews", "{pct}% of patients seen within 10 minutes of their appointment time", "{num:5-25} years in practice"],
         anti_fit=["patients needing complex oral surgery", "people wanting weekend appointments", "patients without transport", "orthodontic treatment"],
         weak=["weekend availability", "parking", "waits for new patients", "insurance processing"], criterion="patient comfort")

scenario(id="pilates_beginner", vertical="Local services", kind="local", town="Marlow Heights", category="pilates studio",
         plural="pilates studios",
         query="Which pilates studio in Marlow Heights is best for a complete beginner?",
         need="complete beginners",
         features=["classes of up to 8 people", "beginner foundation courses", "reformer equipment", "private sessions",
                   "certified instructors", "flexible class passes", "an online class library", "early morning classes"],
         extras=["a free first class", "free mat and towel rental", "a referral discount", "on-site showers", "a booking app"],
         best_for=["complete beginners", "experienced practitioners", "people returning from injury with a physio referral", "busy professionals", "people on a budget"],
         price=("classes from ${p}", 18, 45), unit="members",
         metrics=["a member rating of {rating} out of 5 from verified reviews", "{pct}% of new members still attending after three months", "instructors averaging {num:3-12} years of experience"],
         anti_fit=["athletes wanting high-intensity training", "people wanting large gym facilities", "people needing late-night classes", "people who want yoga instead"],
         weak=["parking", "availability at peak times", "changing rooms", "drop-in pricing"], criterion="beginner friendliness")

scenario(id="restaurant_family", vertical="Local services", kind="local", town="Marlow Heights", category="restaurant",
         query="What's a good family-friendly restaurant in Marlow Heights for a birthday dinner with kids?",
         need="family celebrations",
         features=["a kids' menu", "private dining for groups", "high chairs and booster seats", "a birthday dessert tradition",
                   "a quiet back room", "gluten-free options", "online reservations", "a play corner"],
         extras=["free parking", "takeout", "vegetarian dishes", "outdoor seating", "wheelchair access"],
         best_for=["family celebrations", "romantic dinners", "quick lunches", "large groups", "diners on a budget"],
         price=("mains from ${p}", 12, 32), unit="diners",
         metrics=["a diner rating of {rating} out of 5 from verified reviews", "{num:40-120} seats including a private room", "{pct}% of reservations seated on time"],
         anti_fit=["quiet romantic dinners", "late-night dining", "fine-dining tasting menus", "parties of more than 30"],
         weak=["noise level", "weekend parking", "dessert menu", "wait times"], criterion="family friendliness")

scenario(id="budget_couples", vertical="Personal finance", category="budgeting app",
         query="What's the best budgeting app for a couple who wants to manage shared expenses?",
         need="couples sharing expenses",
         features=["shared household budgets", "automatic bank syncing", "bill reminders", "custom spending categories",
                   "savings goals", "split-expense tracking", "monthly spending reports", "two logins on one account"],
         extras=["a free trial", "bank-level encryption", "web and mobile apps", "CSV export", "no ads"],
         best_for=["couples sharing expenses", "people paying off debt", "freelancers with irregular income", "students on a budget", "investors tracking net worth"],
         price=("${p} per month", 3, 15), unit="households",
         metrics=["an average of ${num:300-900} saved by users in their first year in an internal survey", "{pct}% of linked accounts syncing without errors", "an average rating of {rating} stars from app store reviews"],
         anti_fit=["small businesses", "people wanting investment advice", "users who will not link bank accounts", "people who prefer spreadsheets"],
         weak=["investment tracking", "bank coverage outside the US", "reports", "category rules"], criterion="shared budgeting")

scenario(id="dogfood_picky", vertical="Pets", kind="product", category="dog food", plural="dog foods",
         query="Which dog food is best for a picky small-breed adult dog?",
         need="picky small dogs",
         features=["small kibble size", "real meat as the first ingredient", "grain-inclusive and grain-free recipes", "no artificial preservatives",
                   "a resealable bag", "added probiotics", "veterinarian-formulated recipes", "a wet food topper line"],
         extras=["a subscription discount", "free shipping over $50", "a satisfaction guarantee", "sample packs", "recyclable packaging"],
         best_for=["picky small dogs", "large-breed puppies", "dogs with sensitive stomachs", "active working dogs", "owners on a budget"],
         price=("${p} for a 4 lb bag", 14, 39), unit="dog owners",
         metrics=["{num:85-97}% of dogs finishing the bowl in a palatability trial", "an average rating of {rating} stars from verified buyers", "{num:3-9} recipes for small breeds"],
         anti_fit=["dogs on prescription diets", "large-breed puppies", "raw-food feeders", "owners who need 30 lb bags"],
         weak=["price per pound", "bag sizes", "store availability", "flavor variety"], criterion="palatability")

scenario(id="mealkit_veg", vertical="Food", kind="service", category="meal kit service",
         query="Which meal kit service is best for a vegetarian family of four?",
         need="vegetarian families",
         features=["a dedicated vegetarian menu", "family-size portions", "30-minute recipes", "flexible weekly skips",
                   "kid-friendly recipes", "recyclable packaging", "pre-chopped ingredients", "breakfast and snack add-ons"],
         extras=["a first-box discount", "no subscription commitment", "delivery in most regions", "allergen labeling", "a recipe app"],
         best_for=["vegetarian families", "couples who cook together", "people on low-carb diets", "busy professionals", "families on a budget"],
         price=("${p} per serving", 7, 13), unit="households",
         metrics=["{num:20-40} vegetarian recipes each week", "{pct}% of deliveries arriving on time", "an average rating of {rating} stars from verified customers"],
         anti_fit=["strict vegans", "people who live alone", "people with severe nut allergies", "households wanting fully prepared meals"],
         weak=["packaging volume", "portion sizes", "delivery windows", "spice levels"], criterion="vegetarian variety")

scenario(id="wp_hosting", vertical="Developer tools", category="WordPress hosting provider",
         query="What's the best WordPress hosting for a small food blog getting 30,000 visits a month?",
         need="small blogs",
         features=["one-click WordPress installs", "automatic daily backups", "free SSL certificates", "a built-in CDN",
                   "staging sites", "managed WordPress updates", "malware scanning", "24/7 chat support"],
         extras=["a free domain for the first year", "a 30-day money-back guarantee", "email hosting", "free site migration", "data centers on three continents"],
         best_for=["small blogs and portfolios", "online stores using WooCommerce", "agencies managing many sites", "high-traffic publishers", "beginners on a budget"],
         price=("${p} per month", 3, 30), unit="websites",
         metrics=["{num:99.90-99.99}% uptime over the last 12 months", "an average page load time of {num:0.4-1.4} seconds in tests", "{num:2-8} data center regions"],
         anti_fit=["enterprise sites needing dedicated servers", "developers wanting root access", "non-WordPress applications", "sites with millions of monthly visits"],
         weak=["renewal pricing", "email storage", "support response times", "dashboard"], criterion="speed and reliability")

scenario(id="ebike_commute", vertical="Mobility", kind="product", category="e-bike",
         query="What's the best e-bike for a 10-mile hilly commute?",
         need="hilly commutes",
         features=["a mid-drive motor", "a 60-mile range", "hydraulic disc brakes", "integrated lights",
                   "a rear rack", "a torque sensor", "puncture-resistant tires", "a removable battery"],
         extras=["a two-year warranty", "free assembly", "a 30-day test ride", "financing options", "a lock in the box"],
         best_for=["hilly commutes", "flat city errands", "off-road trails", "riders who need to fold the bike", "riders on a budget"],
         price=("${p}", 1199, 3499), unit="riders",
         metrics=["up to {num:40-80} miles of range in independent tests", "a weight of {num:18-28} kg", "an average rating of {rating} stars from verified buyers"],
         anti_fit=["mountain bike trails", "riders who need a folding bike", "riders wanting the lightest bike", "budgets under $1,000"],
         weak=["weight", "display", "kickstand", "service network"], criterion="hill climbing")

SCENARIOS = S
assert len({s["id"] for s in S}) == len(S) == 30
