"""
Telegram ChromaDB Query Script
Query indexed Telegram messages using RAG with Claude API
"""

import argparse
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import chromadb
import anthropic
import sys


class TelegramQuerier:
    def __init__(self, db_path: str, collection_name: str, anthropic_api_key: str = None):
        """Initialize the querier with ChromaDB and Claude"""
        print(f"Loading ChromaDB from {db_path}...")
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
            count = self.collection.count()
            print(f"✓ Loaded collection '{collection_name}' with {count} messages")
        except Exception as e:
            print(f"✗ Error loading collection '{collection_name}': {e}")
            print("\nAvailable collections:")
            for col in self.chroma_client.list_collections():
                print(f"  - {col.name} ({col.count()} items)")
            sys.exit(1)
        
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.anthropic_client = None
        if anthropic_api_key:
            print("Initializing Claude API...")
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
    
    def search(self, query: str, n_results: int = 10) -> Dict:
        """Search for relevant messages"""
        print(f"\nSearching for: '{query}'")
        query_embedding = self.embedding_model.encode([query])
        
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results
        )
        
        return results
    
    def display_results(self, results: Dict):
        """Display search results in a readable format"""
        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        
        if not documents:
            print("No results found.")
            return
        
        print(f"\nFound {len(documents)} relevant messages:\n")
        print("=" * 80)
        
        for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
            date = meta.get('date', 'Unknown')[:19]  # Format datetime
            sender = meta.get('sender', 'Unknown')
            
            print(f"\n{i}. [{date}] {sender}")
            print(f"   {doc}")
            print("-" * 80)
    
    def ask_claude(self, question: str, n_results: int = 15) -> str:
        """Ask a question using Claude with RAG"""
        if not self.anthropic_client:
            return "Error: Anthropic API key not provided. Use --api-key or set ANTHROPIC_API_KEY"
        
        # Search for relevant messages
        results = self.search(question, n_results)
        
        documents = results.get('documents', [[]])[0]
        if not documents:
            return "No relevant messages found in the chat history."
        
        # Build context
        context = "\n\n".join(documents)
        
        print("\nAsking Claude...")
        
        # Query Claude
        try:
            message = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": f"""You are analyzing Telegram chat history. Based on the following messages, answer the user's question accurately and concisely.

Chat Messages:
{context}

Question: {question}

Provide a clear answer based on the chat history. If the information isn't in the messages, say so. Include relevant dates and senders when appropriate. Answer in the same language as the question."""
                }]
            )
            
            return message.content[0].text
        except Exception as e:
            return f"Error querying Claude: {str(e)}"
    
    def interactive_mode(self):
        """Interactive query mode"""
        print("\n" + "=" * 80)
        print("Interactive Mode - Type 'exit' or 'quit' to stop")
        print("=" * 80 + "\n")
        
        while True:
            try:
                question = input("\n🔍 Your question: ").strip()
                
                if question.lower() in ['exit', 'quit', 'q']:
                    print("Goodbye!")
                    break
                
                if not question:
                    continue
                
                if self.anthropic_client:
                    answer = self.ask_claude(question)
                    print("\n💬 Claude's Answer:")
                    print("-" * 80)
                    print(answer)
                    print("-" * 80)
                else:
                    # Just show search results
                    results = self.search(question, n_results=5)
                    self.display_results(results)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def get_stats(self):
        """Get collection statistics"""
        count = self.collection.count()
        
        # Get sample of metadata to infer date range
        sample = self.collection.get(limit=100)
        
        dates = []
        senders = set()
        
        for meta in sample.get('metadatas', []):
            if meta.get('date'):
                dates.append(meta['date'])
            if meta.get('sender'):
                senders.add(meta['sender'])
        
        stats = {
            'total_messages': count,
            'unique_senders': len(senders),
            'sample_dates': sorted(dates)[:5] if dates else []
        }
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Query indexed Telegram chat history"
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='./chroma_db',
        help='ChromaDB directory path (default: ./chroma_db)'
    )
    parser.add_argument(
        '--collection',
        type=str,
        default='telegram_chat',
        help='ChromaDB collection name (default: telegram_chat)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)'
    )
    parser.add_argument(
        '--query',
        type=str,
        default=None,
        help='Single query to run (non-interactive)'
    )
    parser.add_argument(
        '--search-only',
        action='store_true',
        help='Only search, do not use Claude (shows raw results)'
    )
    parser.add_argument(
        '--n-results',
        type=int,
        default=15,
        help='Number of messages to retrieve (default: 15)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show collection statistics and exit'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    
    args = parser.parse_args()
    
    # Get API key from env if not provided
    api_key = args.api_key
    if not api_key:
        import os
        api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    # Don't require API key for search-only or stats mode
    if args.search_only or args.stats:
        api_key = None
    
    # Initialize querier
    querier = TelegramQuerier(
        db_path=args.db_path,
        collection_name=args.collection,
        anthropic_api_key=api_key
    )
    
    # Show stats if requested
    if args.stats:
        stats = querier.get_stats()
        print("\n" + "=" * 80)
        print("Collection Statistics")
        print("=" * 80)
        print(f"Total messages: {stats['total_messages']}")
        print(f"Unique senders: {stats['unique_senders']}")
        if stats['sample_dates']:
            print(f"Date range (sample): {stats['sample_dates'][0][:10]} to {stats['sample_dates'][-1][:10]}")
        print("=" * 80 + "\n")
        return
    
    # Single query mode
    if args.query:
        if args.search_only:
            results = querier.search(args.query, n_results=args.n_results)
            querier.display_results(results)
        else:
            if not api_key:
                print("Error: Anthropic API key required. Use --api-key or set ANTHROPIC_API_KEY")
                sys.exit(1)
            answer = querier.ask_claude(args.query, n_results=args.n_results)
            print("\n💬 Answer:")
            print("=" * 80)
            print(answer)
            print("=" * 80)
    
    # Interactive mode
    elif args.interactive:
        querier.interactive_mode()
    
    # Default: show help
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python query.py --stats")
        print("  python query.py --query 'What was discussed about helmets?' --api-key sk-...")
        print("  python query.py --query 'helmet' --search-only")
        print("  python query.py --interactive --api-key sk-...")


if __name__ == "__main__":
    main()