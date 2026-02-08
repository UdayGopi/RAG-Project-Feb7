# 📎 Source Attribution Guide

**Ensuring RAG responses show original URLs, not extracted content**

## Problem

By default, RAG systems might show extracted text as "sources", which is:
- ❌ Not user-friendly (walls of text)
- ❌ Not verifiable (can't click to check)
- ❌ Not professional (looks messy)

**What users want:**
- ✅ Original URLs (e.g., `https://www.cms.gov/page`)
- ✅ Clickable links
- ✅ Clean citations
- ✅ Page numbers (for PDFs)

---

## Solution Implemented

### 1. URL Tracking During Ingestion

**File: `utils/url_tracker.py`**

```python
from utils.url_tracker import enrich_documents_with_urls

# When processing URLs
documents = web_reader.load_data(urls=[url])
enrich_documents_with_urls(documents, url=url, title="Page Title")

# Result: Each document gets metadata
doc.metadata = {
    'url': 'https://www.cms.gov/page',
    'source': 'https://www.cms.gov/page',  # KEY!
    'domain': 'www.cms.gov',
    'title': 'Page Title',
    'source_type': 'webpage'
}
```

### 2. File Metadata Tracking

```python
from utils.url_tracker import enrich_file_with_metadata

# When processing files
documents = PDFReader().load_data(file_path)
enrich_file_with_metadata(documents, file_path=path, tenant_id="HIH")

# Result: Each document gets metadata
doc.metadata = {
    'source': 'policy_document.pdf',
    'file_name': 'policy_document.pdf',
    'file_path': '/path/to/policy_document.pdf',
    'source_type': 'file',
    'page_number': 5
}
```

### 3. Source Formatting

**File: `utils/url_tracker.py`**

```python
from utils.url_tracker import format_sources_with_urls

# Format sources for response
sources = format_sources_with_urls(source_nodes)

# Result:
[
    {
        "index": 1,
        "source": "https://www.cms.gov/medicare/regulations",  # URL, not text!
        "type": "webpage",
        "domain": "www.cms.gov",
        "title": "Medicare Regulations",
        "score": 0.92
    },
    {
        "index": 2,
        "source": "HIH_Policy_2024.pdf",  # Filename, not content!
        "type": "file",
        "page": 5,
        "score": 0.88
    }
]
```

---

## Usage in RAG Agent

### During Document Ingestion

```python
from utils.url_tracker import enrich_documents_with_urls, enrich_file_with_metadata
from ingestion.url_processor import URLProcessor

# For URLs
processor = URLProcessor()
documents = processor.process_url(url, tenant_id="HIH")
# URLs automatically added to metadata!

# For files
from llama_index.core import SimpleDirectoryReader
documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
enrich_file_with_metadata(documents, file_path, tenant_id="HIH")
```

### During Query Response

```python
from utils.url_tracker import format_sources_with_urls, deduplicate_sources

# In your RAG query function
def query(self, query: str):
    # ... retrieval logic ...
    
    # Format sources (URLs, not content!)
    sources = format_sources_with_urls(rag_response.source_nodes)
    
    # Remove duplicates
    sources = deduplicate_sources(sources)
    
    return {
        "summary": "...",
        "detailed_response": "...",
        "sources": sources  # Clean URLs!
    }
```

---

## API Response Format

### Before (Bad - Shows Extracted Text):

```json
{
  "sources": [
    {
      "text": "Medicare Part A covers inpatient hospital stays, care in a skilled nursing facility, hospice care, and some home health care. Beneficiaries must meet certain conditions...",
      "score": 0.92
    }
  ]
}
```
❌ **Problem**: Shows extracted content, not source!

### After (Good - Shows URL):

```json
{
  "sources": [
    {
      "index": 1,
      "source": "https://www.cms.gov/medicare/coverage/part-a",
      "type": "webpage",
      "domain": "www.cms.gov",
      "title": "Medicare Part A Coverage",
      "score": 0.92
    },
    {
      "index": 2,
      "source": "HIH_Onboarding_Guide.pdf",
      "type": "file",
      "page": 12,
      "score": 0.88
    }
  ]
}
```
✅ **Perfect**: Shows source URLs and filenames!

---

## Frontend Display

### Markdown Format:

```markdown
**Sources:**
1. [Medicare Part A Coverage](https://www.cms.gov/medicare/coverage/part-a) - www.cms.gov
2. HIH_Onboarding_Guide.pdf (Page 12)
```

### HTML Format:

```html
<div class="sources">
  <h3>Sources:</h3>
  <ol>
    <li>
      <a href="https://www.cms.gov/medicare/coverage/part-a" target="_blank">
        Medicare Part A Coverage
      </a>
      <span class="domain">(www.cms.gov)</span>
    </li>
    <li>
      <span class="file">HIH_Onboarding_Guide.pdf</span>
      <span class="page">(Page 12)</span>
    </li>
  </ol>
</div>
```

---

## Implementation Checklist

### ✅ For URL Ingestion:

```python
# 1. Use URLProcessor
from ingestion.url_processor import URLProcessor

processor = URLProcessor(allowed_domains=["cms.gov"])
documents = processor.process_url(url, tenant_id="HIH")

# 2. Verify metadata
for doc in documents:
    assert 'url' in doc.metadata
    assert 'source' in doc.metadata
    assert doc.metadata['source'] == url  # Source IS the URL!
```

### ✅ For File Ingestion:

```python
# 1. Load documents
from llama_index.core import SimpleDirectoryReader

documents = SimpleDirectoryReader(
    input_files=[file_path]
).load_data()

# 2. Add metadata
from utils.url_tracker import enrich_file_with_metadata

enrich_file_with_metadata(documents, file_path, tenant_id="HIH")

# 3. Verify
for doc in documents:
    assert 'source' in doc.metadata
    assert 'file_name' in doc.metadata
```

### ✅ For Query Response:

```python
# 1. Get retrieval results
rag_response = query_engine.query(query)

# 2. Format sources
from utils.url_tracker import format_sources_with_urls, deduplicate_sources

sources = format_sources_with_urls(rag_response.source_nodes)
sources = deduplicate_sources(sources)

# 3. Return clean response
return {
    "summary": "...",
    "detailed_response": "...",
    "sources": sources  # URLs only!
}
```

---

## Metadata Priority

When extracting source, the system checks in this order:

1. **`metadata['url']`** - Direct URL (highest priority)
2. **`metadata['source']`** - Source (URL or filename)
3. **`metadata['file_path']`** - File path (extract filename)
4. **`metadata['file_name']`** - Filename directly
5. **Fallback**: `"Document {index}"`

---

## Testing

### Test 1: URL Source

```python
from utils.url_tracker import format_sources_with_urls
from llama_index.core.schema import NodeWithScore, TextNode

# Create test node
node = NodeWithScore(
    node=TextNode(
        text="Medicare covers...",
        metadata={
            'url': 'https://www.cms.gov/medicare',
            'title': 'Medicare Coverage'
        }
    ),
    score=0.92
)

# Format
sources = format_sources_with_urls([node])

# Verify
assert sources[0]['source'] == 'https://www.cms.gov/medicare'
assert sources[0]['type'] == 'webpage'
assert sources[0]['title'] == 'Medicare Coverage'
```

### Test 2: File Source

```python
# Create test node
node = NodeWithScore(
    node=TextNode(
        text="Policy states...",
        metadata={
            'file_name': 'HIH_Policy.pdf',
            'page_number': 5
        }
    ),
    score=0.88
)

# Format
sources = format_sources_with_urls([node])

# Verify
assert sources[0]['source'] == 'HIH_Policy.pdf'
assert sources[0]['type'] == 'file'
assert sources[0]['page'] == 5
```

---

## Common Issues

### Issue 1: Sources show extracted text

**Cause**: Metadata not set during ingestion

**Fix**:
```python
# Always enrich documents with metadata!
enrich_documents_with_urls(documents, url=url)
# OR
enrich_file_with_metadata(documents, file_path=path)
```

### Issue 2: Duplicate sources

**Cause**: Same URL retrieved multiple times

**Fix**:
```python
from utils.url_tracker import deduplicate_sources

sources = deduplicate_sources(sources)
```

### Issue 3: Missing page numbers

**Cause**: PDF reader not extracting page metadata

**Fix**:
```python
# Use SimpleDirectoryReader with metadata
reader = SimpleDirectoryReader(
    input_files=[file_path],
    file_metadata=lambda x: {"file_name": Path(x).name}
)
documents = reader.load_data()
```

---

## Best Practices

1. ✅ **Always set `metadata['source']`** during ingestion
2. ✅ **Use `enrich_documents_with_urls()`** for web content
3. ✅ **Use `enrich_file_with_metadata()`** for files
4. ✅ **Format sources** before returning to user
5. ✅ **Deduplicate sources** to avoid clutter
6. ✅ **Include page numbers** for PDFs
7. ✅ **Test metadata** after ingestion

---

## Summary

**Key Functions:**

```python
# Ingestion
from utils.url_tracker import (
    enrich_documents_with_urls,
    enrich_file_with_metadata
)

# Response formatting
from utils.url_tracker import (
    format_sources_with_urls,
    deduplicate_sources,
    format_source_citation
)

# URL processing
from ingestion.url_processor import URLProcessor
```

**Result**: Users see **clean URLs and filenames** as sources, not walls of extracted text! ✅

---

## Files Created

1. **`utils/url_tracker.py`** - URL tracking and source formatting
2. **`ingestion/url_processor.py`** - URL processing with metadata
3. **`docs/SOURCE_ATTRIBUTION.md`** - This guide

**Ready to use!** Import and integrate into your RAG agent.
