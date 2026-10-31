
from dataclasses import dataclass

import strawberry
from fastapi import Depends
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info


# 1. Internal data models
@dataclass(frozen=True)
class DocumentRow:
    id: int
    filename: str
    owner_id: int


@dataclass(frozen=True)
class OwnerRow:
    id: int
    email: str


# 2. Mock repository (temporary in-memory data)
class MockDocumentRepository:
    def __init__(
        self,
        documents: list[DocumentRow] | None = None,
        owners: list[OwnerRow] | None = None,
    ):
        self._documents = (
            documents
            if documents is not None
            else [
                DocumentRow(1, "guide.pdf", 101),
                DocumentRow(2, "testing.pdf", 102),
                DocumentRow(3, "roadmap.pdf", 101),
            ]
        )

        self._owners = (
            owners
            if owners is not None
            else [
                OwnerRow(101, "dev@example.com"),
                OwnerRow(102, "qa@example.com"),
            ]
        )

        self.query_count = 0

    def list_documents(self) -> list[DocumentRow]:
        self.query_count += 1
        return list(self._documents)

    def get_owners_by_ids(
        self, owner_ids: set[int]
    ) -> dict[int, OwnerRow]:
        self.query_count += 1

        return {
            owner.id: owner
            for owner in self._owners
            if owner.id in owner_ids
        }


# 3. GraphQL schema type
@strawberry.type
class DocumentType:
    id: strawberry.ID
    filename: str
    owner_email: str | None


# 4. FastAPI dependency
def get_document_repository() -> MockDocumentRepository:
    return MockDocumentRepository()


# 5. Request-specific GraphQL context
async def get_graphql_context(
    repository: MockDocumentRepository = Depends(
        get_document_repository
    ),
) -> dict:
    return {"repository": repository}


# 6. GraphQL query resolver
@strawberry.type
class Query:
    @strawberry.field
    async def documents(self, info: Info) -> list[DocumentType]:
        repository: MockDocumentRepository = (
            info.context["repository"]
        )

        documents = repository.list_documents()

        if not documents:
            return []

        # Batch-fetch all owners, avoiding one lookup
        # per document.
        owner_ids = {doc.owner_id for doc in documents}
        owners = repository.get_owners_by_ids(owner_ids)

        return [
            DocumentType(
                id=strawberry.ID(str(doc.id)),
                filename=doc.filename,
                owner_email=(
                    owners[doc.owner_id].email
                    if doc.owner_id in owners
                    else None
                ),
            )
            for doc in documents
        ]


# 7. Create schema and router
schema = strawberry.Schema(query=Query)

graphql_router = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
)
