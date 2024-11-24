import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import time

# Update paths
MC_PASS_FILE = r"C:\Users\gdllh\OneDrive\Desktop\pumpfun succsesfull bot\safety_pass1\mc_pass\mc_pass.txt"
HOLDERS_OUTPUT = r"C:\Users\gdllh\OneDrive\Desktop\pumpfun succsesfull bot\safety_pass1\holders\holders.txt"

# Known PumpFun related addresses
PUMPFUN_ADDRESSES = {
    "PUMPFXQGiZkxn6HSEiUyE5WSRe1T4yFR8hxThryRNf6",  # PumpFun program
    "BXhAKUxkGvFbAarA3K1SUYnqXRhEBC1bhUaCaxvzgyJ8",  # Common bonding curve
}

class SolanaTokenScanner:
    def __init__(self):
        self.rpc_url = "https://side-nameless-moon.solana-mainnet.quiknode.pro/f836dcc1ff078ba27a46356e26a64accbfc22a08/"
        self.session: Optional[aiohttp.ClientSession] = None
        self.processed_tokens = set()
        self.pump_addresses = set()
        self.known_tokens = {}  # Track tokens we've seen
        self.rate_limit = 40  # requests per second
        self.request_count = 0
        self.last_request_time = time.time()
        self.last_processed_index = 0  # Track where we left off
        self.retry_delay = 0.1  # Delay between retries in seconds

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def make_rpc_request(self, request_data: dict) -> dict:
        max_retries = 50  # Increased from 3 to 50 retries
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Rate limiting logic
                current_time = time.time()
                if current_time - self.last_request_time < 1:
                    self.request_count += 1
                    if self.request_count >= self.rate_limit:
                        wait_time = 1 - (current_time - self.last_request_time)
                        if wait_time > 0:
                            print(f"Rate limit reached, waiting {wait_time:.2f} seconds...")
                            await asyncio.sleep(wait_time)
                        self.request_count = 0
                        self.last_request_time = time.time()
                else:
                    self.request_count = 1
                    self.last_request_time = current_time

                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                }
                
                async with self.session.post(self.rpc_url, json=request_data, headers=headers, timeout=30) as response:
                    if response.status == 429:  # Too Many Requests
                        retry_count += 1
                        print(f"Rate limit exceeded (429). Retry {retry_count}/{max_retries} after {self.retry_delay}s")
                        await asyncio.sleep(self.retry_delay)
                        continue
                    elif response.status != 200:
                        print(f"HTTP Error {response.status} from QuickNode")
                        retry_count += 1
                        await asyncio.sleep(self.retry_delay)
                        continue
                        
                    result = await response.json()
                    if "error" in result:
                        print(f"RPC Error from QuickNode: {result['error']}")
                        retry_count += 1
                        await asyncio.sleep(self.retry_delay)
                        continue
                        
                    return result
                    
            except Exception as e:
                print(f"Error with QuickNode: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    print(f"Retrying {retry_count}/{max_retries} after {self.retry_delay}s")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {}
        
        print(f"Failed after {max_retries} retries")
        return {}

    async def is_pump_address(self, address: str) -> bool:
        """Check if address is related to PumpFun"""
        if address in PUMPFUN_ADDRESSES:
            return True
        if address in self.pump_addresses:
            return True
        if "pump" in address.lower():
            self.pump_addresses.add(address)
            return True
        return False

    async def get_token_accounts(self, token_address: str) -> List[Dict[str, Any]]:
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getProgramAccounts",
            "params": [
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                {
                    "encoding": "jsonParsed",
                    "filters": [
                        {"dataSize": 165},
                        {"memcmp": {"offset": 0, "bytes": token_address}}
                    ],
                    "commitment": "confirmed"
                }
            ]
        }

        print(f"Fetching token accounts for {token_address} from QuickNode...")
        response = await self.make_rpc_request(request_data)
        
        accounts = response.get("result", [])
        filtered_accounts = []
        
        for account in accounts:
            owner = account["account"]["data"]["parsed"]["info"]["owner"]
            if not await self.is_pump_address(owner):
                filtered_accounts.append(account)
            else:
                print(f"Excluding PumpFun related address: {owner}")
                
        return filtered_accounts

    async def scan_token(self, token_data: dict) -> dict:
        """Modified to return holder data instead of writing to individual files"""
        token_address = token_data.get("mint")
        token_name = token_data.get("name", "N/A")
        
        print(f"\nScanning token: {token_name} ({token_address})")
        
        try:
            accounts = await self.get_token_accounts(token_address)
            if not accounts:
                print(f"No accounts found for {token_name}")
                token_data["holders"] = []
                return token_data
                
            holders = []
            for account in accounts:
                try:
                    parsed_data = account["account"]["data"]["parsed"]["info"]
                    amount = float(parsed_data["tokenAmount"]["uiAmount"])
                    if amount > 0:
                        holders.append({
                            "owner": parsed_data["owner"],
                            "balance": amount,
                            "account": account["pubkey"]
                        })
                except Exception as e:
                    continue

            holders.sort(key=lambda x: x["balance"], reverse=True)
            
            # Calculate total supply and percentages
            total_supply = sum(h["balance"] for h in holders)
            for holder in holders:
                holder["percentage"] = (holder["balance"] / total_supply * 100) if total_supply > 0 else 0

            token_data["holders"] = holders
            token_data["total_supply"] = total_supply
            token_data["holder_count"] = len(holders)
            token_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"Found {len(holders)} holders for {token_name}")
            return token_data
            
        except Exception as e:
            print(f"Error scanning token {token_address}: {str(e)}")
            token_data["holders"] = []
            token_data["error"] = str(e)
            return token_data

