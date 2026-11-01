"""What we embed for each page (the vectors themselves come from llm.get_embedder).

A page's embedding should capture what the page is about, so the text we send matters more
than anything else here:
- once the page is summarised: its title, summary and key points. A summary is the page's
  meaning in a few clean sentences, free of menus, cookie banners and boilerplate.
- before that: the title, the site's description and the opening of the page text.
- pages we couldn't read: the title and description alone, preferring the title the user
  saved when we have nothing else; sign-in pages get no embedding at all.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import llm
from app.models import Bookmark, Document, DocumentStatus

# About 1,500 tokens. The model takes up to 8,192, but a page's opening says what it's about,
# and a long text blurs the vector towards everything the page mentions.
MAX_PAGE_CHARS = 6_000


@dataclass
class EmbeddingText:
    text: str  # formatted for the model ("title: … | text: …")
    source: str  # what it was made from: "summary", "page" or "metadata"


def embedding_text(document: Document, saved_title: str | None = None) -> EmbeddingText | None:
    """The text to embed for `document`, or None when it isn't worth embedding.

    `saved_title` is the title a user saved the bookmark under: the browser took it while they
    were looking at the page, so it often says more than what we could fetch.
    """
    if document.access == "login" and not document.content_text:
        # All we saw was a sign-in screen (Gmail, Outlook, a company GitLab). An embedding of
        # "sign in" sits close to every search, so these get none; keyword search still finds
        # them by the user's saved title and folders.
        return None

    title = document.title or saved_title or document.url

    if document.summary_status == "done" and document.summary:
        body = "\n".join([document.summary, *(document.key_points or [])])
        return EmbeddingText(llm.document_for_embedding(title, body), "summary")

    page_text = document.content_text
    if document.status == DocumentStatus.dead and document.content_source != "archive":
        page_text = None  # what the live page used to say, not what anyone can read now
    if not page_text and not document.description:
        # Only a title to go on: the saved one beats a fetched one, which may be a placeholder
        # ("Site en construction" was saved as "The Hacker Playbook 2").
        title = saved_title or title
    parts = [document.description, page_text[:MAX_PAGE_CHARS] if page_text else None]
    body = "\n".join(part for part in parts if part)
    source = "page" if page_text else "metadata"
    return EmbeddingText(llm.document_for_embedding(title, body or document.site), source)


async def saved_title(session: AsyncSession, document_id: int) -> str | None:
    """The title the page was first saved under (pages are shared, so any user's will do)."""
    return await session.scalar(
        select(Bookmark.title)
        .where(Bookmark.document_id == document_id, Bookmark.deleted_at.is_(None))
        .order_by(Bookmark.id)
        .limit(1)
    )
