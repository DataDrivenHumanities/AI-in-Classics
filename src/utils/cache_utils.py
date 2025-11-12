import os
import json
import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path

class FileCache:
    """
    Simple file-based caching system for storing processed data.
    """
    
    def __init__(self, cache_dir=None, expire_days=7):
        """
        Initialize the cache.
        
        Parameters:
            cache_dir (str): Directory to store cache files. If None, uses default 'cache' directory.
            expire_days (int): Number of days before cache entries expire
        """
        if cache_dir is None:
            # Create cache in project root
            project_root = Path(__file__).parent.parent.parent
            cache_dir = project_root / 'cache'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.index_file = self.cache_dir / 'cache_index.json'
        self.expire_days = expire_days
        self._load_index()
    
    def _load_index(self):
        """Load the cache index file or create it if it doesn't exist."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.index = {}
        else:
            self.index = {}
    
    def _save_index(self):
        """Save the cache index to disk."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f)
    
    def _generate_key(self, key_data):
        """Generate a unique cache key from input data."""
        if isinstance(key_data, str):
            key_str = key_data
        else:
            key_str = str(key_data)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def has(self, key_data):
        """Check if an item exists in the cache and is not expired."""
        key = self._generate_key(key_data)
        
        if key not in self.index:
            return False
        
        # Check if expired
        timestamp = datetime.fromisoformat(self.index[key]['timestamp'])
        expiration = timestamp + timedelta(days=self.expire_days)
        
        if datetime.now() > expiration:
            return False
            
        return True
    
    def get(self, key_data, default=None):
        """
        Retrieve an item from the cache.
        
        Returns default value if the item doesn't exist or is expired.
        """
        key = self._generate_key(key_data)
        
        if not self.has(key_data):
            return default
            
        cache_file = self.cache_dir / f"{key}.pkl"
        
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except (IOError, pickle.PickleError):
            return default
    
    def set(self, key_data, value):
        """Store an item in the cache."""
        key = self._generate_key(key_data)
        cache_file = self.cache_dir / f"{key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(value, f)
                
            self.index[key] = {
                'timestamp': datetime.now().isoformat(),
                'key_data': str(key_data)
            }
            
            self._save_index()
            return True
        except (IOError, pickle.PickleError):
            return False
    
    def clear_expired(self):
        """Remove expired items from cache."""
        expired_keys = []
        
        for key, data in self.index.items():
            timestamp = datetime.fromisoformat(data['timestamp'])
            expiration = timestamp + timedelta(days=self.expire_days)
            
            if datetime.now() > expiration:
                expired_keys.append(key)
        
        for key in expired_keys:
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                cache_file.unlink()
            del self.index[key]
        
        if expired_keys:
            self._save_index()
    
    def clear_all(self):
        """Clear all items from the cache."""
        for key in self.index:
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                cache_file.unlink()
        
        self.index = {}
        self._save_index()

# Create a default cache instance
cache = FileCache()
