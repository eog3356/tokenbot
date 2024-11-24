from datetime import datetime
import asyncio
import json
import os
import websockets


class PumpPortalMonitor:
    def __init__(self):
        self.uri = "wss://pumpportal.fun/api/data"
        self.known_tokens = set()
        # Define paths for different types of data
        self.base_path = r"C:\Users\gdllh\Desktop\tokenbot\safety_pass\info"
        self.new_ca_path = os.path.join(self.base_path, "new_ca.txt")
        self.detailed_info_path = os.path.join(self.base_path, "detailed_info.txt")
        
        # Create directories if they don't exist
        os.makedirs(self.base_path, exist_ok=True)

    async def log_token_data(self, data, is_detailed=False):
        """Log token data to appropriate file"""
        try:
            file_path = self.detailed_info_path if is_detailed else self.new_ca_path
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                if is_detailed:
                    f.write(json.dumps(data, indent=2))
                else:
                    # Write basic token info
                    token_address = data.get('token', {}).get('address') or data.get('mint')
                    symbol = data.get('token', {}).get('symbol') or data.get('symbol', 'N/A')
                    f.write(f"Token Address: {token_address}\n")
                    f.write(f"Symbol: {symbol}\n")
                
                f.write("\n")
        except Exception as e:
            print(f"Error writing to log file: {str(e)}")

    async def monitor_new_tokens(self):
        """Monitor new token creations"""
        print("🚀 Starting PumpPortal token monitor...")
        print(f"Logging data to: {self.base_path}")
        print("Press Ctrl+C to stop")
        
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    print("Connected to PumpPortal WebSocket")
                    
                    payload = {
                        "method": "subscribeNewToken"
                    }
                    await websocket.send(json.dumps(payload))
                    print("Subscribed to new token events")
                    
                    async for message in websocket:
                        data = json.loads(message)
                        # Log detailed data
                        await self.log_token_data(data, is_detailed=True)
                        
                        print("\n🆕 New Token Event:")
                        print(json.dumps(data, indent=2))
                        
                        if 'token' in data or 'mint' in data:
                            token_address = data.get('token', {}).get('address') or data.get('mint')
                            if token_address and token_address not in self.known_tokens:
                                self.known_tokens.add(token_address)
                                # Log basic token info
                                await self.log_token_data(data, is_detailed=False)
                                
                                print(f"Token Address: {token_address}")
                                print(f"Symbol: {data.get('token', {}).get('symbol') or data.get('symbol', 'N/A')}")
                                print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed, reconnecting...")
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Error: {str(e)}")
                await asyncio.sleep(5)


async def main():
    monitor = PumpPortalMonitor()
    await monitor.monitor_new_tokens()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")