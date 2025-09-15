import sqlite3

def print_table(table_name, db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    print(f"\nContents of table: {table_name}")
    for row in c.execute(f'SELECT * FROM {table_name}'):
        print(row)
    conn.close()

if __name__ == "__main__":
    print_table('search_results')
    print_table('queries')
    print_table('articles')
    print_table('scraped_articles')
