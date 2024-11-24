from datetime import datetime
import asyncio
import json
import os
import websockets


class PumpPortalMonitor:
    def __init__(self):
        self.uri = "wss://pumpportal.fun/api/data"
        self.known_tokens = set()
        self.log_path = r"C:\Users\gdllh\OneDrive\Desktop\pumpfun succsesfull bot\safety_pass1\new_ca\tokens_log.txt"
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    async def log_token_data(self, data):
        """Log token data to file"""
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(json.dumps(data, indent=2))
                f.write("\n")
        except Exception as e:
            print(f"Error writing to log file: {str(e)}")

    async def monitor_new_tokens(self):
        """Monitor new token creations"""
        print("🚀 Starting PumpPortal token monitor...")
        print("Press Ctrl+C to stop")
        
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    print("Connected to PumpPortal WebSocket")
                    
                    # Subscribe to new token events
                    payload = {
                        "method": "subscribeNewToken"
                    }
                    await websocket.send(json.dumps(payload))
                    print("Subscribed to new token events")
                    
                    # Listen for messages
                    async for message in websocket:
                        data = json.loads(message)
                        # Log all messages
                        await self.log_token_data(data)
                        
                        print("\n🆕 New Token Event:")
                        print(json.dumps(data, indent=2))
                        
                        # You can add specific parsing here based on the data structure
                        if 'token' in data or 'mint' in data:
                            token_address = data.get('token', {}).get('address') or data.get('mint')
                            if token_address and token_address not in self.known_tokens:
                                self.known_tokens.add(token_address)
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