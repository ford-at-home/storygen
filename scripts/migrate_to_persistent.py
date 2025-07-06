#!/usr/bin/env python3
"""
Migration script to transition from in-memory to persistent data storage
Run this to migrate existing sessions and set up the persistent infrastructure
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from data import (
    init_data_layer, run_migration, run_ingestion_pipeline,
    data_manager, create_backup
)
from data.migration import MigrationConfig
from data.dynamodb_schema import DynamoDBManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('migration')


async def main():
    """Main migration process"""
    print("=" * 60)
    print("Richmond StoryGen Data Migration Tool")
    print("=" * 60)
    print()
    
    # Step 1: Check environment
    print("1. Checking environment...")
    
    required_env_vars = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY", 
        "AWS_REGION",
        "PINECONE_API_KEY"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nPlease set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}=<your-value>")
        return
    
    print("✅ Environment variables configured")
    
    # Step 2: Initialize data layer
    print("\n2. Initializing data layer...")
    
    try:
        await init_data_layer(
            create_tables=True,
            warm_cache=False,  # Skip cache warming for migration
            enable_backups=False  # Enable after migration
        )
        print("✅ Data layer initialized")
    except Exception as e:
        print(f"❌ Failed to initialize data layer: {e}")
        return
    
    # Step 3: Create pre-migration backup
    print("\n3. Creating pre-migration backup...")
    
    try:
        backup_result = await create_backup("pre_migration")
        print(f"✅ Backup created: {backup_result['backup_id']}")
    except Exception as e:
        print(f"⚠️  Backup failed (continuing anyway): {e}")
    
    # Step 4: Run data migration
    print("\n4. Running data migration...")
    
    # Ask for confirmation
    response = input("\nDo you want to run a dry run first? (y/n): ").lower()
    dry_run = response == 'y'
    
    config = MigrationConfig(
        source_type="in_memory",
        dry_run=dry_run,
        create_backup=True,
        validate_data=True,
        batch_size=50,
        enable_rollback=True
    )
    
    try:
        result = await run_migration(config)
        
        print(f"\n{'DRY RUN' if dry_run else 'MIGRATION'} RESULTS:")
        print(f"  - Items processed: {result['items_processed']}")
        print(f"  - Items migrated: {result['items_migrated']}")
        print(f"  - Items failed: {result['items_failed']}")
        
        if result.get('results'):
            for entity_type, stats in result['results'].items():
                if isinstance(stats, dict):
                    print(f"\n  {entity_type}:")
                    print(f"    - Total: {stats.get('total', 0)}")
                    print(f"    - Migrated: {stats.get('migrated', 0)}")
                    print(f"    - Failed: {stats.get('failed', 0)}")
        
        if dry_run and result['items_failed'] == 0:
            response = input("\nDry run successful. Run actual migration? (y/n): ").lower()
            if response == 'y':
                config.dry_run = False
                result = await run_migration(config)
                print("\n✅ Migration completed!")
        elif not dry_run:
            print("\n✅ Migration completed!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return
    
    # Step 5: Ingest Richmond content
    print("\n5. Ingesting Richmond content...")
    
    data_dir = Path("data")
    if data_dir.exists() and list(data_dir.glob("*.md")):
        response = input("\nFound Richmond content files. Ingest them now? (y/n): ").lower()
        if response == 'y':
            try:
                pipeline_result = await run_ingestion_pipeline(str(data_dir))
                print(f"\n✅ Content ingestion completed:")
                print(f"  - Files processed: {pipeline_result['stats']['files_processed']}")
                print(f"  - Chunks created: {pipeline_result['stats']['chunks_created']}")
                print(f"  - Vectors indexed: {pipeline_result['stats']['vectors_indexed']}")
            except Exception as e:
                print(f"❌ Content ingestion failed: {e}")
    else:
        print("⚠️  No Richmond content files found in data/ directory")
    
    # Step 6: Verify setup
    print("\n6. Verifying setup...")
    
    health = data_manager.get_health_status()
    
    print("\nSystem Health:")
    for component, status in health['components'].items():
        icon = "✅" if status == "healthy" else "❌"
        print(f"  {icon} {component}: {status}")
    
    # Step 7: Next steps
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE!")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Update your application to use persistent storage:")
    print("   - Import from session_manager_persistent instead of session_manager")
    print("   - Use data layer functions for all data operations")
    print("\n2. Enable automated backups:")
    print("   - Set enable_backups=True in init_data_layer()")
    print("\n3. Monitor performance:")
    print("   - Check analytics dashboard")
    print("   - Review cache hit rates")
    print("\n4. Test thoroughly before deploying to production")


if __name__ == "__main__":
    asyncio.run(main())