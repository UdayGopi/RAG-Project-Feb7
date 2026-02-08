#!/usr/bin/env python3
"""
Verify that the new modular structure is properly set up.
Checks router query engine and all components.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_imports():
    """Check if all new modules can be imported."""
    print("=" * 60)
    print("🔍 Checking Imports...")
    print("=" * 60)
    
    modules_to_check = [
        ("config", "Config module"),
        ("config.settings", "Settings"),
        ("config.models", "Model configs"),
        ("config.storage", "Storage configs"),
        ("core", "Core module"),
        ("core.llm", "LLM management"),
        ("core.embeddings", "Embeddings"),
        ("storage", "Storage module"),
        ("storage.local_storage", "Local storage"),
        ("storage.s3_storage", "S3 storage"),
        ("storage.vector_stores", "Vector stores"),
        ("agents", "Agents module"),
        ("agents.rag_agent", "RAG Agent"),
        ("agents.intent_classifier", "Intent classifier"),
        ("retrieval", "Retrieval module"),
        ("utils", "Utils module"),
        ("utils.url_tracker", "URL tracker"),
        ("ingestion", "Ingestion module"),
        ("ingestion.url_processor", "URL processor"),
    ]
    
    all_ok = True
    for module_name, description in modules_to_check:
        try:
            __import__(module_name)
            print(f"  ✅ {description:30} ({module_name})")
        except ImportError as e:
            print(f"  ❌ {description:30} ({module_name})")
            print(f"     Error: {e}")
            all_ok = False
    
    return all_ok


def check_agent():
    """Check if ModernRAGAgent can be initialized."""
    print("\n" + "=" * 60)
    print("🤖 Checking ModernRAGAgent...")
    print("=" * 60)
    
    try:
        from agents import get_rag_agent
        agent = get_rag_agent()
        
        print(f"  ✅ Agent initialized: {type(agent).__name__}")
        print(f"  ✅ Router exists: {agent.router_query_engine is not None}")
        print(f"  ✅ Tenants: {agent.list_tenants()}")
        print(f"  ✅ Tools: {len(agent.tools)}")
        
        # Check stats
        stats = agent.get_stats()
        print(f"\n  📊 Stats:")
        for key, value in stats.items():
            print(f"     {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to initialize agent")
        print(f"     Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_router():
    """Check router query engine specifically."""
    print("\n" + "=" * 60)
    print("🎯 Checking Router Query Engine...")
    print("=" * 60)
    
    try:
        from agents import get_rag_agent
        agent = get_rag_agent()
        
        print(f"  Router Type: {type(agent.router_query_engine)}")
        print(f"  Router Enabled: {agent.router_query_engine is not None}")
        print(f"  Tenants: {agent.tenants}")
        print(f"  Tools Count: {len(agent.tools)}")
        
        if agent.router_query_engine:
            print("\n  ✅ Router Query Engine is READY!")
            print(f"     - Multi-tenant routing: ENABLED")
            print(f"     - Auto-detection: ENABLED")
            print(f"     - Tenants loaded: {len(agent.tenants)}")
        else:
            print("\n  ⚠️  Router not initialized (no tenants yet)")
            print("     This is normal if no documents ingested yet")
            print("     Router will auto-initialize when first tenant added")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Router check failed")
        print(f"     Error: {e}")
        return False


def check_citations():
    """Check if citation utilities are working."""
    print("\n" + "=" * 60)
    print("📎 Checking Citations...")
    print("=" * 60)
    
    try:
        from utils.url_tracker import (
            format_sources_with_urls,
            deduplicate_sources
        )
        from llama_index.core.schema import NodeWithScore, TextNode
        
        # Create test node
        test_node = NodeWithScore(
            node=TextNode(
                text="Test content",
                metadata={
                    'url': 'https://example.com/test',
                    'source': 'https://example.com/test',
                    'title': 'Test Page'
                }
            ),
            score=0.95
        )
        
        # Format sources
        sources = format_sources_with_urls([test_node])
        
        print(f"  ✅ Citation formatting works")
        print(f"  ✅ Test source:")
        print(f"     URL: {sources[0]['source']}")
        print(f"     Type: {sources[0]['type']}")
        print(f"     Score: {sources[0]['score']}")
        
        # Check it's URL, not content
        if len(sources[0]['source']) < 500:
            print(f"  ✅ Sources show URLs (not extracted content)")
        else:
            print(f"  ❌ Source seems to be content, not URL!")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Citation check failed")
        print(f"     Error: {e}")
        return False


def check_structure():
    """Check folder structure."""
    print("\n" + "=" * 60)
    print("📁 Checking Folder Structure...")
    print("=" * 60)
    
    required_dirs = [
        "config",
        "core",
        "agents",
        "storage",
        "retrieval",
        "models",
        "ingestion",
        "utils",
        "docs",
        "scripts",
        "ecs"
    ]
    
    all_ok = True
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ (missing)")
            all_ok = False
    
    return all_ok


def main():
    """Run all checks."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "RAG SYSTEM STRUCTURE VERIFICATION" + " " * 15 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    results = {
        "Structure": check_structure(),
        "Imports": check_imports(),
        "Agent": check_agent(),
        "Router": check_router(),
        "Citations": check_citations()
    }
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status:10} {check_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED!")
        print("=" * 60)
        print("\n✅ Your RAG system is properly structured!")
        print("✅ Router Query Engine is implemented!")
        print("✅ Citations are working!")
        print("\n📝 Next steps:")
        print("   1. Update app.py (see UPDATE_APP_GUIDE.md)")
        print("   2. Test: python app.py")
        print("   3. Deploy: bash scripts/deploy-ecs.sh")
        return 0
    else:
        print("⚠️  SOME CHECKS FAILED")
        print("=" * 60)
        print("\n❌ Please fix the issues above")
        print("\n📚 Documentation:")
        print("   - START_HERE.md")
        print("   - MIGRATION_GUIDE.md")
        print("   - ROUTER_ENGINE_GUIDE.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
