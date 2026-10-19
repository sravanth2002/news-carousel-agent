from pydantic import BaseModel


class Article(BaseModel):
    title: str
    link: str
    source: str
    summary: str = ""
    image_url: str = ""
    ts: float = 0


class Pick(BaseModel):
    id: int
    headline: str
    body: str
    subject: str = ""


class Slide(BaseModel):
    category: str = ""
    headline: str
    body: str = ""
    source: str
    link: str = ""
    image_url: str = ""
    keywords: str = ""
    subject: str = ""
    rows: list[list[str]] = []
