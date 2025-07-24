"""
Migrate from single-fund database to multi-fund database
"""

from database_v2 import MultiFundDatabase
import os

def migrate():
    """Migrate existing VTSAX data to new multi-fund database"""
    old_db = "vtsax_holdings.db"
    new_db = "index_funds.db"
    
    if not os.path.exists(old_db):
        print(f"Old database '{old_db}' not found. Nothing to migrate.")
        return
    
    if os.path.exists(new_db):
        response = input(f"New database '{new_db}' already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
        os.remove(new_db)
    
    print(f"Migrating from '{old_db}' to '{new_db}'...")
    
    # Create new database and migrate
    db = MultiFundDatabase(new_db)
    db.migrate_from_old_db(old_db)
    
    # Verify migration
    stats = db.get_stats()
    print(f"\nMigration complete!")
    print(f"- Funds: {stats['total_funds']}")
    print(f"- Total unique stocks: {stats['unique_stocks']}")
    
    for fund_stat in stats['fund_stats']:
        print(f"- {fund_stat[0]}: {fund_stat[2]} holdings")
    
    print(f"\nOld database '{old_db}' has been preserved.")
    print(f"New database '{new_db}' is ready for use.")

if __name__ == '__main__':
    migrate()