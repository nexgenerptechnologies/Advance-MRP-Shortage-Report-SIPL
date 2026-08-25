import os

def search_in_dir(dir_path, search_term):
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith(('.js', '.py', '.html', '.json', '.txt')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if search_term.lower() in content.lower():
                            print(f"Found in: {file_path}")
                except Exception:
                    pass

print("Searching for 'Fetch Project BOM Items'...")
search_in_dir(r'c:\Users\DELL\Documents\New project\Advance-MRP-Shortage-Report-SIPL', 'Fetch Project BOM Items')
print("Searching for 'Items with Inventory Shortage'...")
search_in_dir(r'c:\Users\DELL\Documents\New project\Advance-MRP-Shortage-Report-SIPL', 'Items with Inventory Shortage')
print("Searching for 'Add Shortage to Purchase Order'...")
search_in_dir(r'c:\Users\DELL\Documents\New project\Advance-MRP-Shortage-Report-SIPL', 'Add Shortage to Purchase Order')
