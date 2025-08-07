import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import aiohttp
from datetime import datetime, timedelta

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
ADMIN_ROLE_IDS = set(os.getenv("ADMIN_ROLE_IDS").split(","))

DISCORD_API_BASE = "https://discord.com/api"

sessions = {} 

@app.get("/")
def index():
    return RedirectResponse("/login")

@app.get("/login")
def login():
    discord_oauth_url = (
        f"{DISCORD_API_BASE}/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds%20guilds.members.read"
    )
    return RedirectResponse(discord_oauth_url) 

@app.get("/callback") 
async def callback(code: str): 
    async with aiohttp.ClientSession() as session:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET, 
            "grant_type": "authorization_code",
            "code": code, 
            "redirect_uri": REDIRECT_URI,
            "scope": "identify guilds guilds.members.read"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(f"{DISCORD_API_BASE}/oauth2/token", data=data, headers=headers) as resp:
            token_data = await resp.json()

        access_token = token_data.get("access_token")
        if not access_token:
            return HTMLResponse("Authentication failed.", status_code=401)

        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(f"{DISCORD_API_BASE}/users/@me", headers=headers) as resp:
            user = await resp.json()

        async with session.get(f"{DISCORD_API_BASE}/guilds/{GUILD_ID}/members/{user['id']}", headers=headers) as resp:
            member_data = await resp.json()

        user_id = user["id"]
        user_roles = member_data.get("roles", [])
        is_admin = any(role in ADMIN_ROLE_IDS for role in user_roles)
        is_owner = user_id == member_data.get("guild", {}).get("owner_id", None)

        user_avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{user['avatar']}.png"  # Avatar URL

        sessions[user_id] = {
            "username": user["username"],
            "discriminator": user["discriminator"],
            "admin": is_admin or is_owner,
            "avatar_url": user_avatar_url  # Save the avatar URL
        }

        # Create a redirect response and set a cookie for user_id
        response = RedirectResponse(f"/dashboard?user_id={user_id}")
        response.set_cookie("user_id", user_id)  # Store user_id in cookie
        return response
 
@app.get("/dashboard") 
def dashboard(request: Request):
    # Check if the user_id cookie exists
    user_id = request.cookies.get("user_id")
    
    if not user_id or user_id not in sessions:
        return RedirectResponse("/login")  # If no valid session, redirect to login

    user_data = sessions.get(user_id)

    if user_data["admin"]:
        commands = {
            "economy": [
                {"name": "/balance", "description": "Check your account balance"},
                {"name": "/daily", "description": "Claim your daily reward of $100!"},
                {"name": "/leaderboard", "description": "See the top 10 users with the most money!"},
                {"name": "/stocks", "description": "Use this command to see the current stocks!"},
                {"name": "/buy", "description": "Buy stacks from the Arch Angel market!"},
                {"name": "/sell", "description": "Sell your stocks for money!"},
                {"name": "/portfolio", "description": "Look at your portfolio."}
            ],
            "gambling": [
                {"name": "/slots", "description": "Play slots and spin a good row!"},
                {"name": "/coinflip", "description": "Toss a coin and hope you're lucky!"},
                {"name": "/clicker", "description": "Use this to click the button and make money!"},
                {"name": "/blackjack", "description": "Play blackjack and win money."},
                {"name": "/roll", "description": "Roll the dice and win!"},
                {"name": "/duel", "description": "Challenge your friends to a duel!"},
                {"name": "/bomb", "description": "Defuse a bomb for money!"},
                {"name": "/rob", "description": "Rob another user for their money!"}
            ],
            "grind": [
                {"name": "!key", "description": "Ping the Key Farm role and find people to grind with!"},
                {"name": "!desert", "description": "Ping the Desert role and find people to grind with!"},
                {"name": "!needcarry", "description": "Ping high rank users that you need a carry!"},
                {"name": "!carry", "description": "Ping low rank users that you can carry them!"},
                {"name": "!apply4carry", "description": "Apply for the 'Carry Verified' role."},
                {"name": "!apply4needcarry", "description": "Apply for the 'Need Carry' role."},
                {"name": "/lootbox", "description": "Find treasure in a box!"}
            ],
            "staff": [
                {"name": "/kick", "description": "Kick a member from the server"},
                {"name": "/ban", "description": "Ban a member from the server"},
                {"name": "/warn", "description": "Warn a member for their actions"},
                {"name": "/mute", "description": "Temporarily mute a member"},
                {"name": "/purge", "description": "Delete messages in bulk"}
            ]
        }
    else:
        commands = {
            "economy": [
                {"name": "/balance", "description": "Check your account balance"},
                {"name": "/daily", "description": "Claim your daily reward of $100!"},
                {"name": "/leaderboard", "description": "See the top 10 users with the most money!"},
            ],
            "gambling": [
                {"name": "/slots", "description": "Play slots and spin a good row!"},
                {"name": "/coinflip", "description": "Toss a coin and hope you're lucky!"}
            ],
            "grind": [ 
                {"name": "!key", "description": "Ping the Key Farm role and find people to grind with!"},
                {"name": "!desert", "description": "Ping the Desert role and find people to grind with!"},
                {"name": "!needcarry", "description": "Ping high rank users that you need a carry!"},
                {"name": "!carry", "description": "Ping low rank users that you can carry them!"},
                {"name": "!apply4carry", "description": "Apply for the 'Carry Verified' role."},
                {"name": "!apply4needcarry", "description": "Apply for the 'Need Carry' role."},
                {"name": "/lootbox", "description": "Find treasure in a box!"}
            ],
        } 

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": f"{user_data['username']}#{user_data['discriminator']}",
        "admin": user_data["admin"],  
        "commands": commands,
        "user_avatar_url": user_data["avatar_url"],  # Pass avatar URL
        "display_name": user_data['username']  # Display the name (without discriminator)
    })

