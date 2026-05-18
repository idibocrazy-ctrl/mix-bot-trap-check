import aiohttp
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

async def check_ban(uid: str) -> dict | None:

    api_url = f"http://np2.npcloud.online:2053/check?uid={uid}"

    timeout = aiohttp.ClientTimeout(total=30)

    try:

        async with aiohttp.ClientSession(timeout=timeout) as session:

            async with session.get(api_url) as response:

                response.raise_for_status()

                response_data = await response.json()

                if response_data.get("status") == 200:

                    data = response_data.get("data")

                    if data:

                        return {
                            "is_banned": data.get("is_banned", 0),
                            "nickname": data.get("nickname", ""),
                            "period": data.get("period", 0),
                            "region": data.get("region", "N/A")
                        }

                return None

    except aiohttp.ClientError as e:

        print(f"API request failed for UID {uid}: {e}")
        return None

    except asyncio.TimeoutError:

        print(f"API request timed out for UID {uid}.")
        return None

    except Exception as e:

        print(f"Unexpected error for UID {uid}: {e}")
        return None