async def parse_token_data(content: str) -> List[Dict]:
    """Parse the specific format of token data from the file"""
    tokens = []
    current_token = {}
    
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Remove any trailing commas
        line = line.rstrip(',')
        
        try:
            # Split by first colon and handle the quotes
            key, value = [part.strip().strip('"') for part in line.split(':', 1)]
            
            # Add to current token
            current_token[key] = value
            
            # If we have a market_cap field, this is the end of a token entry
            if key == "market_cap":
                if "mint" in current_token:  # Validate token has required field
                    tokens.append(current_token.copy())
                current_token = {}
                
        except Exception as e:
            print(f"Error parsing line: {line} - {str(e)}")
            continue
            
    # Add the last token if it exists
    if current_token and "mint" in current_token:
        tokens.append(current_token.copy())
        
    return tokens

async def monitor_and_update():
    """Main function to monitor mc_pass.txt and update holders"""
    print("Starting token holder monitoring...")
    print(f"Monitoring file: {MC_PASS_FILE}")
    print(f"Output file: {HOLDERS_OUTPUT}")
    
    scanner = SolanaTokenScanner()
    async with scanner:
        while True:
            try:
                # Read tokens from mc_pass.txt with proper encoding
                if not os.path.exists(MC_PASS_FILE):
                    print(f"Waiting for {MC_PASS_FILE} to be created...")
                    await asyncio.sleep(5)
                    continue

                with open(MC_PASS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                    if not content:
                        print("Empty file, waiting...")
                        await asyncio.sleep(5)
                        continue

                # Parse tokens using the new parser
                tokens = await parse_token_data(content)

                if not tokens:
                    print("No valid tokens found in mc_pass.txt, waiting...")
                    await asyncio.sleep(5)
                    continue

                # Continue from where we left off
                tokens_to_process = tokens[scanner.last_processed_index:]
                if not tokens_to_process:
                    scanner.last_processed_index = 0  # Reset if we've processed all tokens
                    tokens_to_process = tokens

                # Scan each token
                print(f"\nUpdating holders for {len(tokens_to_process)} tokens...")
                updated_tokens = []
                
                for i, token in enumerate(tokens_to_process):
                    if "mint" in token:
                        token_with_holders = await scanner.scan_token(token)
                        if token_with_holders.get("holders"):  # Only add if we got holders
                            updated_tokens.append(token_with_holders)
                        scanner.last_processed_index = (scanner.last_processed_index + 1) % len(tokens)
                    else:
                        print(f"Skipping invalid token data: {token}")

                # Write updated data to holders.txt
                if updated_tokens:
                    try:
                        # Read existing holders first
                        existing_holders = []
                        if os.path.exists(HOLDERS_OUTPUT):
                            with open(HOLDERS_OUTPUT, 'r', encoding='utf-8') as f:
                                for line in f:
                                    try:
                                        holder = json.loads(line.strip())
                                        existing_holders.append(holder)
                                    except:
                                        continue

                        # Update existing holders with new data
                        updated_holder_mints = {t["mint"] for t in updated_tokens}
                        final_holders = [h for h in existing_holders if h.get("mint") not in updated_holder_mints]
                        final_holders.extend(updated_tokens)

                        # Write back all holders
                        with open(HOLDERS_OUTPUT, 'w', encoding='utf-8') as f:
                            for holder in final_holders:
                                json.dump(holder, f, indent=2, ensure_ascii=False)
                                f.write("\n")

                        print(f"\nSuccessfully updated holders at {datetime.now()}")
                        print(f"Processed {len(updated_tokens)} tokens")
                    except Exception as e:
                        print(f"Error writing to holders.txt: {str(e)}")
                else:
                    print("No valid tokens to update")

                # Add a small delay before processing the next batch
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Error in monitoring loop: {str(e)}")
                print("Retrying in 5 seconds...")
                await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_and_update())
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")