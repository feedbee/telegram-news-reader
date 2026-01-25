"""
Telegram JSON to ChromaDB Indexer
Indexes Telegram chat history from JSON export into ChromaDB for semantic search
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


class TelegramIndexer:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize the indexer with ChromaDB and embedding model"""
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        print(f"Initializing ChromaDB (persist to: {persist_directory})...")
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.collection = None
        self.persist_directory = persist_directory
        
    def load_json(self, json_path: str) -> Dict:
        """Load Telegram JSON export"""
        print(f"Loading JSON from {json_path}...")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded {len(data.get('messages', []))} messages")
        return data
    
    def extract_messages(self, data: Dict) -> List[Dict]:
        """Extract and format messages from JSON"""
        messages = []
        chat_info = data.get('chat', {})
        chat_title = chat_info.get('title', 'Unknown')
        
        for msg in data.get('messages', []):
            # Skip messages without text
            if not msg.get('text'):
                continue
            
            # Extract sender information
            sender_name = "Unknown"
            sender_username = None
            from_id = msg.get('from_id', {})
            
            if from_id.get('type') == 'PeerUser':
                user = from_id.get('user', {})
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                sender_username = user.get('username')
                
                sender_name = first_name
                if last_name:
                    sender_name += f" {last_name}"
                if sender_username:
                    sender_name += f" (@{sender_username})"
            
            # Create message entry
            messages.append({
                'id': msg['id'],
                'date': msg['date'],
                'sender': sender_name,
                'sender_id': from_id.get('id'),
                'text': msg['text'],
                'chat_title': chat_title,
                'reactions': msg.get('reactions', {}).get('results', []) if msg.get('reactions') else []
            })
        
        print(f"Extracted {len(messages)} text messages")
        return messages
    
    def create_collection(self, collection_name: str, reset: bool = True):
        """Create or get ChromaDB collection"""
        if reset:
            try:
                self.chroma_client.delete_collection(collection_name)
                print(f"Deleted existing collection: {collection_name}")
            except:
                pass
        
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Telegram chat messages"}
        )
        print(f"Created collection: {collection_name}")
    
    def index_messages(self, messages: List[Dict], batch_size: int = 100):
        """Index messages into ChromaDB with embeddings"""
        if not messages:
            print("No messages to index")
            return 0
        
        print(f"Preparing {len(messages)} messages for indexing...")
        
        # Prepare data for indexing
        texts = []
        metadatas = []
        ids = []
        
        for msg in messages:
            # Create rich text with context (this is what gets embedded)
            date_str = msg['date'][:10]  # Extract date only
            text_with_context = f"[{date_str}] {msg['sender']}: {msg['text']}"
            
            texts.append(text_with_context)
            metadatas.append({
                'message_id': str(msg['id']),
                'date': msg['date'],
                'sender': msg['sender'],
                'chat_title': msg['chat_title'],
                'has_reactions': len(msg['reactions']) > 0
            })
            ids.append(f"msg_{msg['id']}")
        
        print("Generating embeddings...")
        embeddings = self.embedding_model.encode(
            texts, 
            show_progress_bar=True,
            batch_size=32
        )
        
        print(f"Indexing messages in batches of {batch_size}...")
        total_indexed = 0
        
        for i in range(0, len(texts), batch_size):
            batch_end = min(i + batch_size, len(texts))
            
            self.collection.add(
                embeddings=embeddings[i:batch_end].tolist(),
                documents=texts[i:batch_end],
                metadatas=metadatas[i:batch_end],
                ids=ids[i:batch_end]
            )
            
            total_indexed += (batch_end - i)
            print(f"Indexed {total_indexed}/{len(texts)} messages")
        
        return total_indexed
    
    def get_collection_stats(self):
        """Get statistics about the indexed collection"""
        if not self.collection:
            return None
        
        count = self.collection.count()
        return {
            'total_messages': count,
            'collection_name': self.collection.name
        }
    
    def test_search(self, query: str, n_results: int = 5):
        """Test search functionality"""
        if not self.collection:
            print("No collection available")
            return
        
        print(f"\nTesting search with query: '{query}'")
        query_embedding = self.embedding_model.encode([query])
        
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results
        )
        
        print(f"\nTop {n_results} results:")
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
            print(f"\n{i}. {doc}")
            print(f"   Date: {metadata['date'][:10]}, Sender: {metadata['sender']}")


def main():
    parser = argparse.ArgumentParser(
        description="Index Telegram JSON chat history into ChromaDB"
    )
    parser.add_argument(
        'json_file',
        type=str,
        help='Path to Telegram JSON export file'
    )
    parser.add_argument(
        '--collection',
        type=str,
        default='telegram_chat',
        help='ChromaDB collection name (default: telegram_chat)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='./chroma_db',
        help='ChromaDB persist directory (default: ./chroma_db)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for indexing (default: 100)'
    )
    parser.add_argument(
        '--test-query',
        type=str,
        default=None,
        help='Test query to run after indexing'
    )
    parser.add_argument(
        '--no-reset',
        action='store_true',
        help='Do not reset existing collection (append mode)'
    )
    
    args = parser.parse_args()
    
    # Validate JSON file exists
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Error: JSON file not found: {args.json_file}")
        return
    
    # Initialize indexer
    indexer = TelegramIndexer(persist_directory=args.db_path)
    
    # Load and process JSON
    data = indexer.load_json(args.json_file)
    messages = indexer.extract_messages(data)
    
    if not messages:
        print("No messages to index. Exiting.")
        return
    
    # Create collection
    indexer.create_collection(args.collection, reset=not args.no_reset)
    
    # Index messages
    count = indexer.index_messages(messages, batch_size=args.batch_size)
    
    # Force persist (for older ChromaDB versions)
    print("Persisting database to disk...")
    try:
        # ChromaDB 0.4.x needs explicit persist
        if hasattr(indexer.chroma_client, 'persist'):
            indexer.chroma_client.persist()
    except Exception as e:
        print(f"Note: persist() not available (ChromaDB 0.5+): {e}")
    
    # Show stats
    stats = indexer.get_collection_stats()
    print(f"\n{'='*50}")
    print(f"Indexing Complete!")
    print(f"{'='*50}")
    print(f"Collection: {stats['collection_name']}")
    print(f"Total messages indexed: {stats['total_messages']}")
    print(f"Database location: {args.db_path}")
    print(f"{'='*50}\n")
    
    # Test search if requested
    if args.test_query:
        indexer.test_search(args.test_query)


if __name__ == "__main__":
    main()