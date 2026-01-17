import discord
from discord.ext import commands, tasks
import aiohttp
import os
from datetime import datetime, time, timezone, timedelta
import asyncio

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration from environment variables
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
CR_API_KEY = os.environ.get('CR_API_KEY')
PLAYER_TAG = os.environ.get('PLAYER_TAG')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', 0))

# Clash Royale API endpoint
CR_API_BASE = 'https://api.clashroyale.com/v1'

# Store the last shop data
last_shop_data = None

async def get_player_data():
    """Fetch player data from Clash Royale API"""
    headers = {
        'Authorization': f'Bearer {CR_API_KEY}'
    }
    
    # Remove # from player tag if present
    tag = PLAYER_TAG.replace('#', '')
    url = f'{CR_API_BASE}/players/%23{tag}'
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"API Error: {response.status}")
                    return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def create_shop_embed(data):
    """Create a nice embed for shop data"""
    global last_shop_data
    last_shop_data = data
    
    embed = discord.Embed(
        title="🛒 Clash Royale Emoji Shop",
        description=f"Shop checked on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        color=discord.Color.blue()
    )
    
    if data:
        player_name = data.get('name', 'Unknown')
        embed.add_field(name="👤 Player", value=player_name, inline=True)
        embed.add_field(name="🏆 Trophies", value=f"{data.get('trophies', 'N/A'):,}", inline=True)
        embed.add_field(name="⭐ Level", value=data.get('expLevel', 'N/A'), inline=True)
        
        embed.add_field(
            name="📝 Note",
            value="The Clash Royale API doesn't provide direct emote shop data. However, you can check your in-game shop and use this bot as a daily reminder!",
            inline=False
        )
        
        if 'cards' in data:
            total_cards = len(data['cards'])
            embed.add_field(name="🃏 Cards Unlocked", value=total_cards, inline=True)
        
        if 'currentDeck' in data:
            deck_cards = [card['name'] for card in data['currentDeck'][:4]]
            if deck_cards:
                embed.add_field(
                    name="🎴 Current Deck (First 4)",
                    value=", ".join(deck_cards),
                    inline=False
                )
        
        embed.set_footer(text="💡 Use !myshop to check anytime | Shop resets daily at 12 AM UTC")
    else:
        embed.add_field(
            name="❌ Error",
            value="Could not fetch data from Clash Royale API.",
            inline=False
        )
    
    return embed

@tasks.loop(hours=24)
async def daily_shop_check():
    """Post shop reminder daily at shop reset time"""
    await bot.wait_until_ready()
    
    now = datetime.now(timezone.utc)
    next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if now.hour >= 0:
        next_reset += timedelta(days=1)
    
    wait_seconds = (next_reset - now).total_seconds()
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
    
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Channel {CHANNEL_ID} not found!")
        return
    
    data = await get_player_data()
    embed = create_shop_embed(data)
    
    await channel.send("🔔 **Daily Shop Reset!** The Clash Royale shop has refreshed!", embed=embed)

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is now online!')
    print(f'Bot ID: {bot.user.id}')
    print(f'Monitoring player: {PLAYER_TAG}')
    print(f'Posting to channel: {CHANNEL_ID}')
    
    if not daily_shop_check.is_running():
        daily_shop_check.start()

@bot.command(name='myshop', aliases=['shop', 'checkshop', 'emotes'])
async def my_shop(ctx):
    """Check your shop anytime"""
    await ctx.send("🔍 Checking your Clash Royale shop...")
    
    data = await get_player_data()
    embed = create_shop_embed(data)
    
    await ctx.send(embed=embed)

@bot.command(name='lastshop')
async def last_shop(ctx):
    """Show the last shop data that was fetched"""
    global last_shop_data
    
    if last_shop_data:
        embed = create_shop_embed(last_shop_data)
        embed.title = "🛒 Last Checked Shop Data"
        await ctx.send("Here's the last shop data I fetched:", embed=embed)
    else:
        await ctx.send("❌ No shop data available yet! Use `!myshop` to fetch current data.")

@bot.command(name='setchannel')
@commands.has_permissions(administrator=True)
async def set_channel(ctx):
    """Set the current channel for daily updates"""
    channel_id = ctx.channel.id
    await ctx.send(
        f"✅ This channel is set for daily updates!\n"
        f"📋 Channel ID: `{channel_id}`"
    )

@bot.command(name='commands')
async def commands_list(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🤖 Clash Royale Shop Bot - Commands",
        description="Here are all the commands you can use:",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="!myshop (or !shop, !checkshop, !emotes)",
        value="Check your current shop data. Use this if you missed the daily update!",
        inline=False
    )
    
    embed.add_field(
        name="!lastshop",
        value="Show the last shop data that was automatically fetched",
        inline=False
    )
    
    embed.add_field(
        name="!setchannel",
        value="Set this channel for daily updates (Admin only)",
        inline=False
    )
    
    embed.add_field(
        name="!commands",
        value="Show this help message",
        inline=False
    )
    
    embed.set_footer(text="Shop resets daily at 12:00 AM UTC")
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
