import os
import time
import re
from pathlib import Path

def read_token_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

def parse_tokens(content):
    tokens = []
    # Split content into individual token entries
    token_entries = content.strip().split('\n\n')
    
    for entry in token_entries:
        if not entry.strip():
            continue
        
        # Extract mint and mcap using regex
        mint_match = re.search(r'"mint":\s*"([^"]+)"', entry)
        mcap_match = re.search(r'"mcap":\s*"\$([0-9,]+\.[0-9]+)"', entry)
        
        if mint_match and mcap_match:
            mcap_str = mcap_match.group(1).replace(',', '')
            mcap = float(mcap_str)
            tokens.append((entry, mcap))  # Store full entry instead of just mint
    
    return tokens

def monitor_tokens():
    base_dir = r"C:\Users\gdllh\OneDrive\Desktop\pumpfun succsesfull bot\safety_pass1\tokens_mc"
    output_file = r"C:\Users\gdllh\OneDrive\Desktop\pumpfun succsesfull bot\safety_pass1\mc_pass\mc_pass.txt"
    tracked_mints = set()
    
    # Load previously tracked mints
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract mints from the full entries
            tracked_mints = set(re.findall(r'"mint":\s*"([^"]+)"', content))
    
    while True:
        for i in range(1, 11):
            file_name = f"tokens_mc{i if i > 1 else ''}.txt"
            file_path = os.path.join(base_dir, file_name)
            
            try:
                content = read_token_file(file_path)
                tokens = parse_tokens(content)
                
                for entry, mcap in tokens:
                    mint_match = re.search(r'"mint":\s*"([^"]+)"', entry)
                    mint = mint_match.group(1)
                    
                    if mcap > 20000 and mint not in tracked_mints:
                        # Add full token entry to tracking file
                        with open(output_file, 'a', encoding='utf-8') as f:
                            f.write(f"{entry}\n\n")
                        tracked_mints.add(mint)
                        print(f"Added new token with mint {mint} (MCap: ${mcap:,.2f})")
                        
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
                
        time.sleep(1)  # Wait 1 second before next check

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    output_dir = Path(r"C:\Users\gdllh\OneDrive\Desktop\pumpfun succsesfull bot\safety_pass1\mc_pass")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    monitor_tokens()