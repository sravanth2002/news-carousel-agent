from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    hint: str
    feeds: dict[str, str]
    keywords: tuple[str, ...] = ()
    fallback: str = "newspaper"  # Commons search if the story's own image is missing


TC = "https://techcrunch.com/feed/"
VERGE = "https://www.theverge.com/rss/index.xml"
ET_TECH = "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms"
HINDU_BIZ = "https://www.thehindu.com/business/feeder/default.rss"
BBC_BIZ = "https://feeds.bbci.co.uk/news/business/rss.xml"

CATEGORIES = [
    Category(
        "ai",
        "AI UPDATE",
        "the newest AI development (new model, LLM, launch) and, if the text supports it, one pro or con of AI's impact",
        {
            "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
            "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        },
        fallback="artificial intelligence",
    ),
    Category(
        "economy",
        "ECONOMY",
        "how India's economy and other countries' economies affect each other (trade, tariffs, oil, currency, investment)",
        {
            "ET Economy": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
            "The Hindu Business": HINDU_BIZ,
            "BBC Business": BBC_BIZ,
        },
        fallback="Reserve Bank of India",
    ),
    Category(
        "politics",
        "INDIA POLITICS",
        "a political development in India and its impact on people or business",
        {
            "The Hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
            "Indian Express": "https://indianexpress.com/section/india/feed/",
        },
        fallback="Parliament of India",
    ),
    Category("stocks", "MARKETS", "", {}, fallback="stock exchange"),
    Category(
        "tech",
        "TECH",
        "a notable technological advancement (new chip, device, vehicle, robot, science breakthrough)",
        {"The Verge": VERGE, "TechCrunch": TC, "Engadget": "https://www.engadget.com/rss.xml"},
        fallback="technology",
    ),
    Category(
        "jobs",
        "JOBS",
        "which companies are hiring or cutting jobs and for which roles",
        {
            "ET Tech": ET_TECH,
            "The Hindu Business": HINDU_BIZ,
            "BBC Business": BBC_BIZ,
            "TechCrunch": TC,
        },
        keywords=(
            "hiring",
            "jobs",
            "layoff",
            "recruit",
            "workforce",
            "employ",
            "openings",
            "talent",
        ),
        fallback="office",
    ),
    Category(
        "masters",
        "MASTERS ABROAD",
        "Indian students going abroad for a Master's: country rules, visas, admissions, entrance exams, curriculum changes",
        {
            "PIE News": "https://thepienews.com/feed/",
            "Indian Express Education": "https://indianexpress.com/section/education/feed/",
            "Hindustan Times Education": "https://www.hindustantimes.com/feeds/rss/education/rssfeed.xml",
        },
        keywords=(
            "abroad",
            "student",
            "visa",
            "master",
            "university",
            "germany",
            "admission",
            "international",
        ),
        fallback="university campus",
    ),
    Category(
        "startups",
        "STARTUPS",
        "a notable startup funding round, launch or exit, preferably India-related",
        {
            "Inc42": "https://inc42.com/feed/",
            "TechCrunch Startups": "https://techcrunch.com/category/startups/feed/",
        },
        fallback="startup office",
    ),
    Category(
        "cyber",
        "CYBERSECURITY",
        "a major data breach, cyberattack, scam or security flaw and what people should do",
        {
            "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
            "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
        },
        fallback="cybersecurity",
    ),
    Category(
        "space",
        "SPACE & SCIENCE",
        "a space or science development (ISRO, NASA, missions, discoveries)",
        {
            "NASA": "https://www.nasa.gov/feed/",
            "The Hindu Science": "https://www.thehindu.com/sci-tech/science/feeder/default.rss",
        },
        fallback="space rocket",
    ),
]