current_raid = {
    "snow_island": "Not started",
    "jungle_island": "Not started",
    "dedu_island": "Not started"
} 

@app.get("/current_raid") 
async def current_raid_status():
    return {"current_raid": current_raid}

def get_current_raid(): 
    current_minute = datetime.now().minute

    for raid, times in raid_times.items():
        if times["start"] <= current_minute <= times["end"]:
            return raid, "In Progress"

    return "jungle_island", "Not started" 

raid_times = {
    "dedu_island": {"start": 15, "end": 29},
    "snow_island": {"start": 30, "end": 44},  
    "jungle_island": {"start": 15, "end": 29},
}

def get_next_raid_start(): 
    current_minute = datetime.now().minute 
    next_raid_start = None

    for raid, times in raid_times.items():
        if current_minute < times["start"]:
            next_raid_start = f"{raid} starts at {times['start']} minute"
            break
        elif current_minute > times["end"]:
            next_raid_start = f"{raid} starts at {times['start']} minute"

    if not next_raid_start:
        next_raid_start = f"Next raid starts at 00 minute (Jungle Island)"

    return next_raid_start

@app.get("/current_raid_page")
async def current_raid_page(request: Request):
    current_time = datetime.now().strftime('%H:%M:%S')

    current_raid, raid_status = get_current_raid()

    raid_status_dict = {
        "dedu_island": "Not started",
        "snow_island": "Not started",
        "jungle_island": "Not started"
    }
    raid_status_dict[current_raid] = raid_status  

    next_raid_start = get_next_raid_start()

    return templates.TemplateResponse("current_raid.html", {
        "request": request,
        "current_time": current_time,
        "raid_status": raid_status_dict,
        "time_to_next_raid": next_raid_start
    })

@app.get("/logout")
def logout(request: Request):
    # Retrieve user_id from cookie
    user_id = request.cookies.get("user_id")
    
    if user_id:
        sessions.pop(user_id, None)  # Remove session data
    
    # Clear the cookie and redirect to login page
    response = RedirectResponse(url="/login")
    response.delete_cookie("user_id")  # Deleting the "user_id" cookie
    return response
