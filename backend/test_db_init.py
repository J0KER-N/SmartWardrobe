"""Test script to verify database initialization."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("Testing database initialization...")
    
    # Test imports
    print("1. Testing imports...")
    from app.config import get_settings
    from app.database import engine
    from app.models import Base, User, Garment, TryOnRecord, TryOnStatus
    
    print("   ✓ Imports successful")
    
    # Test settings
    print("2. Testing settings...")
    settings = get_settings()
    print(f"   ✓ Settings loaded: {settings.database_url}")
    
    # Test database connection
    print("3. Testing database connection...")
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("   ✓ Database connection successful")
    
    # Test table creation
    print("4. Testing table creation...")
    Base.metadata.create_all(bind=engine)
    print("   ✓ Tables created successfully")
    
    # Test TryOnStatus enum
    print("5. Testing TryOnStatus enum...")
    assert TryOnStatus.pending.value == "pending"
    assert TryOnStatus.completed.value == "completed"
    assert TryOnStatus.failed.value == "failed"
    print("   ✓ TryOnStatus enum working correctly")
    
    print("\n✅ All tests passed! Database initialization is working correctly.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

