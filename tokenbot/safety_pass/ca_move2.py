import json
import time
from pathlib import Path
from datetime import datetime

# Global variables
INPUT_FILE = r"C:\Users\gdllh\OneDrive\Desktop\pumpfun succsesfull bot\safety_pass1\new_ca\tokens_log.txt"
BASE_OUTPUT_PATH = r"C:\Users\gdllh\OneDrive\Desktop\pumpfun succsesfull bot\safety_pass1\tokens_mc\tokens_mc"

def parse_timestamp(timestamp_str):
    try:
        time_part = timestamp_str.replace("Time: ", "").strip()
        return datetime.strptime(time_part, "%Y-%m-%d %H:%M:%S")
    except:
        return None

def reorganize_files():
    """Collect all entries and redistribute them properly across files"""
    all_entries = []
    existing_mcaps = {}
    
    # Collect all valid entries from all files
    for i in range(1, 11):
        file_path = f"{BASE_OUTPUT_PATH}{i if i > 1 else ''}.txt"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    entries = [e for e in content.split('\n\n') if e.strip()]
                    for entry in entries:
                        if entry.strip():
                            try:
                                mint_match = entry.split('"mint": "')[1].split('"')[0]
                                mcap = ""
                                if '"market_cap": "' in entry:
                                    mcap = entry.split('"market_cap": "')[1].split('"')[0]
                                existing_mcaps[mint_match] = mcap
                                timestamp = entry.split('"timestamp": "Time: ')[1].split('"')[0]
                                entry_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                                all_entries.append((entry_time, entry))
                            except:
                                continue
        except:
            continue

    # Sort entries by timestamp (newest first)
    all_entries.sort(key=lambda x: x[0], reverse=True)
    sorted_entries = [entry for _, entry in all_entries]

    # Clear all files
    for i in range(1, 11):
        file_path = f"{BASE_OUTPUT_PATH}{i if i > 1 else ''}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('')

    # Redistribute entries
    current_file = None
    file_number = 1
    token_count = 0
    
    for entry in sorted_entries:
        if token_count % 50 == 0:
            if current_file:
                current_file.close()
            current_output = f"{BASE_OUTPUT_PATH}{file_number if file_number > 1 else ''}.txt"
            current_file = open(current_output, 'a', encoding='utf-8')
            
        current_file.write(entry + '\n\n')
        token_count += 1
        
        if token_count >= 50:
            token_count = 0
            file_number += 1

    if current_file:
        current_file.close()

    return existing_mcaps

def clean_old_entries(file_path, max_age_minutes=20):
    try:
        if not Path(file_path).exists():
            return 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        entries = content.strip().split('\n\n')
        current_time = datetime.now()
        fresh_entries = []
        
        for entry in entries:
            if not entry.strip():
                continue
            
            # Simple timestamp extraction and comparison
            try:
                timestamp_str = entry.split('"timestamp": "Time: ')[1].split('"')[0]
                entry_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                age_minutes = (current_time - entry_time).total_seconds() / 60
                
                if age_minutes <= max_age_minutes:
                    fresh_entries.append(entry)
                else:
                    print(f"Removing old entry (age: {int(age_minutes)} minutes): {entry.split('name')[1].split(',')[0]}")
            except:
                fresh_entries.append(entry)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            if fresh_entries:
                f.write('\n\n'.join(fresh_entries) + '\n\n')
            else:
                f.write('')
        
        return len(fresh_entries)
    except Exception as e:
        print(f"Error cleaning file {file_path}: {str(e)}")
        return 0

def clean_all_files():
    while True:
        try:
            print("\nStarting cleanup cycle...")
            total_removed = 0
            
            # First, remove old tokens
            for i in range(1, 11):
                file_path = f"{BASE_OUTPUT_PATH}{i if i > 1 else ''}.txt"
                before_count = sum(1 for line in open(file_path, 'r', encoding='utf-8') if line.strip())
                fresh_count = clean_old_entries(file_path)
                removed_count = before_count - fresh_count
                if removed_count > 0:
                    total_removed += removed_count
                    print(f"Cleaned {file_path} - Removed {removed_count} old entries")
            
            # Then reorganize if needed
            if total_removed > 0:
                print("Reorganizing files...")
                reorganize_files()
                print(f"Cleanup complete - Removed {total_removed} old entries")
            else:
                print("No old entries found")
                
            time.sleep(10)
        except Exception as e:
            print(f"Error in clean_all_files: {str(e)}")
            time.sleep(10)

def process_tokens():
    processed_entries = set()
    token_count = 0
    file_number = 1
    current_output = f"{BASE_OUTPUT_PATH}.txt"

    # Initial reorganization and market cap collection
    existing_mcaps = reorganize_files()
    
    current_file = open(current_output, 'a', encoding='utf-8')

    # Start the cleaning process in a separate thread
    from threading import Thread
    cleaner_thread = Thread(target=clean_all_files, daemon=True)
    cleaner_thread.start()

    while True:
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            entries = content.split('==================================================')
            
            for entry in entries:
                entry = entry.strip()
                if not entry or '"message"' in entry:
                    continue
                
                entry_hash = hash(entry)
                if entry_hash in processed_entries:
                    continue
                
                timestamp = ""
                if "Time:" in entry:
                    timestamp = entry.split('\n')[0].strip()
                
                json_start = entry.find('{')
                json_end = entry.rfind('}')
                
                if json_start != -1 and json_end != -1:
                    try:
                        json_text = entry[json_start:json_end + 1].strip()
                        data = json.loads(json_text)
                        
                        mcap = existing_mcaps.get(data['mint'], '')
                        
                        output_text = f""""mint": "{data['mint']}",
    "bondingCurveKey": "{data['bondingCurveKey']}",
       "name": "{data['name']}",
         "symbol": "{data['symbol']}",
           "uri": "{data['uri']}",
             "timestamp": "{timestamp}",
               "market_cap": "{mcap}"\n\n"""
                        
                        current_file.write(output_text)
                        current_file.flush()
                        token_count += 1
                        processed_entries.add(entry_hash)
                        
                        if token_count >= 50:
                            current_file.close()
                            file_number += 1
                            if file_number <= 10:
                                token_count = 0
                                current_output = f"{BASE_OUTPUT_PATH}{file_number}.txt"
                                current_file = open(current_output, 'a', encoding='utf-8')
                                print(f"Moving to next file: {current_output}")
                        
                        print(f"Successfully processed entry for {data['name']} (File {file_number}, Token {token_count})")
                            
                    except (json.JSONDecodeError, Exception) as e:
                        print(f"Error processing entry: {str(e)}")
                        continue
            
            time.sleep(1)
                            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            if 'current_file' in locals() and not current_file.closed:
                current_file.close()
            time.sleep(5)
            current_file = open(current_output, 'a', encoding='utf-8')

if __name__ == "__main__":
    process_tokens()