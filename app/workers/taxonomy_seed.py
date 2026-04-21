"""Canonical SherrByte taxonomy.

9 pillars at the top level, each with a curated set of microtopics. Each
microtopic has a `prompt_gloss` — a natural-language sentence encoded into
the zero-shot classifier's embedding space. Match quality depends heavily on
these; revise them as you see misclassifications in production.

Starting with ~60 launch microtopics. You will add more over time via the
admin panel or BERTopic-driven discovery.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PillarSeed:
    slug: str
    name_en: str
    name_hi: str
    icon: str
    sort_order: int


@dataclass(frozen=True)
class MicrotopicSeed:
    slug: str
    pillar_slug: str
    name_en: str
    name_hi: str
    prompt_gloss: str


PILLARS: list[PillarSeed] = [
    PillarSeed("politics", "Politics", "राजनीति", "🏛", 10),
    PillarSeed("business", "Business & Economy", "बिज़नेस", "💼", 20),
    PillarSeed("tech", "Technology", "टेक्नोलॉजी", "💻", 30),
    PillarSeed("sports", "Sports", "खेल", "⚽", 40),
    PillarSeed("entertainment", "Entertainment", "मनोरंजन", "🎬", 50),
    PillarSeed("science", "Science & Health", "विज्ञान व स्वास्थ्य", "🔬", 60),
    PillarSeed("world", "World", "विश्व", "🌍", 70),
    PillarSeed("society", "Society & Culture", "समाज", "🫂", 80),
    PillarSeed("opinion", "Opinion & Analysis", "विचार", "💭", 90),
]


MICROTOPICS: list[MicrotopicSeed] = [
    # ---------- Politics ----------
    MicrotopicSeed(
        "politics-india-national", "politics",
        "Indian national politics", "भारतीय राष्ट्रीय राजनीति",
        "News about India's national government, parliament, BJP, Congress, cabinet decisions, and central policy.",
    ),
    MicrotopicSeed(
        "politics-india-state", "politics",
        "Indian state politics", "भारतीय राज्य राजनीति",
        "News about Indian state governments, chief ministers, assembly elections, and regional parties.",
    ),
    MicrotopicSeed(
        "politics-elections", "politics",
        "Elections & campaigns", "चुनाव",
        "Coverage of elections, election results, voter turnout, political campaigns, and election commission.",
    ),
    MicrotopicSeed(
        "politics-policy", "politics",
        "Government policy", "सरकारी नीति",
        "Coverage of new laws, policies, government schemes, and legislation.",
    ),
    MicrotopicSeed(
        "politics-diplomacy", "politics",
        "Diplomacy & foreign affairs", "कूटनीति",
        "India's diplomatic relations, foreign policy, bilateral talks, and international summits.",
    ),
    MicrotopicSeed(
        "politics-defence", "politics",
        "Defence & security", "रक्षा",
        "Indian armed forces, defence deals, border security, and military exercises.",
    ),

    # ---------- Business ----------
    MicrotopicSeed(
        "business-markets", "business",
        "Stock markets", "शेयर बाज़ार",
        "Coverage of Sensex, Nifty, stock markets, trading, and equity movement in India.",
    ),
    MicrotopicSeed(
        "business-startups", "business",
        "Startups & venture capital", "स्टार्टअप",
        "Indian startups, funding rounds, unicorns, venture capital, and founders.",
    ),
    MicrotopicSeed(
        "business-crypto", "business",
        "Cryptocurrency", "क्रिप्टोकरेंसी",
        "Bitcoin, Ethereum, crypto regulation in India, Web3, and blockchain news.",
    ),
    MicrotopicSeed(
        "business-economy", "business",
        "Indian economy", "भारतीय अर्थव्यवस्था",
        "Indian GDP, inflation, RBI monetary policy, interest rates, and macroeconomics.",
    ),
    MicrotopicSeed(
        "business-companies", "business",
        "Corporate India", "कंपनी जगत",
        "Earnings, mergers, leadership changes, and news about Indian corporates like Reliance, Tata, Adani, Infosys.",
    ),
    MicrotopicSeed(
        "business-realestate", "business",
        "Real estate & housing", "रियल एस्टेट",
        "Indian real estate market, housing prices, construction, RERA, and property trends.",
    ),
    MicrotopicSeed(
        "business-autos", "business",
        "Autos & mobility", "ऑटो",
        "Indian automobile industry, electric vehicles, Tata Motors, Mahindra, Maruti, and auto sales.",
    ),

    # ---------- Tech ----------
    MicrotopicSeed(
        "tech-ai", "tech",
        "Artificial intelligence", "एआई",
        "Artificial intelligence, large language models, ChatGPT, Gemini, generative AI, and AI policy.",
    ),
    MicrotopicSeed(
        "tech-gadgets", "tech",
        "Gadgets & consumer tech", "गैजेट्स",
        "Smartphones, laptops, launches, reviews, Apple, Samsung, Xiaomi, and OnePlus devices.",
    ),
    MicrotopicSeed(
        "tech-internet", "tech",
        "Internet & social media", "इंटरनेट",
        "Social media platforms, Facebook, Instagram, X, YouTube, WhatsApp, content moderation.",
    ),
    MicrotopicSeed(
        "tech-cybersecurity", "tech",
        "Cybersecurity & privacy", "साइबर सुरक्षा",
        "Data breaches, ransomware, cybersecurity incidents, privacy, DPDP Act, and online scams.",
    ),
    MicrotopicSeed(
        "tech-space", "tech",
        "Space & ISRO", "अंतरिक्ष",
        "ISRO missions, Chandrayaan, Aditya-L1, Gaganyaan, SpaceX, and global space programs.",
    ),
    MicrotopicSeed(
        "tech-telecom", "tech",
        "Telecom & 5G", "टेलीकॉम",
        "Jio, Airtel, Vi, 5G rollout, spectrum auctions, and Indian telecom regulation.",
    ),

    # ---------- Sports ----------
    MicrotopicSeed(
        "sports-cricket", "sports",
        "Cricket", "क्रिकेट",
        "Indian cricket team, IPL, Test matches, World Cup, BCCI, and cricket statistics.",
    ),
    MicrotopicSeed(
        "sports-football", "sports",
        "Football", "फुटबॉल",
        "Football matches, Premier League, La Liga, Champions League, FIFA World Cup, and ISL.",
    ),
    MicrotopicSeed(
        "sports-olympics", "sports",
        "Olympics & multi-sport", "ओलंपिक्स",
        "Olympic Games, Commonwealth Games, Asian Games, Paralympics, and medal coverage.",
    ),
    MicrotopicSeed(
        "sports-tennis", "sports",
        "Tennis", "टेनिस",
        "Tennis, Wimbledon, Australian Open, US Open, French Open, and ATP/WTA tours.",
    ),
    MicrotopicSeed(
        "sports-kabaddi-hockey", "sports",
        "Kabaddi, hockey & Indian sports", "कबड्डी-हॉकी",
        "Pro Kabaddi League, hockey, Indian traditional sports, and domestic leagues.",
    ),

    # ---------- Entertainment ----------
    MicrotopicSeed(
        "ent-bollywood", "entertainment",
        "Bollywood", "बॉलीवुड",
        "Bollywood movies, actors, box office, film releases, and Hindi cinema.",
    ),
    MicrotopicSeed(
        "ent-south-cinema", "entertainment",
        "South Indian cinema", "दक्षिण भारतीय सिनेमा",
        "Tamil, Telugu, Malayalam, Kannada cinema, Tollywood, Kollywood, Mollywood, and Sandalwood.",
    ),
    MicrotopicSeed(
        "ent-ott", "entertainment",
        "OTT & streaming", "ओटीटी",
        "Netflix, Amazon Prime, Disney+ Hotstar, JioCinema, web series, and streaming releases.",
    ),
    MicrotopicSeed(
        "ent-music", "entertainment",
        "Music", "संगीत",
        "Indian and international music, albums, concerts, singers, and award shows.",
    ),
    MicrotopicSeed(
        "ent-celebrity", "entertainment",
        "Celebrity news", "सेलिब्रिटी",
        "Celebrity weddings, relationships, public appearances, and lifestyle coverage.",
    ),

    # ---------- Science & Health ----------
    MicrotopicSeed(
        "sci-climate", "science",
        "Climate & environment", "जलवायु व पर्यावरण",
        "Climate change, pollution, heatwaves, floods, renewable energy, and environmental policy.",
    ),
    MicrotopicSeed(
        "sci-medicine", "science",
        "Medicine & health", "चिकित्सा",
        "Medical research, disease outbreaks, public health, hospitals, and health policy.",
    ),
    MicrotopicSeed(
        "sci-mental-health", "science",
        "Mental health", "मानसिक स्वास्थ्य",
        "Mental health awareness, anxiety, depression, therapy, and wellbeing.",
    ),
    MicrotopicSeed(
        "sci-research", "science",
        "Scientific research", "वैज्ञानिक शोध",
        "Published scientific research, discoveries, Nobel Prizes, and breakthroughs.",
    ),
    MicrotopicSeed(
        "sci-fitness", "science",
        "Fitness & nutrition", "फिटनेस",
        "Exercise, nutrition, diet, yoga, and physical wellbeing.",
    ),

    # ---------- World ----------
    MicrotopicSeed(
        "world-us", "world",
        "United States", "अमेरिका",
        "US politics, US economy, Federal Reserve, White House, and American news.",
    ),
    MicrotopicSeed(
        "world-china", "world",
        "China", "चीन",
        "Chinese economy, politics, Xi Jinping, Taiwan tensions, and China-India relations.",
    ),
    MicrotopicSeed(
        "world-middleeast", "world",
        "Middle East", "मध्य पूर्व",
        "Israel, Palestine, Gaza, Iran, Saudi Arabia, UAE, and Middle Eastern conflict.",
    ),
    MicrotopicSeed(
        "world-europe", "world",
        "Europe", "यूरोप",
        "European Union, UK, Germany, France, Italy, and European politics.",
    ),
    MicrotopicSeed(
        "world-neighbours", "world",
        "South Asia neighbours", "पड़ोसी देश",
        "Pakistan, Bangladesh, Nepal, Sri Lanka, Bhutan, Maldives, and South Asian affairs.",
    ),
    MicrotopicSeed(
        "world-war-conflict", "world",
        "War & conflict", "युद्ध व संघर्ष",
        "Ukraine-Russia war, armed conflict, ceasefires, and international peace efforts.",
    ),

    # ---------- Society ----------
    MicrotopicSeed(
        "society-education", "society",
        "Education", "शिक्षा",
        "Indian schools, colleges, IIT, NEET, JEE, UGC, NEP, and education policy.",
    ),
    MicrotopicSeed(
        "society-gender", "society",
        "Gender & women", "लिंग व महिला",
        "Women's rights, gender equality, feminism, and women in leadership.",
    ),
    MicrotopicSeed(
        "society-caste-religion", "society",
        "Caste & religion", "जाति व धर्म",
        "Caste, reservation, Hindu-Muslim relations, minority rights, and religious affairs.",
    ),
    MicrotopicSeed(
        "society-crime", "society",
        "Crime & justice", "अपराध व न्याय",
        "Crime, arrests, court judgments, Supreme Court rulings, and law enforcement.",
    ),
    MicrotopicSeed(
        "society-farmers", "society",
        "Agriculture & farmers", "किसान",
        "Indian farmers, agriculture policy, MSP, farm laws, crop prices, and rural issues.",
    ),
    MicrotopicSeed(
        "society-lifestyle", "society",
        "Lifestyle", "जीवनशैली",
        "Travel, food, fashion, parenting, home, and daily life coverage.",
    ),
    MicrotopicSeed(
        "society-disasters", "society",
        "Disasters & weather", "आपदा",
        "Cyclones, earthquakes, floods, monsoon, heatwaves, and disaster response.",
    ),

    # ---------- Opinion ----------
    MicrotopicSeed(
        "opinion-editorial", "opinion",
        "Editorials", "संपादकीय",
        "Newspaper editorials and opinion pieces on current affairs.",
    ),
    MicrotopicSeed(
        "opinion-analysis", "opinion",
        "Analysis & long-form", "विश्लेषण",
        "Long-form analysis, investigations, and explainers on complex issues.",
    ),
    MicrotopicSeed(
        "opinion-interview", "opinion",
        "Interviews", "साक्षात्कार",
        "Interviews with politicians, business leaders, celebrities, and public figures.",
    ),
]
