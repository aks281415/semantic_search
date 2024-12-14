## implementation of document_service.py (Phase 1: Basic Setup and Document Processing) 
input
docs/
├── pdfs/
│   ├── brown_v_board.pdf         # Input PDF 1
│   └── miranda_v_arizona.pdf     # Input PDF 2
└── metadata.json                 # Input Metadata

[
    {
        "filename": "brown_v_board.pdf",
        "case": "Brown v. Board of Education",
        "year": 1954,
        "court": "Supreme Court",
        "citation": "347 U.S. 483"
    },
    {
        "filename": "miranda_v_arizona.pdf",
        "case": "Miranda v. Arizona",
        "year": 1966,
        "court": "Supreme Court",
        "citation": "384 U.S. 436"
    }
]

output 

[
    {
        "content": "We conclude that in the field of public education...",  # Full PDF text
        "metadata": {
            "filename": "brown_v_board.pdf",
            "case": "Brown v. Board of Education",
            "year": 1954,
            "court": "Supreme Court",
            "citation": "347 U.S. 483"
        }
    },
    {
        "content": "The person in custody must, prior to interrogation...",  # Full PDF text
        "metadata": {
            "filename": "miranda_v_arizona.pdf",
            "case": "Miranda v. Arizona",
            "year": 1966,
            "court": "Supreme Court",
            "citation": "384 U.S. 436"
        }
    }
]

## Phase 2: Text Processing and Chunking
We have documents now in this format:
# Current Input (from Phase 1):
{
    "content": "Full long text from PDF...",
    "metadata": {
        "filename": "brown_v_board.pdf",
        "case": "Brown v. Board of Education",
        # ... other metadata
    }
}

Need for Chunking:

PDFs have long text content
OpenAI has token limits
Better search precision with smaller chunks
Each chunk needs to keep its parent document's metadata

# output

# After chunking, each chunk will look like this:
[
    # First Chunk
    {
        "chunk_id": "550e8400-e29b-41d4-a716-446655440000",  # UUID
        "content": "In Miranda v. Arizona (1966) the Supreme Court held that the Fifth Amendment...",
        "metadata": {
            # Original metadata preserved
            "filename": "miranda_v_arizona.pdf",
            "case": "Miranda v. Arizona",
            "year": 1966,
            "court": "Supreme Court",
            "citation": "384 U.S. 436",
            
            # Chunk-specific metadata added
            "chunk_index": 0,
            "is_first_chunk": True,
            "chunk_start": 0,
            "chunk_end": 1000,
            "total_chunks": 3  # If document was split into 3 chunks
        }
    },

    # Second Chunk
    {
        "chunk_id": "550e8400-e29b-41d4-a716-446655440001",
        "content": "The Court established that police must inform suspects of their rights...",
        "metadata": {
            # Original metadata same as above
            "filename": "miranda_v_arizona.pdf",
            "case": "Miranda v. Arizona",
            "year": 1966,
            "court": "Supreme Court",
            "citation": "384 U.S. 436",
            
            # Different chunk-specific metadata
            "chunk_index": 1,
            "is_first_chunk": False,
            "chunk_start": 900,  # Note overlap with previous chunk
            "chunk_end": 1900,
            "total_chunks": 3
        }
    },
    # ... more chunks
]

# Output (all chunks from all documents)
all_chunks = [
    # Chunks from Brown v. Board
    {
        "chunk_id": "uuid1",
        "content": "Brown v. Board chunk 1...",
        "metadata": {"case": "Brown v. Board", "chunk_index": 0, ...}
    },
    {
        "chunk_id": "uuid2",
        "content": "Brown v. Board chunk 2...",
        "metadata": {"case": "Brown v. Board", "chunk_index": 1, ...}
    },
    # Chunks from Miranda v. Arizona
    {
        "chunk_id": "uuid3",
        "content": "Miranda v. Arizona chunk 1...",
        "metadata": {"case": "Miranda v. Arizona", "chunk_index": 0, ...}
    },
    # ... more chunks
]

## implementation of document_service.py (Phase 3: embedding and vector database storage)

do we need indexing?

# Current Search (might be slower)
results = index.query(
    vector=query_embedding,
    top_k=5
)

# With Proper Indexing (faster & more efficient)
results = index.query(
    vector=query_embedding,
    top_k=5,
    filter={
        "year": {"$gte": 1950},
        "court": "Supreme Court"
    }
)

we have metadata indexing , namespace based indexing , hybrid search index

# namespace based chunking
vectors_supreme = [...] # vectors from Supreme Court cases
vectors_district = [...] # vectors from District Court cases

(Upsert with different namespaces)
index.upsert(vectors=vectors_supreme, namespace='supreme_court')
index.upsert(vectors=vectors_district, namespace='district_court')

# hybrid search index (Include both sparse and dense vectors)
vector_with_keywords = {
    "id": "chunk_1",
    "values": embedding,
    "sparse_values": {
        "indices": [14, 23, 45],  # Positions of important legal terms
        "values": [1.0, 0.8, 0.6]  # Importance scores
    },
    "metadata": {...}
}

# other traditional vector database indexing
Types:
a. Flat Index (Brute Force)
   - Compares query with every vector
   - Accurate but slow for large datasets

b. IVF (Inverted File Index)
   - Clusters similar vectors
   - Faster search but slight accuracy trade-off

c. HNSW (Hierarchical Navigable Small World)
   - Graph-based approach
   - Balance between speed and accuracy


# Input: Takes chunks from Phase 2
# Processes them into Pinecone Vectors

# Output: Vectors in Pinecone
{
    "id": "uuid1",
    "values": [0.123, 0.456, ...],  # 1536-dimensional vector
    "metadata": {
        "filename": "brown_v_board.pdf",
        "case": "Brown v. Board",
        "year": 1954,
        "chunk_index": 0,
        "is_first_chunk": True,
        "content": "The Supreme Court case of Brown...",
        "processed_at": 1709584372.45  # timestamp
    }
}

## implementation of search_service.py (Phase 4: search )

# Input (POST /api/search)
{
    "query": "What did the Supreme Court say about segregation in schools?"
}

# Output
{
    "results": [
        {
            "content": "The Court found that separate educational facilities are inherently unequal...",
            "metadata": {
                "case": "Brown v. Board of Education",
                "year": 1954,
                "court": "Supreme Court",
                "citation": "347 U.S. 483"
            },
            "similarity_score": 0.89
        },
        {
            // More results...
        }
    ],
    "total_results": 5,
    "processing_time": "0.5s"
}

# Input (GET /api/search/health)
No input required

# Output
{
    "status": "healthy",
    "cache_size": 50,
    "active_connections": 5
}
# OR if unhealthy
{
    "status": "unhealthy",
    "error": "Connection to Pinecone failed"
}






