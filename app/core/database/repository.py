"""Repository for conversation, user, message, and document operations."""

from datetime import datetime
from uuid import UUID

import logfire
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import (
    Conversation,
    Document,
    DocumentChunk,
    Message,
    User,
)


class ConversationRepository:
    """Repository for user, conversation, and message database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_or_create_user(
        self, phone_number: str, name: str | None = None
    ) -> User:
        """Get existing user or create new one.

        Args:
            phone_number: WhatsApp phone number
            name: User name (pushName from WhatsApp)

        Returns:
            User instance
        """
        try:
            # Try to get existing user
            stmt = select(User).where(User.phone_number == phone_number)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                # Update name if provided and different
                if name and user.name != name:
                    user.name = name
                    await self.session.flush()
                    logfire.info(
                        "User updated",
                        phone_number=phone_number,
                        name=name,
                    )
                return user

            # Create new user
            user = User(phone_number=phone_number, name=name)
            self.session.add(user)
            await self.session.flush()
            logfire.info(
                "User created",
                phone_number=phone_number,
                user_id=str(user.id),
            )
            return user

        except Exception as e:
            logfire.error(
                "Error in get_or_create_user",
                phone_number=phone_number,
                error=str(e),
                exc_info=e,
            )
            raise

    async def get_active_conversation(
        self, user_id: UUID
    ) -> Conversation | None:
        """Get active conversation for user.

        Args:
            user_id: User ID

        Returns:
            Active conversation or None
        """
        try:
            stmt = (
                select(Conversation)
                .where(
                    (Conversation.user_id == user_id)
                    & (Conversation.is_active == True)  # noqa: E712
                )
                .order_by(Conversation.created_at.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            conversation = result.scalar_one_or_none()

            return conversation

        except Exception as e:
            logfire.error(
                "Error in get_active_conversation",
                user_id=str(user_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def create_conversation(self, user_id: UUID) -> Conversation:
        """Create new conversation for user.

        Args:
            user_id: User ID

        Returns:
            New conversation instance
        """
        try:
            conversation = Conversation(user_id=user_id, is_active=True)
            self.session.add(conversation)
            await self.session.flush()

            logfire.info(
                "Conversation created",
                conversation_id=str(conversation.id),
                user_id=str(user_id),
            )
            return conversation

        except Exception as e:
            logfire.error(
                "Error in create_conversation",
                user_id=str(user_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        message_id: str | None = None,
    ) -> Message:
        """Add message to conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role ("user" or "assistant")
            content: Message content
            message_id: WhatsApp message ID (optional)

        Returns:
            Created message instance
        """
        try:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_id=message_id,
            )
            self.session.add(message)
            await self.session.flush()

            return message

        except Exception as e:
            logfire.error(
                "Error in add_message",
                conversation_id=str(conversation_id),
                role=role,
                error=str(e),
                exc_info=e,
            )
            raise

    async def get_recent_messages(
        self, conversation_id: UUID, limit: int = 15
    ) -> list[Message]:
        """Get recent messages from conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages ordered by creation time (oldest first)
        """
        try:
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            messages = result.scalars().all()

            # Reverse to get oldest first (proper conversation order)
            messages_ordered = list(reversed(messages))

            return messages_ordered

        except Exception as e:
            logfire.error(
                "Error in get_recent_messages",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def get_last_message_time(
        self, conversation_id: UUID
    ) -> datetime | None:
        """Get the creation time of the last message in a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Datetime of last message or None if no messages
        """
        try:
            stmt = (
                select(Message.created_at)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            last_time: datetime | None = result.scalar_one_or_none()
            return last_time

        except Exception as e:
            logfire.error(
                "Error in get_last_message_time",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def close_conversation(self, conversation_id: UUID) -> None:
        """Close (deactivate) conversation.

        Args:
            conversation_id: Conversation ID
        """
        try:
            stmt = select(Conversation).where(
                Conversation.id == conversation_id
            )
            result = await self.session.execute(stmt)
            conversation = result.scalar_one_or_none()

            if conversation:
                conversation.is_active = False
                await self.session.flush()
                logfire.info(
                    "Conversation closed",
                    conversation_id=str(conversation_id),
                )
            else:
                logfire.warn(
                    "Conversation not found for closing",
                    conversation_id=str(conversation_id),
                )

        except Exception as e:
            logfire.error(
                "Error in close_conversation",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=e,
            )
            raise


class DocumentRepository:
    """Repository for document and document chunk operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create_document(
        self,
        nombre: str,
        descripcion: str,
        file_type: str,
        school: str,
        file_url: str,
        is_active: bool = True,
    ) -> Document:
        """Create a new document.

        Args:
            nombre: Document name
            descripcion: Document description
            file_type: File type (pdf, docx, etc.)
            school: School/Faculty name
            file_url: URL of the document file
            is_active: Whether document is active

        Returns:
            Created document instance
        """
        try:
            document = Document(
                nombre=nombre,
                descripcion=descripcion,
                file_type=file_type,
                school=school,
                file_url=file_url,
                is_active=is_active,
            )
            self.session.add(document)
            await self.session.flush()

            logfire.info(
                "Document created",
                document_id=str(document.id),
                nombre=nombre,
                school=school,
            )
            return document

        except Exception as e:
            logfire.error(
                "Error creating document",
                nombre=nombre,
                school=school,
                error=str(e),
                exc_info=e,
            )
            raise

    async def soft_delete_document(self, document_id: UUID) -> bool:
        """Soft delete a document (mark as inactive).

        Args:
            document_id: Document ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            stmt = select(Document).where(Document.id == document_id)
            result = await self.session.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                logfire.warning(
                    "Document not found for deletion",
                    document_id=str(document_id),
                )
                return False

            document.is_active = False
            await self.session.flush()

            logfire.info(
                "Document soft deleted",
                document_id=str(document_id),
            )
            return True

        except Exception as e:
            logfire.error(
                "Error deleting document",
                document_id=str(document_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def get_active_documents(
        self, school: str | None = None
    ) -> list[Document]:
        """Get all active documents, optionally filtered by school.

        Args:
            school: Optional school filter

        Returns:
            List of active documents
        """
        try:
            stmt = select(Document).where(Document.is_active == True)  # noqa: E712

            if school:
                stmt = stmt.where(Document.school == school)

            stmt = stmt.order_by(Document.created_at.desc())
            result = await self.session.execute(stmt)
            documents = list(result.scalars().all())

            return documents

        except Exception as e:
            logfire.error(
                "Error retrieving documents",
                school=school,
                error=str(e),
                exc_info=e,
            )
            raise

    async def get_document_by_id(self, document_id: UUID) -> Document | None:
        """Get document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document instance or None if not found
        """
        try:
            stmt = select(Document).where(Document.id == document_id)
            result = await self.session.execute(stmt)
            document = result.scalar_one_or_none()

            return document

        except Exception as e:
            logfire.error(
                "Error retrieving document",
                document_id=str(document_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def delete_chunks_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of chunks deleted
        """
        try:
            # Count first
            count_stmt = select(func.count()).where(
                DocumentChunk.document_id == document_id
            )
            count_result = await self.session.execute(count_stmt)
            count = count_result.scalar() or 0

            # Delete
            stmt = delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
            await self.session.execute(stmt)
            await self.session.flush()

            logfire.info(
                "Chunks deleted",
                document_id=str(document_id),
                chunks_deleted=count,
            )
            return count

        except Exception as e:
            logfire.error(
                "Error deleting chunks",
                document_id=str(document_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def get_chunks_count(self, document_id: UUID) -> int:
        """Get the number of chunks for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of chunks
        """
        stmt = select(func.count()).where(
            DocumentChunk.document_id == document_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
