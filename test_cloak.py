import sys
import asyncio
import pandas as pd

sys.path.append("/Users/hoangkien/NLV/bot-amazon-jp")
from register_worker import process_account

async def test():
    # Read the first account from AmazonJP_test.xlsx
    df = pd.read_excel("AmazonJP_test.xlsx")
    
    # Check if there is data
    if df.empty:
        print("No accounts in AmazonJP_test.xlsx")
        return
        
    first_row = df.iloc[0]
    email = str(first_row.get("Mail", ""))
    pswd = str(first_row.get("Password", ""))
    proxy = str(first_row.get("Proxy", ""))
    
    print(f"Testing with Email: {email}, Proxy: {proxy}")
    
    email_param = f"{email}|{pswd}"
    
    # Run the worker function
    result = await process_account(email_param, pswd, proxy, idx=1, chrome_path="dummy_path_since_it_is_hardcoded")
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(test())
