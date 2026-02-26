import os
import psycopg

# It is best practice to use environment variables instead of pasting passwords in code
DB_URL = os.getenv("DATABASE_URL")

def test_connection():
    print("🚀 Starting Database Smoke Test...\n")
    
    if not DB_URL:
        print("❌ Error: DATABASE_URL environment variable is not set.")
        print("   Please set it in your terminal before running this script.")
        return

    print("🔄 Attempting to connect to the cloud database...")
    
    try:
        # We connect to the DB using the URL
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # Execute a completely harmless query that touches NO tables
                cur.execute("SELECT version(), current_timestamp;")
                result = cur.fetchone()
                
                db_version = result[0]
                db_time = result[1]
                
                print("\n✅ CONNECTION SUCCESSFUL!")
                print("==================================================")
                print(f"🏛️ Database Version: {db_version}")
                print(f"🕒 Database Time:    {db_time}")
                print("==================================================")
                print("\nYour connection string is valid and the firewall is open!")
                
    except psycopg.OperationalError as e:
        print("\n❌ CONNECTION FAILED (Network/Auth Issue):")
        print(f"   {e}")
        print("\n💡 Tip: Check if your cloud provider requires you to 'Allow IP' or open the firewall for your current computer.")
    except Exception as e:
        print("\n❌ AN UNEXPECTED ERROR OCCURRED:")
        print(f"   {e}")

if __name__ == "__main__":
    test_connection()