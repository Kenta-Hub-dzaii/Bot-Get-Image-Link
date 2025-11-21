import discord
import os
import aiohttp
import json
import asyncio
import requests
import base64
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta
import humanize
from typing import Optional
import random
import string
import discord
from discord import app_commands

# Load environment variables
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Database files
WHITELIST_FILE = 'whitelist.json'
BLACKLIST_FILE = 'blacklist.json'
VIOLATION_LOG_FILE = 'violation_log.json'
USAGE_LOG_FILE = 'usage_log.json'
USER_STATS_FILE = 'user_stats.json'
SERVER_SETTINGS_FILE = 'server_settings.json'
BACKUP_DATA_FILE = 'backup_data.json'
PREMIUM_USERS_FILE = 'premium_users.json'
TCOIN_DATA_FILE = 'tcoin_data.json'
ECONOMY_DATA_FILE = 'economy_data.json'
TAG_DATA_FILE = 'tag_data.json'
BOX_DATA_FILE = 'box_data.json'
TICKET_DATA_FILE = 'ticket_data.json'
BANNED_CMD_USERS_FILE = 'banned_cmd_users.json'

def load_json(filename):
    """Load data from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(filename, data):
    """Save data to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Load data
whitelist_data = load_json(WHITELIST_FILE)
blacklist_data = load_json(BLACKLIST_FILE)
violation_log_data = load_json(VIOLATION_LOG_FILE)
usage_log = load_json(USAGE_LOG_FILE)
user_stats = load_json(USER_STATS_FILE)
server_settings = load_json(SERVER_SETTINGS_FILE)
backup_data = load_json(BACKUP_DATA_FILE)
premium_users = load_json(PREMIUM_USERS_FILE)
tcoin_data = load_json(TCOIN_DATA_FILE)
economy_data = load_json(ECONOMY_DATA_FILE)
tag_data = load_json(TAG_DATA_FILE)
box_data = load_json(BOX_DATA_FILE)
ticket_data = load_json(TICKET_DATA_FILE)
banned_cmd_users = load_json(BANNED_CMD_USERS_FILE)

# Initialize default data
whitelist = whitelist_data.get('users', []) if isinstance(whitelist_data, dict) else whitelist_data
blacklist = blacklist_data.get('users', []) if isinstance(blacklist_data, dict) else blacklist_data
violation_log = violation_log_data.get('logs', []) if isinstance(violation_log_data, dict) else violation_log_data
premium_users = premium_users.get('users', []) if isinstance(premium_users, dict) else premium_users
tcoin_users = tcoin_data.get('users', {}) if isinstance(tcoin_data, dict) else tcoin_data
daily_limits = tcoin_data.get('daily_limits', {}) if isinstance(tcoin_data, dict) else {}
economy_users = economy_data.get('users', {}) if isinstance(economy_data, dict) else economy_data
tags = tag_data.get('tags', {}) if isinstance(tag_data, dict) else tag_data
user_tags = tag_data.get('user_tags', {}) if isinstance(tag_data, dict) else {}
boxes = box_data.get('boxes', {}) if isinstance(box_data, dict) else box_data
user_boxes = box_data.get('user_boxes', {}) if isinstance(box_data, dict) else {}
ticket_setups = ticket_data.get('setups', {}) if isinstance(ticket_data, dict) else ticket_data
banned_cmd_users = banned_cmd_users.get('users', {}) if isinstance(banned_cmd_users, dict) else banned_cmd_users

# Configuration from .env
BOT_MODE = os.getenv('BOT_MODE', 'public')
DAILY_LIMIT_MB = int(os.getenv('DAILY_LIMIT_MB', 100))
DAILY_LIMIT_BYTES = DAILY_LIMIT_MB * 1024 * 1024
IMGUR_CLIENT_ID = os.getenv('IMGUR_CLIENT_ID')
VIOLATION_CHANNEL_ID = os.getenv('VIOLATION_LOG_CHANNEL_ID')
ADMIN_USER_IDS = [int(x.strip()) for x in os.getenv('ADMIN_USER_IDS', '').split(',') if x.strip()]
AUTO_DELETE_TIME = int(os.getenv('AUTO_DELETE_TIME', 300))
MAX_IMAGES = int(os.getenv('MAX_IMAGES', 10))
ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif,webp,bmp').split(',')
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 32))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
COOLDOWN_TIME = int(os.getenv('COOLDOWN_TIME', 30))
BACKUP_CHANNEL_IDS = [int(x.strip()) for x in os.getenv('BACKUP_CHANNEL_IDS', '').split(',') if x.strip()]
AUTO_BACKUP = os.getenv('AUTO_BACKUP', 'true').lower() == 'true'
LANGUAGE = os.getenv('LANGUAGE', 'vi')
PREMIUM_MODE = os.getenv('PREMIUM_MODE', 'false').lower() == 'true'
REPORT_CHANNEL_ID = os.getenv('REPORT_CHANNEL_ID')
TCOIN_WEB_URL = os.getenv('TCOIN_WEB_URL', 'https://your-tcoin-website.com')

# GIF URLs
UPLOADING_GIF = "https://media.giphy.com/media/3o7bu8sRnYpTOG1p8k/giphy.gif"
SUCCESS_GIF = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"
ERROR_GIF = "https://media.giphy.com/media/3o7aD2d7hy9ktXNDP2/giphy.gif"
WARNING_GIF = "https://media.giphy.com/media/l0HU7JI1m1eEwz7K8/giphy.gif"

class ImgBBUploader:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.imgbb.com/1/upload"
    
    async def upload_image(self, image_url: str, filename: str = None):
        """Upload image from URL to ImgBB"""
        if not self.api_key:
            return None, "ImgBB API Key not configured"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return None, f"Cannot download image from URL: {response.status}"
                    
                    image_data = await response.read()
                    
                    if len(image_data) > MAX_FILE_SIZE_BYTES:
                        return None, f"Image too large (limit {MAX_FILE_SIZE_MB}MB)"
                    
                    base64_image = base64.b64encode(image_data).decode()
                    
                    form_data = aiohttp.FormData()
                    form_data.add_field('key', self.api_key)
                    form_data.add_field('image', base64_image)
                    if filename:
                        form_data.add_field('name', filename)
                    
                    async with session.post(self.base_url, data=form_data) as upload_response:
                        result = await upload_response.json()
                        print(f"ImgBB Response: {result}")
                        
                        if upload_response.status == 200 and result.get('success', False):
                            data = result['data']
                            
                            image_info = {
                                'id': data.get('id', 'unknown'),
                                'url': data.get('url', ''),
                                'display_url': data.get('display_url', ''),
                                'thumb': data.get('thumb', {}).get('url', '') if isinstance(data.get('thumb'), dict) else data.get('thumb', ''),
                                'delete_url': data.get('delete_url', ''),
                                'size': data.get('size', 0),
                                'width': data.get('width', 0),
                                'height': data.get('height', 0),
                                'format': self._get_file_extension(data)
                            }
                            
                            return image_info, None
                        else:
                            error = result.get('error', {}).get('message', 'Unknown error') if isinstance(result.get('error'), dict) else str(result.get('error', 'Unknown error'))
                            return None, f"ImgBB API error: {error}"
                            
        except asyncio.TimeoutError:
            return None, "Timeout connecting to ImgBB"
        except Exception as e:
            return None, f"Upload error: {str(e)}"
    
    def _get_file_extension(self, data):
        if data.get('extension'):
            return data['extension']
        elif data.get('image', {}).get('extension'):
            return data['image']['extension']
        elif data.get('url'):
            url = data['url']
            if '.' in url:
                return url.split('.')[-1].lower()
        return 'unknown'

imgbb_uploader = ImgBBUploader(IMGUR_CLIENT_ID) if IMGUR_CLIENT_ID else None

def is_authorized(user_id):
    user_id = str(user_id)
    if user_id in blacklist:
        return False
    return True

def is_premium(user_id):
    user_id = str(user_id)
    return user_id in premium_users

def is_admin(user_id):
    return user_id in ADMIN_USER_IDS

def is_banned_from_commands(user_id):
    user_id = str(user_id)
    return user_id in banned_cmd_users

def get_user_tcoin(user_id):
    user_id = str(user_id)
    return tcoin_users.get(user_id, 0)

def add_user_tcoin(user_id, amount):
    user_id = str(user_id)
    if user_id not in tcoin_users:
        tcoin_users[user_id] = 0
    tcoin_users[user_id] += amount
    save_json(TCOIN_DATA_FILE, {'users': tcoin_users, 'daily_limits': daily_limits})

def get_user_economy(user_id):
    user_id = str(user_id)
    if user_id not in economy_users:
        economy_users[user_id] = {
            'balance': 0,
            'daily_claimed': None,
            'last_work': None,
            'level': 1,
            'xp': 0
        }
    return economy_users[user_id]

def update_user_economy(user_id, data):
    user_id = str(user_id)
    economy_users[user_id] = data
    save_json(ECONOMY_DATA_FILE, {'users': economy_users})

def get_daily_limit_count(user_id, limit_type):
    user_id = str(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    key = f"{user_id}_{limit_type}_{today}"
    return daily_limits.get(key, 0)

def update_daily_limit_count(user_id, limit_type):
    user_id = str(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    key = f"{user_id}_{limit_type}_{today}"
    daily_limits[key] = daily_limits.get(key, 0) + 1
    save_json(TCOIN_DATA_FILE, {'users': tcoin_users, 'daily_limits': daily_limits})

def can_earn_tcoin(user_id, limit_type):
    max_attempts = 10 if limit_type == 'upload' else 5
    return get_daily_limit_count(user_id, limit_type) < max_attempts

def get_user_daily_usage(user_id):
    user_id = str(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if user_id not in user_stats:
        user_stats[user_id] = {}
    
    if today not in user_stats[user_id]:
        user_stats[user_id][today] = 0
    
    return user_stats[user_id][today]

def update_user_daily_usage(user_id, size_bytes):
    user_id = str(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if user_id not in user_stats:
        user_stats[user_id] = {}
    
    if today not in user_stats[user_id]:
        user_stats[user_id][today] = 0
    
    user_stats[user_id][today] += size_bytes
    save_json(USER_STATS_FILE, user_stats)

def get_remaining_daily_usage(user_id):
    used = get_user_daily_usage(user_id)
    remaining = DAILY_LIMIT_BYTES - used
    return max(0, remaining)

def can_upload(user_id, file_size):
    if is_premium(user_id):
        return True
    return get_remaining_daily_usage(user_id) >= file_size

def get_daily_limit(user_id):
    if is_premium(user_id):
        return DAILY_LIMIT_BYTES * 5
    return DAILY_LIMIT_BYTES

async def log_violation(user: discord.User, attachment_url: str, reason: str):
    violation_data = {
        'user_id': str(user.id),
        'user_name': f"{user.name}#{user.discriminator}",
        'attachment_url': attachment_url,
        'reason': reason,
        'timestamp': datetime.now().isoformat()
    }
    
    violation_log.append(violation_data)
    save_json(VIOLATION_LOG_FILE, {'logs': violation_log})
    
    if str(user.id) not in blacklist:
        blacklist.append(str(user.id))
        save_json(BLACKLIST_FILE, {'users': blacklist})
    
    if VIOLATION_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(VIOLATION_CHANNEL_ID))
            if channel:
                embed = discord.Embed(
                    title="🚨 CONTENT VIOLATION - AUTO BLACKLISTED",
                    description=f"User has been automatically added to blacklist",
                    color=0xff0000,
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="👤 Violating User", value=f"{user.mention} (`{user.id}`)", inline=False)
                embed.add_field(name="📄 Reason", value=reason, inline=False)
                embed.add_field(name="🔗 Image Link", value=f"[View Image]({attachment_url})", inline=False)
                embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
                
                await channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Error sending violation log: {e}")

def log_usage(user_id, command: str, file_size: int = 0):
    user_id = str(user_id)
    timestamp = datetime.now().isoformat()
    
    if user_id not in usage_log:
        usage_log[user_id] = []
    
    usage_log[user_id].append({
        'command': command,
        'file_size': file_size,
        'timestamp': timestamp
    })
    
    usage_log[user_id] = usage_log[user_id][-100:]
    save_json(USAGE_LOG_FILE, usage_log)

async def backup_image(user_id, image_url, image_data):
    backup_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    backup_data[backup_id] = {
        'user_id': str(user_id),
        'image_url': image_url,
        'image_data': image_data,
        'timestamp': datetime.now().isoformat(),
        'backup_id': backup_id
    }
    
    save_json(BACKUP_DATA_FILE, backup_data)
    
    if AUTO_BACKUP and BACKUP_CHANNEL_IDS:
        for channel_id in BACKUP_CHANNEL_IDS:
            try:
                channel = bot.get_channel(channel_id)
                if channel:
                    embed = discord.Embed(
                        title="📦 IMAGE BACKUP",
                        color=0x00ff00,
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="👤 User", value=f"<@{user_id}>", inline=True)
                    embed.add_field(name="🆔 Backup ID", value=backup_id, inline=True)
                    embed.add_field(name="🔗 URL", value=f"[Image Link]({image_url})", inline=True)
                    embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
                    
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"❌ Error backing up image to channel {channel_id}: {e}")
    
    return backup_id

def get_user_info_embed(user: discord.User):
    user_id = str(user.id)
    
    embed = discord.Embed(
        title=f"👤 User Info {user.display_name}",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="📛 Full Name", value=f"{user.name}#{user.discriminator}", inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{user.id}`", inline=True)
    embed.add_field(name="📅 Account Created", value=f"<t:{int(user.created_at.timestamp())}:D>", inline=True)
    
    today_usage = get_user_daily_usage(user.id)
    remaining = get_remaining_daily_usage(user.id)
    daily_limit = get_daily_limit(user.id)
    
    embed.add_field(
        name="📊 Today's Usage",
        value=f"**Used:** {humanize.naturalsize(today_usage)}\n**Remaining:** {humanize.naturalsize(remaining)}\n**Limit:** {humanize.naturalsize(daily_limit)}",
        inline=False
    )
    
    tcoin_amount = get_user_tcoin(user.id)
    embed.add_field(name="🪙 Tcoin", value=f"**{tcoin_amount}** Tcoin", inline=True)
    
    status = "✅ Allowed" if is_authorized(user.id) else "❌ Blocked"
    embed.add_field(name="🔐 Status", value=status, inline=True)
    
    premium_status = "⭐ PREMIUM" if is_premium(user.id) else "🔹 STANDARD"
    embed.add_field(name="💎 Account Type", value=premium_status, inline=True)
    
    embed.add_field(name="🔧 Bot Mode", value=BOT_MODE.upper(), inline=True)
    
    total_commands = len(usage_log.get(user_id, []))
    embed.add_field(name="📈 Total Commands", value=f"**{total_commands}** commands", inline=True)
    
    embed.set_footer(text=f"User ID: {user.id}")
    
    return embed

def add_report_button(embed):
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="📢 Report Bug", 
        style=discord.ButtonStyle.danger,
        custom_id="report_bug"
    ))
    return view

class ServerSelectDropdown(discord.ui.Select):
    def __init__(self, guilds, command_type: str):
        options = []
        for guild in guilds[:25]:
            guild_name = guild.name[:25] + "..." if len(guild.name) > 25 else guild.name
            options.append(
                discord.SelectOption(
                    label=guild_name,
                    value=str(guild.id),
                    description=f"Members: {guild.member_count}",
                    emoji="🏠"
                )
            )
        
        placeholder = "Select server to get logo..." if command_type == "logo" else "Select server to get logo link..."
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )
        self.command_type = command_type
    
    async def callback(self, interaction: discord.Interaction):
        guild_id = int(self.values[0])
        guild = bot.get_guild(guild_id)
        
        if not guild:
            embed = discord.Embed(title="❌ Server not found", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        server_icon = guild.icon
        if not server_icon:
            embed = discord.Embed(
                title="❌ Server has no logo",
                description=f"Server **{guild.name}** has no logo!",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if self.command_type == "logo":
            embed = discord.Embed(
                title=f"🏠 Server Logo: {guild.name}",
                description=f"Logo of server **{guild.name}**",
                color=0x0099ff,
                timestamp=datetime.now()
            )
            embed.set_image(url=server_icon.url)
        else:
            embed = discord.Embed(
                title=f"🔗 Server Logo Link: {guild.name}",
                description=f"Logo link of server **{guild.name}**",
                color=0x0099ff,
                timestamp=datetime.now()
            )
            embed.add_field(name="🔗 Logo Link", value=f"```{server_icon.url}```", inline=False)
        
        embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👥 Members", value=f"`{guild.member_count}`", inline=True)
        embed.add_field(name="📅 Server Created", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="👤 Requested by", value=interaction.user.mention, inline=True)
        embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=server_icon.url))
        view.add_item(discord.ui.Button(label="🌐 Open Image", style=discord.ButtonStyle.link, url=server_icon.url))
        
        log_usage(interaction.user.id, f'get{"logo" if self.command_type == "logo" else "linklogo"}server')
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ServerSelectView(discord.ui.View):
    def __init__(self, guilds, command_type: str):
        super().__init__(timeout=60.0)
        self.add_item(ServerSelectDropdown(guilds, command_type))

class ImageConverterView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300.0)
        self.user_id = user_id
        self.original_image = None
    
    @discord.ui.select(
        placeholder="Select format to convert...",
        options=[
            discord.SelectOption(label="PNG", value="png", description="Convert to PNG", emoji="🖼️"),
            discord.SelectOption(label="JPEG", value="jpeg", description="Convert to JPEG", emoji="📷"),
            discord.SelectOption(label="WEBP", value="webp", description="Convert to WEBP", emoji="🌐"),
        ]
    )
    async def convert_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)
            return
        
        format_type = select.values[0]
        
        if not self.original_image:
            await interaction.response.send_message("❌ Original image not found!", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            imgbb_data, error = await imgbb_uploader.upload_image(self.original_image, f"converted_image.{format_type}")
            
            if error:
                await interaction.followup.send(f"❌ Conversion error: {error}", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="✅ Conversion successful!",
                description=f"Image converted to **{format_type.upper()}** format",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            embed.add_field(name="🔗 New Image Link", value=f"```{imgbb_data['url']}```", inline=False)
            embed.add_field(name="🖼️ Format", value=format_type.upper(), inline=True)
            embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
            embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=imgbb_data['url']))
            view.add_item(discord.ui.Button(label="🌐 Open Image", style=discord.ButtonStyle.link, url=imgbb_data['url']))
            
            log_usage(interaction.user.id, f'convert_to_{format_type}')
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Conversion error: {str(e)}", ephemeral=True)

class TicketSetupModal(discord.ui.Modal, title='Ticket Setup'):
    category_name = discord.ui.TextInput(
        label='Category Name',
        placeholder='Enter category name for tickets...',
        default='TICKETS',
        max_length=50
    )
    
    channel_name = discord.ui.TextInput(
        label='Channel Name',
        placeholder='Enter channel name for tickets...',
        default='🎫create-ticket',
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        ticket_setups[guild_id] = {
            'category_name': self.category_name.value,
            'channel_name': self.channel_name.value,
            'setup_by': interaction.user.id,
            'setup_at': datetime.now().isoformat()
        }
        save_json(TICKET_DATA_FILE, {'setups': ticket_setups})
        
        embed = discord.Embed(
            title="✅ Ticket System Setup",
            description="Ticket system has been configured!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="🏷️ Category Name", value=self.category_name.value, inline=True)
        embed.add_field(name="💬 Channel Name", value=self.channel_name.value, inline=True)
        embed.add_field(name="👤 Setup by", value=interaction.user.mention, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'✅ {bot.user} has connected successfully!')
    print(f'📊 Active on {len(bot.guilds)} servers')
    print(f'🔧 Mode: {BOT_MODE.upper()}')
    print(f'💾 Limit: {DAILY_LIMIT_MB}MB/day')
    print(f'📋 Whitelist: {len(whitelist)} users')
    print(f'🚫 Blacklist: {len(blacklist)} users')
    print(f'⭐ Premium users: {len(premium_users)} users')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'❌ Command sync error: {e}')

    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers | /help")
    await bot.change_presence(activity=activity)
    
    if not cleanup_old_data.is_running():
        cleanup_old_data.start()
        print("✅ Started data cleanup task")

# ==================== ADMIN COMMANDS ====================

@bot.tree.command(name="addwhitelist", description="Add user to whitelist (admin only)")
@app_commands.default_permissions(administrator=True)
async def add_whitelist(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    user_id = str(user.id)
    
    if user_id in whitelist:
        embed = discord.Embed(title="❌ User already in whitelist", color=0xff0000)
    else:
        whitelist.append(user_id)
        save_json(WHITELIST_FILE, {'users': whitelist})
        embed = discord.Embed(
            title="✅ Added to whitelist",
            description=f"Added {user.mention} to whitelist!",
            color=0x00ff00
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removewhitelist", description="Remove user from whitelist (admin only)")
@app_commands.default_permissions(administrator=True)
async def remove_whitelist(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    user_id = str(user.id)
    
    if user_id in whitelist:
        whitelist.remove(user_id)
        save_json(WHITELIST_FILE, {'users': whitelist})
        embed = discord.Embed(
            title="✅ Removed from whitelist",
            description=f"Removed {user.mention} from whitelist!",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(title="❌ User not in whitelist", color=0xff0000)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addblacklist", description="Add user to blacklist (admin only)")
@app_commands.default_permissions(administrator=True)
async def add_blacklist(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    user_id = str(user.id)
    
    if user_id in blacklist:
        embed = discord.Embed(title="❌ User already in blacklist", color=0xff0000)
    else:
        blacklist.append(user_id)
        save_json(BLACKLIST_FILE, {'users': blacklist})
        embed = discord.Embed(
            title="✅ Added to blacklist",
            description=f"Added {user.mention} to blacklist!",
            color=0x00ff00
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removeblacklist", description="Remove user from blacklist (admin only)")
@app_commands.default_permissions(administrator=True)
async def remove_blacklist(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    user_id = str(user.id)
    
    if user_id in blacklist:
        blacklist.remove(user_id)
        save_json(BLACKLIST_FILE, {'users': blacklist})
        embed = discord.Embed(
            title="✅ Removed from blacklist",
            description=f"Removed {user.mention} from blacklist!",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(title="❌ User not in blacklist", color=0xff0000)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="whitelist", description="View whitelist (admin only)")
@app_commands.default_permissions(administrator=True)
async def show_whitelist(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    if not whitelist:
        embed = discord.Embed(title="📋 Whitelist", description="Whitelist is empty!", color=0xffa500)
    else:
        users_list = []
        for user_id in whitelist[:20]:
            try:
                user = await bot.fetch_user(int(user_id))
                users_list.append(f"{user.mention} (`{user_id}`)")
            except:
                users_list.append(f"`{user_id}`")
        
        embed = discord.Embed(title="📋 Whitelist", description="\n".join(users_list), color=0x00ff00)
        embed.set_footer(text=f"Total: {len(whitelist)} users")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="blacklist", description="View blacklist (admin only)")
@app_commands.default_permissions(administrator=True)
async def show_blacklist(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    if not blacklist:
        embed = discord.Embed(title="🚫 Blacklist", description="Blacklist is empty!", color=0xffa500)
    else:
        users_list = []
        for user_id in blacklist[:20]:
            try:
                user = await bot.fetch_user(int(user_id))
                users_list.append(f"{user.mention} (`{user_id}`)")
            except:
                users_list.append(f"`{user_id}`")
        
        embed = discord.Embed(title="🚫 Blacklist", description="\n".join(users_list), color=0xff0000)
        embed.set_footer(text=f"Total: {len(blacklist)} users")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addpremium", description="Add user to premium (admin only)")
@app_commands.default_permissions(administrator=True)
async def add_premium(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    user_id = str(user.id)
    
    if user_id in premium_users:
        embed = discord.Embed(title="❌ User already in premium", color=0xff0000)
    else:
        premium_users.append(user_id)
        save_json(PREMIUM_USERS_FILE, {'users': premium_users})
        embed = discord.Embed(
            title="⭐ Added to premium",
            description=f"Added {user.mention} to premium list!",
            color=0xffd700
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removepremium", description="Remove user from premium (admin only)")
@app_commands.default_permissions(administrator=True)
async def remove_premium(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    user_id = str(user.id)
    
    if user_id in premium_users:
        premium_users.remove(user_id)
        save_json(PREMIUM_USERS_FILE, {'users': premium_users})
        embed = discord.Embed(
            title="✅ Removed from premium",
            description=f"Removed {user.mention} from premium list!",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(title="❌ User not in premium", color=0xff0000)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== TCOIN SYSTEM ====================

@bot.tree.command(name="gettcoin", description="Get free Tcoin")
async def get_tcoin(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 No permission to use",
            description="You are not in whitelist. Contact admin to be added.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🪙 Get Free Tcoin",
        description="Choose method to get Tcoin below:",
        color=0xffd700,
        timestamp=datetime.now()
    )
    
    current_tcoin = get_user_tcoin(interaction.user.id)
    embed.add_field(name="💰 Current Tcoin", value=f"**{current_tcoin}** Tcoin", inline=True)
    
    upload_attempts = get_daily_limit_count(interaction.user.id, 'upload')
    link_attempts = get_daily_limit_count(interaction.user.id, 'link')
    
    embed.add_field(name="📸 Upload images", value=f"**{10 - upload_attempts}/10** left", inline=True)
    embed.add_field(name="🔗 Complete links", value=f"**{5 - link_attempts}/5** left", inline=True)
    
    view = discord.ui.View()
    
    upload_button = discord.ui.Button(
        label="📸 Upload Image (+1 Tcoin)",
        style=discord.ButtonStyle.primary,
        custom_id="upload_tcoin"
    )
    
    link_button = discord.ui.Button(
        label="🔗 Complete Link (+2-5 Tcoin)",
        style=discord.ButtonStyle.success,
        custom_id="link_tcoin"
    )
    
    premium_button = discord.ui.Button(
        label="💎 Buy Premium (500 Tcoin/3 days)",
        style=discord.ButtonStyle.danger,
        custom_id="buy_premium"
    )
    
    view.add_item(upload_button)
    view.add_item(link_button)
    view.add_item(premium_button)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="buypremium", description="Buy Premium with Tcoin")
async def buy_premium(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    current_tcoin = get_user_tcoin(interaction.user.id)
    
    if current_tcoin < 500:
        embed = discord.Embed(
            title="❌ Not enough Tcoin",
            description=f"You need 500 Tcoin to buy 3-day Premium!\nCurrent: **{current_tcoin}** Tcoin",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    add_user_tcoin(interaction.user.id, -500)
    
    if user_id not in premium_users:
        premium_users.append(user_id)
        save_json(PREMIUM_USERS_FILE, {'users': premium_users})
    
    embed = discord.Embed(
        title="⭐ Premium purchased successfully!",
        description="You have activated Premium for 3 days!",
        color=0xffd700,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💰 Remaining Tcoin", value=f"**{get_user_tcoin(interaction.user.id)}** Tcoin", inline=True)
    embed.add_field(name="⏰ Duration", value="3 days", inline=True)
    embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="tcoin", description="View your Tcoin")
async def tcoin_info(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    current_tcoin = get_user_tcoin(interaction.user.id)
    
    embed = discord.Embed(
        title="🪙 Tcoin Information",
        description=f"Tcoin of {interaction.user.mention}",
        color=0xffd700,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💰 Balance", value=f"**{current_tcoin}** Tcoin", inline=True)
    
    upload_attempts = get_daily_limit_count(interaction.user.id, 'upload')
    link_attempts = get_daily_limit_count(interaction.user.id, 'link')
    
    embed.add_field(name="📸 Uploads today", value=f"**{upload_attempts}/10** times", inline=True)
    embed.add_field(name="🔗 Links today", value=f"**{link_attempts}/5** times", inline=True)
    
    premium_status = "⭐ ACTIVATED" if is_premium(interaction.user.id) else "🔹 NOT ACTIVATED"
    embed.add_field(name="💎 Premium", value=premium_status, inline=True)
    
    embed.add_field(
        name="📈 How to earn Tcoin",
        value="""• 📸 **Upload images**: +1 Tcoin/time (10 times/day)
• 🔗 **Complete links**: +2-5 Tcoin/time (5 times/day)
• ⭐ **Buy Premium**: 500 Tcoin/3 days""",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== ECONOMY SYSTEM ====================

@bot.tree.command(name="balance", description="View your balance")
async def balance_command(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    user_data = get_user_economy(target_user.id)
    
    embed = discord.Embed(
        title="💰 Balance",
        description=f"Balance of {target_user.mention}",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💵 Coins", value=f"**{user_data['balance']}** coins", inline=True)
    embed.add_field(name="📊 Level", value=f"**{user_data['level']}**", inline=True)
    embed.add_field(name="⭐ XP", value=f"**{user_data['xp']}**", inline=True)
    embed.add_field(name="👤 User", value=target_user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="daily", description="Receive daily coins")
async def daily_command(interaction: discord.Interaction):
    user_data = get_user_economy(interaction.user.id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if user_data['daily_claimed'] == today:
        embed = discord.Embed(
            title="❌ Already claimed today",
            description="You have already claimed your daily coins!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    coins = random.randint(100, 500)
    user_data['balance'] += coins
    user_data['daily_claimed'] = today
    update_user_economy(interaction.user.id, user_data)
    
    embed = discord.Embed(
        title="💰 Daily Reward Claimed!",
        description=f"You received **{coins}** coins!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💵 New Balance", value=f"**{user_data['balance']}** coins", inline=True)
    embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
    embed.add_field(name="📅 Next claim", value=f"<t:{(datetime.now() + timedelta(days=1)).timestamp():.0f}:R>", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="work", description="Work to earn coins")
async def work_command(interaction: discord.Interaction):
    user_data = get_user_economy(interaction.user.id)
    now = datetime.now()
    
    if user_data['last_work']:
        last_work = datetime.fromisoformat(user_data['last_work'])
        if (now - last_work).seconds < 3600:
            remaining = 3600 - (now - last_work).seconds
            embed = discord.Embed(
                title="⏰ Cooldown",
                description=f"You can work again in {remaining//60} minutes!",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    coins = random.randint(50, 200)
    xp = random.randint(5, 15)
    
    user_data['balance'] += coins
    user_data['xp'] += xp
    user_data['last_work'] = now.isoformat()
    
    # Level up check
    xp_needed = user_data['level'] * 100
    if user_data['xp'] >= xp_needed:
        user_data['level'] += 1
        user_data['xp'] = 0
        level_up = True
    else:
        level_up = False
    
    update_user_economy(interaction.user.id, user_data)
    
    embed = discord.Embed(
        title="💼 Work Completed!",
        description=f"You earned **{coins}** coins and **{xp}** XP!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    if level_up:
        embed.add_field(name="🎉 Level Up!", value=f"You reached level **{user_data['level']}**!", inline=False)
    
    embed.add_field(name="💵 Balance", value=f"**{user_data['balance']}** coins", inline=True)
    embed.add_field(name="📊 Level", value=f"**{user_data['level']}**", inline=True)
    embed.add_field(name="⭐ XP", value=f"**{user_data['xp']}**/{user_data['level'] * 100}", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="gamble", description="Gamble your coins (50/50 chance)")
async def gamble_command(interaction: discord.Interaction, amount: int):
    user_data = get_user_economy(interaction.user.id)
    
    if amount <= 0:
        embed = discord.Embed(title="❌ Invalid amount", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if user_data['balance'] < amount:
        embed = discord.Embed(
            title="❌ Not enough coins",
            description=f"You only have **{user_data['balance']}** coins!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # 50/50 chance
    if random.random() < 0.5:
        # Win
        user_data['balance'] += amount
        result = "won"
        color = 0x00ff00
    else:
        # Lose
        user_data['balance'] -= amount
        result = "lost"
        color = 0xff0000
    
    update_user_economy(interaction.user.id, user_data)
    
    embed = discord.Embed(
        title="🎰 Gambling Result",
        description=f"You {result} **{amount}** coins!",
        color=color,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💵 New Balance", value=f"**{user_data['balance']}** coins", inline=True)
    embed.add_field(name="🎯 Result", value=f"You {result}!", inline=True)
    embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== TICKET SYSTEM ====================

@bot.tree.command(name="setup_ticket", description="Setup ticket system")
@app_commands.default_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    await interaction.response.send_modal(TicketSetupModal())

@bot.tree.command(name="setup_list", description="List ticket setups")
@app_commands.default_permissions(administrator=True)
async def setup_list(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in ticket_setups:
        embed = discord.Embed(
            title="❌ No ticket setup",
            description="No ticket system setup for this server!",
            color=0xff0000
        )
    else:
        setup = ticket_setups[guild_id]
        embed = discord.Embed(
            title="🎫 Ticket System Setup",
            color=0x0099ff,
            timestamp=datetime.fromisoformat(setup['setup_at'])
        )
        embed.add_field(name="🏷️ Category Name", value=setup['category_name'], inline=True)
        embed.add_field(name="💬 Channel Name", value=setup['channel_name'], inline=True)
        embed.add_field(name="👤 Setup by", value=f"<@{setup['setup_by']}>", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== TAG SYSTEM ====================

@bot.tree.command(name="tag_list", description="List all tags")
async def tag_list(interaction: discord.Interaction):
    if not tags:
        embed = discord.Embed(title="🏷️ Tags", description="No tags available!", color=0xffa500)
    else:
        tag_list_text = "\n".join([f"• **{name}** - {data['description']}" for name, data in tags.items()])
        embed = discord.Embed(
            title="🏷️ Available Tags",
            description=tag_list_text,
            color=0x0099ff
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="add_tag", description="Add new tag (admin only)")
@app_commands.default_permissions(administrator=True)
async def add_tag(interaction: discord.Interaction, name: str, description: str, content: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
        return
    
    tags[name.lower()] = {
        'description': description,
        'content': content,
        'created_by': interaction.user.id,
        'created_at': datetime.now().isoformat()
    }
    save_json(TAG_DATA_FILE, {'tags': tags, 'user_tags': user_tags})
    
    embed = discord.Embed(
        title="✅ Tag Added",
        description=f"Tag **{name}** has been added!",
        color=0x00ff00
    )
    embed.add_field(name="📝 Description", value=description, inline=True)
    embed.add_field(name="👤 Added by", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== MAIN COMMANDS ====================

@bot.tree.command(name="help", description="Bot usage guide")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Bot Usage Guide",
        description="Image upload and smart content management bot",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="🖼️ Image Upload Commands",
        value="""• `/laylinkanh` - Upload 1 image to ImgBB
• `/laynhieulink` - Upload multiple images to ImgBB (max 10)
• `/laylinkanhdiscord` - Get Discord CDN link (10 seconds)
• `/uploadimgbb` - Upload image to ImgBB with options
• `/uploadmulti` - Upload multiple images at once""",
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Information Commands",
        value="""• `/help` - Show this guide
• `/stats` - Your usage statistics
• `/userinfo` - User information
• `/serverinfo` - Server information
• `/botinfo` - Bot information""",
        inline=False
    )
    
    embed.add_field(
        name="👤 Profile & Server Image Commands",
        value="""• `/layiduser` - Get user Discord ID
• `/laylinklogoprofile` - Get profile picture link
• `/laylogoserver` - Get server logo
• `/laylinklogoserver` - Get server logo link
• `/banneruser` - Get user banner
• `/bannerserver` - Get server banner""",
        inline=False
    )
    
    embed.add_field(
        name="🪙 Tcoin Commands",
        value="""• `/gettcoin` - Get free Tcoin
• `/tcoin` - View Tcoin information
• `/buypremium` - Buy Premium with Tcoin""",
        inline=False
    )
    
    embed.add_field(
        name="💰 Economy Commands",
        value="""• `/balance` - View your balance
• `/daily` - Receive daily coins
• `/work` - Work to earn coins
• `/gamble` - Gamble coins (50/50 chance)""",
        inline=False
    )
    
    embed.add_field(
        name="🎫 Ticket Commands",
        value="""• `/setup_ticket` - Setup ticket system
• `/setup_list` - List ticket setups""",
        inline=False
    )
    
    embed.add_field(
        name="🏷️ Tag Commands",
        value="""• `/tag_list` - List all tags
• `/add_tag` - Add new tag (admin)""",
        inline=False
    )
    
    embed.add_field(
        name="🔧 Utility Commands",
        value="""• `/convertimage` - Convert image format
• `/backupimage` - Backup image
• `/restoreimage` - Restore image from backup
• `/listbackup` - List backups
• `/deletebackup` - Delete backup
• `/report` - Report bug or suggestion
• `/ping` - Check bot latency""",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Management Commands (Admin)",
        value="""• `/addwhitelist` - Add user to whitelist
• `/removewhitelist` - Remove user from whitelist
• `/addblacklist` - Add user to blacklist
• `/removeblacklist` - Remove user from blacklist
• `/addpremium` - Add user to premium
• `/removepremium` - Remove user from premium""",
        inline=False
    )
    
    embed.add_field(
        name="📜 Usage Rules",
        value="""• ✅ **Allowed**: Normal images, memes, artwork, personal photos
• ❌ **Banned**: 18+, gore, violence, sensitive content, inappropriate images
• 💾 **Limit**: 100MB/day/user (Standard), 500MB/day (Premium)
• ⏰ **Upload time**: 1 hour/command
• 📸 **Image count**: Maximum 10 images/upload""",
        inline=False
    )
    
    embed.add_field(
        name="📊 Statistics",
        value=f"• **Mode**: PUBLIC\n• **Blacklist**: {len(blacklist)} users\n• **Premium**: {len(premium_users)} users\n• **Servers**: {len(bot.guilds)} servers",
        inline=False
    )
    
    embed.set_footer(text="Follow rules to avoid being blocked from using bot")
    
    view = add_report_button(embed)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    import discord
from discord import app_commands
from discord.ext import commands

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

import discord
from discord import app_commands

# XÓA TẤT CẢ LỆNH CŨ TRƯỚC KHI ĐĂNG KÝ LẠI
def cleanup_commands():
    commands_to_remove = ['setup', 'setupinfo', 'reset']
    for cmd_name in commands_to_remove:
        try:
            bot.tree.remove_command(cmd_name)
            print(f"✅ Đã xóa lệnh: {cmd_name}")
        except Exception as e:
            print(f"ℹ️ Không thể xóa {cmd_name}: {e}")

# GỌI HÀM DỌN DẸP TRƯỚC KHI ĐĂNG KÝ LỆNH
cleanup_commands()

# LỆNH SETUP
@bot.tree.command(name="setup", description="Set up roles and channels for image upload")
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("🔄 Setting up system...", ephemeral=True)
        
        guild = interaction.guild
        admin = interaction.user
        
        # Tạo danh mục BOT COMMAND
        category = discord.utils.get(guild.categories, name="BOT COMMAND")
        if not category:
            category = await guild.create_category("BOT COMMAND")
            await category.set_permissions(guild.default_role, view_channel=False)
            print(f"✅ Created category: {category.name}")

        # Tạo kênh 📷BOT GET IMAGE LINK📷
        image_channel = discord.utils.get(guild.text_channels, name="📷bot-get-image-link📷")
        if not image_channel:
            image_channel = await guild.create_text_channel(
                "📷bot-get-image-link📷", 
                category=category
            )
            await image_channel.edit(position=0)
            print(f"✅ Created channel: {image_channel.name}")

        # Tạo role allowed
        allowed_role = discord.utils.get(guild.roles, name="allowed")
        if not allowed_role:
            allowed_role = await guild.create_role(
                name="allowed",
                color=discord.Color.green(),
                reason="Role for bot usage permission"
            )
            print(f"✅ Created role: {allowed_role.name}")

        # Tạo role unallowed
        unallowed_role = discord.utils.get(guild.roles, name="unallowed")
        if not unallowed_role:
            unallowed_role = await guild.create_role(
                name="unallowed",
                color=discord.Color.red(),
                reason="Role for no bot usage permission"
            )
            print(f"✅ Created role: {unallowed_role.name}")

        # THÊM TẤT CẢ MỌI NGƯỜI VÀO ROLE ALLOWED (kể cả đã có role hay chưa)
        members = guild.members
        added_count = 0
        error_count = 0
        
        for member in members:
            try:
                # Thêm role allowed cho tất cả mọi người
                await member.add_roles(allowed_role)
                added_count += 1
                print(f"✅ Added allowed role to: {member.display_name}")
            except Exception as e:
                error_count += 1
                print(f"❌ Error adding role to {member.display_name}: {e}")

        # Cấu hình permissions cho danh mục
        await category.set_permissions(allowed_role, view_channel=True, send_messages=True, read_message_history=True)
        await category.set_permissions(unallowed_role, view_channel=False, send_messages=False, read_message_history=False)

        # Tạo embed thông báo hoàn thành
        embed = discord.Embed(
            title="✅ Setup Completed!",
            description="System has been set up successfully",
            color=discord.Color.green()
        )
        embed.add_field(name="📁 Category", value=category.mention, inline=True)
        embed.add_field(name="📷 Image Channel", value=image_channel.mention, inline=True)
        embed.add_field(name="✅ Allowed Role", value=allowed_role.mention, inline=True)
        embed.add_field(name="❌ Unallowed Role", value=unallowed_role.mention, inline=True)
        embed.add_field(name="👥 Members", value=f"Added {added_count} members to allowed role\nErrors: {error_count}", inline=False)
        embed.set_footer(text=f"Set up by {admin.display_name}", icon_url=admin.display_avatar.url)

        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"✅ Setup completed for server: {guild.name}")

    except Exception as e:
        print(f"❌ Setup error: {e}")
        await interaction.followup.send("❌ An error occurred during setup. Please try again later.", ephemeral=True)

# LỆNH SETUPINFO
@bot.tree.command(name="setupinfo", description="View information about the current setup")
async def setupinfo(interaction: discord.Interaction):
    try:
        guild = interaction.guild
        
        # Kiểm tra các thành phần đã được thiết lập
        category = discord.utils.get(guild.categories, name="BOT COMMAND")
        image_channel = discord.utils.get(guild.text_channels, name="📷bot-get-image-link📷")
        allowed_role = discord.utils.get(guild.roles, name="allowed")
        unallowed_role = discord.utils.get(guild.roles, name="unallowed")
        
        embed = discord.Embed(
            title="ℹ️ System Information",
            color=discord.Color.blue()
        )
        
        if category:
            embed.add_field(name="📁 BOT COMMAND Category", value=f"✅ Created\n{category.mention}", inline=True)
        else:
            embed.add_field(name="📁 BOT COMMAND Category", value="❌ Not created", inline=True)
            
        if image_channel:
            embed.add_field(name="📷 Image Channel", value=f"✅ Created\n{image_channel.mention}", inline=True)
        else:
            embed.add_field(name="📷 Image Channel", value="❌ Not created", inline=True)
            
        if allowed_role:
            members_with_role = len(allowed_role.members)
            total_members = guild.member_count
            embed.add_field(name="✅ Allowed Role", value=f"✅ Created\n{members_with_role}/{total_members} members", inline=True)
        else:
            embed.add_field(name="✅ Allowed Role", value="❌ Not created", inline=True)
            
        if unallowed_role:
            embed.add_field(name="❌ Unallowed Role", value=f"✅ Created\n{unallowed_role.mention}", inline=True)
        else:
            embed.add_field(name="❌ Unallowed Role", value="❌ Not created", inline=True)

        # Kiểm tra trạng thái tổng quan
        if all([category, image_channel, allowed_role, unallowed_role]):
            status = "✅ System is fully set up"
        else:
            status = "⚠️ System is not fully set up"
            
        embed.add_field(name="📊 Overall Status", value=status, inline=False)
        embed.set_footer(text="Use /setup to configure the system")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        print(f"❌ Error getting setup info: {e}")
        await interaction.response.send_message("❌ An error occurred while getting setup information.", ephemeral=True)

# LỆNH RESET
@bot.tree.command(name="reset", description="Reset all bot setup and remove created channels/roles")
@app_commands.default_permissions(administrator=True)
async def reset(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("🔄 Resetting system...", ephemeral=True)
        
        guild = interaction.guild
        deleted_items = []
        
        # Xóa kênh 📷BOT GET IMAGE LINK📷
        image_channel = discord.utils.get(guild.text_channels, name="📷bot-get-image-link📷")
        if image_channel:
            try:
                await image_channel.delete()
                deleted_items.append("📷 Image Channel")
                print(f"✅ Deleted channel: {image_channel.name}")
            except Exception as e:
                print(f"❌ Error deleting channel: {e}")

        # Xóa danh mục BOT COMMAND (chỉ xóa nếu rỗng)
        category = discord.utils.get(guild.categories, name="BOT COMMAND")
        if category:
            try:
                # Kiểm tra xem danh mục có còn kênh không
                if len(category.channels) == 0:
                    await category.delete()
                    deleted_items.append("📁 BOT COMMAND Category")
                    print(f"✅ Deleted category: {category.name}")
                else:
                    deleted_items.append("📁 BOT COMMAND Category (not empty, skipped)")
            except Exception as e:
                print(f"❌ Error deleting category: {e}")

        # Xóa role allowed (chỉ xóa nếu bot có quyền)
        allowed_role = discord.utils.get(guild.roles, name="allowed")
        if allowed_role:
            try:
                # Kiểm tra xem role có thể xóa được không
                if allowed_role.position < guild.me.top_role.position:
                    await allowed_role.delete()
                    deleted_items.append("✅ Allowed Role")
                    print(f"✅ Deleted role: {allowed_role.name}")
                else:
                    deleted_items.append("✅ Allowed Role (position too high, skipped)")
            except Exception as e:
                print(f"❌ Error deleting allowed role: {e}")

        # Xóa role unallowed (chỉ xóa nếu bot có quyền)
        unallowed_role = discord.utils.get(guild.roles, name="unallowed")
        if unallowed_role:
            try:
                # Kiểm tra xem role có thể xóa được không
                if unallowed_role.position < guild.me.top_role.position:
                    await unallowed_role.delete()
                    deleted_items.append("❌ Unallowed Role")
                    print(f"✅ Deleted role: {unallowed_role.name}")
                else:
                    deleted_items.append("❌ Unallowed Role (position too high, skipped)")
            except Exception as e:
                print(f"❌ Error deleting unallowed role: {e}")

        # Tạo embed thông báo kết quả
        embed = discord.Embed(
            title="🔄 Reset Completed!",
            description="System reset has been completed",
            color=discord.Color.orange()
        )
        
        if deleted_items:
            embed.add_field(
                name="🗑️ Deleted Items", 
                value="\n".join([f"• {item}" for item in deleted_items]), 
                inline=False
            )
        else:
            embed.add_field(
                name="ℹ️ Status", 
                value="No setup items found to delete", 
                inline=False
            )
            
        embed.set_footer(text=f"Reset by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"✅ Reset completed for server: {guild.name}")

    except Exception as e:
        print(f"❌ Reset error: {e}")
        await interaction.followup.send("❌ An error occurred during reset. Please try again later.", ephemeral=True)

# ĐỒNG BỘ LỆNH SAU KHI ĐĂNG KÝ
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã đồng bộ {len(synced)} lệnh")
    except Exception as e:
        print(f"❌ Lỗi đồng bộ lệnh: {e}")
        
@bot.tree.command(name="laylinkanh", description="Upload 1 image to ImgBB and get link")
async def lay_link_anh(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Blocked from use",
            description="You have been added to blacklist. Contact admin to be removed.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not imgbb_uploader:
        embed = discord.Embed(
            title="❌ ImgBB configuration error", 
            description="ImgBB API Key not configured!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    remaining = get_remaining_daily_usage(interaction.user.id)
    if remaining <= 0 and not is_premium(interaction.user.id):
        embed = discord.Embed(
            title="💾 Out of daily usage",
            description=f"You have used all {DAILY_LIMIT_MB}MB for today. Please come back tomorrow!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📸 Upload Image",
        description="**🔒 Only you can see**\nPlease upload 1 image in the next message!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="⏰ Time", value="1 hour to upload", inline=True)
    embed.add_field(name="💾 Remaining space", value=humanize.naturalsize(remaining), inline=True)
    embed.add_field(name="📝 Formats", value=", ".join(ALLOWED_EXTENSIONS), inline=True)
    embed.add_field(name="👤 Uploader", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Status", value="🟢 Waiting for image...", inline=True)
    
    if is_premium(interaction.user.id):
        embed.add_field(name="💎 Account", value="⭐ PREMIUM", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.attachments
    
    try:
        wait_msg = await bot.wait_for('message', timeout=3600.0, check=check)
        
        if wait_msg.attachments:
            attachment = wait_msg.attachments[0]
            
            if any(attachment.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                if not can_upload(interaction.user.id, attachment.size):
                    embed = discord.Embed(
                        title="💾 Not enough space",
                        description=f"File {humanize.naturalsize(attachment.size)} exceeds remaining space {humanize.naturalsize(remaining)}!",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                uploading_embed = discord.Embed(
                    title="⏳ Uploading...",
                    description=f"**{interaction.user.mention}** is uploading image to ibb.co",
                    color=0xffa500,
                    timestamp=datetime.now()
                )
                uploading_embed.set_image(url=UPLOADING_GIF)
                uploading_embed.add_field(name="📁 File", value=attachment.filename, inline=True)
                uploading_embed.add_field(name="📏 Size", value=humanize.naturalsize(attachment.size), inline=True)
                await interaction.followup.send(embed=uploading_embed, ephemeral=True)
                
                imgbb_data, error = await imgbb_uploader.upload_image(attachment.url, attachment.filename)
                
                if error:
                    error_embed = discord.Embed(
                        title="❌ Upload failed", 
                        description=error, 
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                    return
                
                update_user_daily_usage(interaction.user.id, attachment.size)
                log_usage(interaction.user.id, 'laylinkanh', attachment.size)
                
                if can_earn_tcoin(interaction.user.id, 'upload'):
                    add_user_tcoin(interaction.user.id, 1)
                    update_daily_limit_count(interaction.user.id, 'upload')
                    tcoin_earned = True
                else:
                    tcoin_earned = False
                
                backup_id = await backup_image(interaction.user.id, imgbb_data['url'], imgbb_data)
                
                result_embed = discord.Embed(
                    title="✅ Upload successful!",
                    description=f"**{interaction.user.mention}** uploaded image to ImgBB",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                result_embed.add_field(name="🔗 Image link", value=f"```{imgbb_data['url']}```", inline=False)
                result_embed.add_field(name="🔗 Thumbnail link", value=f"```{imgbb_data['thumb']}```", inline=False)
                result_embed.add_field(name="📁 File name", value=attachment.filename, inline=True)
                result_embed.add_field(name="📏 Size", value=humanize.naturalsize(attachment.size), inline=True)
                result_embed.add_field(name="🖼️ Format", value=imgbb_data['format'].upper(), inline=True)
                result_embed.add_field(name="📐 Image size", value=f"{imgbb_data['width']}x{imgbb_data['height']}", inline=True)
                result_embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
                result_embed.add_field(name="💾 Remaining space", value=humanize.naturalsize(get_remaining_daily_usage(interaction.user.id)), inline=True)
                result_embed.add_field(name="📦 Backup ID", value=f"`{backup_id}`", inline=True)
                
                if tcoin_earned:
                    result_embed.add_field(name="🪙 Tcoin", value="+1 Tcoin", inline=True)
                
                result_embed.set_image(url=imgbb_data['url'])
                result_embed.set_thumbnail(url=SUCCESS_GIF)
                
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=imgbb_data['url']))
                view.add_item(discord.ui.Button(label="🔗 Copy Thumb", style=discord.ButtonStyle.link, url=imgbb_data['thumb']))
                view.add_item(discord.ui.Button(label="🌐 Open Image", style=discord.ButtonStyle.link, url=imgbb_data['url']))
                
                await interaction.followup.send(embed=result_embed, view=view, ephemeral=True)
                
                try:
                    await wait_msg.delete()
                except:
                    pass
                
            else:
                error_embed = discord.Embed(
                    title="❌ Format not supported", 
                    description=f"Only support: {', '.join(ALLOWED_EXTENSIONS)}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            error_embed = discord.Embed(
                title="❌ No image found",
                description="Please attach image when using this command",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏰ Timeout",
            description="You didn't upload image within 1 hour!",
            color=0xffa500
        )
        await interaction.followup.send(embed=timeout_embed, ephemeral=True)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Unknown error",
            description=f"An error occurred: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="laynhieulink", description="Upload multiple images to ImgBB and get links")
async def lay_nhieu_link(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Blocked from use",
            description="You have been added to blacklist. Contact admin to be removed.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not imgbb_uploader:
        embed = discord.Embed(
            title="❌ ImgBB configuration error", 
            description="ImgBB API Key not configured!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    remaining = get_remaining_daily_usage(interaction.user.id)
    if remaining <= 0 and not is_premium(interaction.user.id):
        embed = discord.Embed(
            title="💾 Out of daily usage",
            description=f"You have used all {DAILY_LIMIT_MB}MB for today. Please come back tomorrow!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🖼️ Upload Multiple Images",
        description="**🔒 Only you can see**\nUpload maximum 10 images in the next message!",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="⏰ Time", value="1 hour to upload", inline=True)
    embed.add_field(name="💾 Remaining space", value=humanize.naturalsize(remaining), inline=True)
    embed.add_field(name="📸 Max images", value=f"{MAX_IMAGES} images", inline=True)
    embed.add_field(name="👤 Uploader", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Status", value="🟢 Waiting for images...", inline=True)
    
    if is_premium(interaction.user.id):
        embed.add_field(name="💎 Account", value="⭐ PREMIUM", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.attachments
    
    try:
        wait_msg = await bot.wait_for('message', timeout=3600.0, check=check)
        
        if wait_msg.attachments:
            attachments = [att for att in wait_msg.attachments if any(
                att.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS
            )][:MAX_IMAGES]
            
            if not attachments:
                embed = discord.Embed(
                    title="❌ No valid images",
                    description=f"No images found with supported formats ({', '.join(ALLOWED_EXTENSIONS)})",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            total_size = sum(att.size for att in attachments)
            if not can_upload(interaction.user.id, total_size):
                embed = discord.Embed(
                    title="💾 Not enough space",
                    description=f"Total {humanize.naturalsize(total_size)} exceeds remaining space {humanize.naturalsize(remaining)}!",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            uploading_embed = discord.Embed(
                title=f"⏳ Uploading {len(attachments)} images...",
                description=f"**{interaction.user.mention}** is uploading images to ImgBB",
                color=0xffa500,
                timestamp=datetime.now()
            )
            uploading_embed.set_image(url=UPLOADING_GIF)
            uploading_embed.add_field(name="📊 Total size", value=humanize.naturalsize(total_size), inline=True)
            uploading_embed.add_field(name="📸 Image count", value=len(attachments), inline=True)
            await interaction.followup.send(embed=uploading_embed, ephemeral=True)
            
            uploaded_images = []
            failed_uploads = []
            total_uploaded_size = 0
            tcoin_earned = 0
            
            for attachment in attachments:
                imgbb_data, error = await imgbb_uploader.upload_image(attachment.url, attachment.filename)
                
                if imgbb_data:
                    uploaded_images.append({
                        'filename': attachment.filename,
                        'url': imgbb_data['url'],
                        'thumb': imgbb_data['thumb'],
                        'size': attachment.size,
                        'format': imgbb_data['format'],
                        'width': imgbb_data['width'],
                        'height': imgbb_data['height']
                    })
                    total_uploaded_size += attachment.size
                    
                    if can_earn_tcoin(interaction.user.id, 'upload'):
                        add_user_tcoin(interaction.user.id, 1)
                        update_daily_limit_count(interaction.user.id, 'upload')
                        tcoin_earned += 1
                    
                    await backup_image(interaction.user.id, imgbb_data['url'], imgbb_data)
                else:
                    failed_uploads.append({
                        'filename': attachment.filename,
                        'error': error
                    })
            
            update_user_daily_usage(interaction.user.id, total_uploaded_size)
            log_usage(interaction.user.id, 'laynhieulink', total_uploaded_size)
            
            result_embed = discord.Embed(
                title=f"✅ Uploaded {len(uploaded_images)} images!",
                description=f"**{interaction.user.mention}** uploaded successfully",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            view = discord.ui.View()
            
            links_text = ""
            for i, img in enumerate(uploaded_images, 1):
                links_text += f"{i}. **{img['filename']}**\n```{img['url']}```\n"
                view.add_item(discord.ui.Button(
                    label=f"📋 Image {i}",
                    style=discord.ButtonStyle.link,
                    url=img['url']
                ))
            
            if links_text:
                result_embed.add_field(name="🔗 Link list", value=links_text[:1024], inline=False)
            
            result_embed.add_field(name="📊 Total size", value=humanize.naturalsize(total_uploaded_size), inline=True)
            result_embed.add_field(name="💾 Remaining space", value=humanize.naturalsize(get_remaining_daily_usage(interaction.user.id)), inline=True)
            result_embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
            result_embed.add_field(name="📅 Upload date", value=f"<t:{int(datetime.now().timestamp())}:D>", inline=True)
            result_embed.add_field(name="👤 Uploader", value=interaction.user.mention, inline=True)
            
            if tcoin_earned > 0:
                result_embed.add_field(name="🪙 Tcoin earned", value=f"+{tcoin_earned} Tcoin", inline=True)
            
            if failed_uploads:
                failed_text = "\n".join([f"• {f['filename']}: {f['error']}" for f in failed_uploads[:3]])
                result_embed.add_field(name="❌ Upload failed", value=failed_text, inline=False)
            
            result_embed.set_thumbnail(url=SUCCESS_GIF)
            
            await interaction.followup.send(embed=result_embed, view=view, ephemeral=True)
            
            try:
                await wait_msg.delete()
            except:
                pass
            
        else:
            embed = discord.Embed(
                title="❌ No images found",
                description="Please attach images when using this command",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="⏰ Timeout",
            description="You didn't upload images within 1 hour!",
            color=0xffa500
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Unknown error",
            description=f"An error occurred: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

# ==================== ADDITIONAL COMMANDS ====================

@bot.tree.command(name="uploadimgbb", description="Upload image to ImgBB with advanced options")
async def upload_imgbb(interaction: discord.Interaction):
    await lay_link_anh(interaction)

@bot.tree.command(name="uploadmulti", description="Upload multiple images at once to ImgBB")
async def upload_multi(interaction: discord.Interaction):
    await lay_nhieu_link(interaction)

@bot.tree.command(name="serverinfo", description="Information about current server")
async def server_info(interaction: discord.Interaction):
    guild = interaction.guild
    
    embed = discord.Embed(
        title=f"🏠 Server Info: {guild.name}",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="📅 Created", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
    embed.add_field(name="👥 Members", value=f"`{guild.member_count}`", inline=True)
    embed.add_field(name="📊 Online", value=f"`{sum(1 for m in guild.members if m.status != discord.Status.offline)}`", inline=True)
    embed.add_field(name="💬 Channels", value=f"`{len(guild.channels)}`", inline=True)
    embed.add_field(name="🎭 Roles", value=f"`{len(guild.roles)}`", inline=True)
    embed.add_field(name="🚀 Boost Level", value=f"`{guild.premium_tier}`", inline=True)
    embed.add_field(name="⭐ Boosts", value=f"`{guild.premium_subscription_count}`", inline=True)
    
    if guild.banner:
        embed.add_field(name="🎨 Banner", value=f"[View banner]({guild.banner.url})", inline=True)
    
    embed.set_footer(text=f"Server: {guild.name}")
    
    log_usage(interaction.user.id, 'serverinfo')
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="botinfo", description="Information about bot")
async def bot_info(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Bot Information",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    embed.add_field(name="📛 Bot name", value=bot.user.name, inline=True)
    embed.add_field(name="🆔 Bot ID", value=f"`{bot.user.id}`", inline=True)
    embed.add_field(name="📅 Bot created", value=f"<t:{int(bot.user.created_at.timestamp())}:D>", inline=True)
    
    total_members = sum(guild.member_count for guild in bot.guilds)
    total_commands = sum(len(logs) for logs in usage_log.values())
    
    embed.add_field(name="🏠 Servers", value=f"`{len(bot.guilds)}`", inline=True)
    embed.add_field(name="👥 Total members", value=f"`{total_members}`", inline=True)
    embed.add_field(name="📈 Total commands", value=f"`{total_commands}`", inline=True)
    
    latency = round(bot.latency * 1000)
    embed.add_field(name="🏓 Latency", value=f"`{latency}ms`", inline=True)
    
    embed.add_field(name="🔧 Mode", value=BOT_MODE.upper(), inline=True)
    embed.add_field(name="💾 Daily limit", value=f"`{DAILY_LIMIT_MB}MB`", inline=True)
    embed.add_field(name="🚫 Blacklist", value=f"`{len(blacklist)}` users", inline=True)
    embed.add_field(name="⭐ Premium", value=f"`{len(premium_users)}` users", inline=True)
    
    embed.add_field(name="🔢 Version", value="`2.0.0`", inline=True)
    embed.add_field(name="📚 Library", value="`discord.py`", inline=True)
    embed.add_field(name="🐍 Python", value="`3.8+`", inline=True)
    
    embed.set_footer(text=f"Bot ID: {bot.user.id}")
    
    log_usage(interaction.user.id, 'botinfo')
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="banneruser", description="Get user banner")
async def banner_user(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    
    try:
        user_info = await bot.fetch_user(target_user.id)
        
        if not user_info.banner:
            embed = discord.Embed(
                title="❌ User has no banner",
                description=f"{target_user.mention} has no banner!",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🎨 Banner of {target_user.display_name}",
            description=f"Banner of {target_user.mention}",
            color=0x0099ff,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🔗 Banner link", value=f"```{user_info.banner.url}```", inline=False)
        embed.add_field(name="👤 User", value=target_user.mention, inline=True)
        embed.add_field(name="🆔 User ID", value=f"`{target_user.id}`", inline=True)
        embed.add_field(name="👤 Requested by", value=interaction.user.mention, inline=True)
        embed.set_image(url=user_info.banner.url)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=user_info.banner.url))
        view.add_item(discord.ui.Button(label="🌐 Open Banner", style=discord.ButtonStyle.link, url=user_info.banner.url))
        
        log_usage(interaction.user.id, 'banneruser')
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error getting banner",
            description=f"Cannot get banner of {target_user.mention}: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="bannerserver", description="Get server banner")
async def banner_server(interaction: discord.Interaction):
    guild = interaction.guild
    
    if not guild.banner:
        embed = discord.Embed(
            title="❌ Server has no banner",
            description=f"Server **{guild.name}** has no banner!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"🎨 Server Banner: {guild.name}",
        description=f"Banner of server **{guild.name}**",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="🔗 Banner link", value=f"```{guild.banner.url}```", inline=False)
    embed.add_field(name="🏠 Server", value=guild.name, inline=True)
    embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="👤 Requested by", value=interaction.user.mention, inline=True)
    embed.set_image(url=guild.banner.url)
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=guild.banner.url))
    view.add_item(discord.ui.Button(label="🌐 Open Banner", style=discord.ButtonStyle.link, url=guild.banner.url))
    
    log_usage(interaction.user.id, 'bannerserver')
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="convertimage", description="Convert image format")
async def convert_image(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Blocked from use",
            description="You have been added to blacklist. Contact admin to be removed.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not IMGUR_CLIENT_ID:
        embed = discord.Embed(
            title="❌ Configuration error",
            description="ImgBB API Key not configured!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔄 Convert Image Format",
        description="**🔒 Only you can see**\nUpload image in next message to convert format!",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="⏰ Time", value="5 minutes to upload", inline=True)
    embed.add_field(name="🖼️ Supported formats", value="PNG, JPEG, WEBP", inline=True)
    embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Status", value="🟢 Waiting for image...", inline=True)
    
    view = ImageConverterView(interaction.user.id)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.attachments
    
    try:
        wait_msg = await bot.wait_for('message', timeout=300.0, check=check)
        
        if wait_msg.attachments:
            attachment = wait_msg.attachments[0]
            
            if any(attachment.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                view.original_image = attachment.url
                
                embed = discord.Embed(
                    title="✅ Image received!",
                    description=f"Received image **{attachment.filename}**\nSelect format to convert from menu below:",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="📁 File", value=attachment.filename, inline=True)
                embed.add_field(name="📏 Size", value=humanize.naturalsize(attachment.size), inline=True)
                embed.set_thumbnail(url=attachment.url)
                
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                
                try:
                    await wait_msg.delete()
                except:
                    pass
            else:
                error_embed = discord.Embed(
                    title="❌ Format not supported",
                    description=f"Only support: {', '.join(ALLOWED_EXTENSIONS)}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            error_embed = discord.Embed(
                title="❌ No image found",
                description="Please attach image when using this command",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏰ Timeout",
            description="You didn't upload image within 5 minutes!",
            color=0xffa500
        )
        await interaction.followup.send(embed=timeout_embed, ephemeral=True)

@bot.tree.command(name="backupimage", description="Backup image to database")
async def backup_image_command(interaction: discord.Interaction, image_url: str):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Blocked from use",
            description="You have been added to blacklist. Contact admin to be removed.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    try:
        if not image_url.startswith(('http://', 'https://')):
            embed = discord.Embed(
                title="❌ Invalid URL",
                description="URL must start with http:// or https://",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    embed = discord.Embed(
                        title="❌ Cannot download image",
                        description="URL doesn't return valid image!",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                image_data = await response.read()
                
                imgbb_data, error = await imgbb_uploader.upload_image(image_url, "backup_image")
                
                if error:
                    embed = discord.Embed(
                        title="❌ Backup error",
                        description=error,
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                backup_id = await backup_image(interaction.user.id, imgbb_data['url'], imgbb_data)
                
                embed = discord.Embed(
                    title="✅ Backup successful!",
                    description=f"Image backed up successfully",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="🔗 Image link", value=f"```{imgbb_data['url']}```", inline=False)
                embed.add_field(name="📦 Backup ID", value=f"`{backup_id}`", inline=True)
                embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
                embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
                embed.add_field(name="🖼️ Format", value=imgbb_data['format'].upper(), inline=True)
                embed.add_field(name="📐 Size", value=f"{imgbb_data['width']}x{imgbb_data['height']}", inline=True)
                
                embed.set_image(url=imgbb_data['url'])
                
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=imgbb_data['url']))
                view.add_item(discord.ui.Button(label="🌐 Open Image", style=discord.ButtonStyle.link, url=imgbb_data['url']))
                
                log_usage(interaction.user.id, 'backupimage')
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Backup error",
            description=f"An error occurred: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="restoreimage", description="Restore image from backup")
async def restore_image(interaction: discord.Interaction, backup_id: str):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Blocked from use",
            description="You have been added to blacklist. Contact admin to be removed.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if backup_id not in backup_data:
        embed = discord.Embed(
            title="❌ Backup ID doesn't exist",
            description="No backup found with this ID!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    backup = backup_data[backup_id]
    
    if str(interaction.user.id) != backup['user_id'] and not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="❌ No access permission",
            description="You don't have permission to access this backup!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📦 Backup Information",
        description=f"Backup ID: `{backup_id}`",
        color=0x0099ff,
        timestamp=datetime.fromisoformat(backup['timestamp'])
    )
    
    embed.add_field(name="🔗 Image link", value=f"```{backup['image_url']}```", inline=False)
    embed.add_field(name="👤 User", value=f"<@{backup['user_id']}>", inline=True)
    embed.add_field(name="⏰ Backup time", value=f"<t:{int(datetime.fromisoformat(backup['timestamp']).timestamp())}:F>", inline=True)
    
    if 'image_data' in backup:
        img_data = backup['image_data']
        embed.add_field(name="🖼️ Format", value=img_data.get('format', 'Unknown').upper(), inline=True)
        embed.add_field(name="📐 Size", value=f"{img_data.get('width', 'Unknown')}x{img_data.get('height', 'Unknown')}", inline=True)
    
    embed.set_image(url=backup['image_url'])
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=backup['image_url']))
    view.add_item(discord.ui.Button(label="🌐 Open Image", style=discord.ButtonStyle.link, url=backup['image_url']))
    
    log_usage(interaction.user.id, 'restoreimage')
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="listbackup", description="List your backups")
async def list_backup(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Blocked from use",
            description="You have been added to blacklist. Contact admin to be removed.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    user_backups = {k: v for k, v in backup_data.items() if v['user_id'] == str(interaction.user.id)}
    
    if not user_backups:
        embed = discord.Embed(
            title="📦 Backup List",
            description="You don't have any backups!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    sorted_backups = sorted(user_backups.items(), key=lambda x: x[1]['timestamp'], reverse=True)[:10]
    
    embed = discord.Embed(
        title="📦 Your Backup List",
        description=f"Total: **{len(user_backups)}** backup(s)",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    for backup_id, backup in sorted_backups:
        time = datetime.fromisoformat(backup['timestamp'])
        embed.add_field(
            name=f"🆔 {backup_id}",
            value=f"⏰ <t:{int(time.timestamp())}:R>\n🔗 [View image]({backup['image_url']})",
            inline=True
        )
    
    embed.set_footer(text="Use /restoreimage <backup_id> to restore")
    
    log_usage(interaction.user.id, 'listbackups')
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="deletebackup", description="Delete backup")
async def delete_backup(interaction: discord.Interaction, backup_id: str):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 No permission to use",
            description="You are not in whitelist. Contact admin to be added.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if backup_id not in backup_data:
        embed = discord.Embed(
            title="❌ Backup ID doesn't exist",
            description="No backup found with this ID!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    backup = backup_data[backup_id]
    
    if str(interaction.user.id) != backup['user_id'] and not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="❌ No delete permission",
            description="You don't have permission to delete this backup!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    del backup_data[backup_id]
    save_json(BACKUP_DATA_FILE, backup_data)
    
    embed = discord.Embed(
        title="✅ Backup deleted!",
        description=f"Backup `{backup_id}` deleted successfully",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="🔗 Image link", value=f"[{backup['image_url']}]({backup['image_url']})", inline=False)
    embed.add_field(name="👤 Deleted by", value=interaction.user.mention, inline=True)
    
    log_usage(interaction.user.id, 'deletebackup')
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="cleardata", description="Clear your usage data")
async def clear_data(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if user_id in user_stats:
        del user_stats[user_id]
        save_json(USER_STATS_FILE, user_stats)
    
    if user_id in usage_log:
        del usage_log[user_id]
        save_json(USAGE_LOG_FILE, usage_log)
    
    user_backups = {k: v for k, v in backup_data.items() if v['user_id'] == user_id}
    for backup_id in user_backups.keys():
        del backup_data[backup_id]
    save_json(BACKUP_DATA_FILE, backup_data)
    
    embed = discord.Embed(
        title="✅ Data cleared!",
        description="Cleared all your usage data and backups",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📊 Cleared", value="• Usage statistics\n• Command history\n• Image backups", inline=False)
    embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping_command(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: **{latency}ms**",
        color=0x00ff00 if latency < 100 else 0xffa500 if latency < 200 else 0xff0000,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Status", value="✅ Good" if latency < 100 else "⚠️ Average" if latency < 200 else "❌ High", inline=True)
    embed.add_field(name="🏠 Servers", value=f"`{len(bot.guilds)}`", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="laylinkanhdiscord", description="Get image link from Discord CDN (fast)")
async def lay_link_anh_discord(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 No permission to use",
            description="You are not in whitelist. Contact admin to be added.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="⚡ Get Discord CDN Link",
        description="**🔒 Only you can see**\nUpload image in 10 seconds to get link!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="⏰ Time", value="10 seconds to upload", inline=True)
    embed.add_field(name="⚡ Speed", value="Discord CDN link - very fast", inline=True)
    embed.add_field(name="👤 Uploader", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Status", value="🟢 Waiting for image...", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.attachments
    
    try:
        wait_msg = await bot.wait_for('message', timeout=10.0, check=check)
        
        if wait_msg.attachments:
            attachments = [att for att in wait_msg.attachments if any(
                att.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS
            )]
            
            if not attachments:
                embed = discord.Embed(
                    title="❌ No valid images",
                    description=f"No images found with supported formats ({', '.join(ALLOWED_EXTENSIONS)})",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            view = discord.ui.View()
            links_text = ""
            
            for i, attachment in enumerate(attachments, 1):
                links_text += f"{i}. **{attachment.filename}**\n```{attachment.url}```\n"
                view.add_item(discord.ui.Button(
                    label=f"📋 Image {i}",
                    style=discord.ButtonStyle.link,
                    url=attachment.url
                ))
            
            result_embed = discord.Embed(
                title=f"✅ Got {len(attachments)} links!",
                description=f"**{interaction.user.mention}** - Discord CDN Links",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            result_embed.add_field(name="🔗 Link list", value=links_text[:1024], inline=False)
            result_embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
            result_embed.add_field(name="📅 Date", value=f"<t:{int(datetime.now().timestamp())}:D>", inline=True)
            result_embed.add_field(name="👤 Uploader", value=interaction.user.mention, inline=True)
            result_embed.set_thumbnail(url=SUCCESS_GIF)
            
            log_usage(interaction.user.id, 'laylinkanhdiscord')
            
            await interaction.followup.send(embed=result_embed, view=view, ephemeral=True)
            
            try:
                await wait_msg.delete()
            except:
                pass
            
        else:
            embed = discord.Embed(
                title="❌ No images found",
                description="Please attach images when using this command",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="⏰ Timeout",
            description="You didn't upload image within 10 seconds!",
            color=0xffa500
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Unknown error",
            description=f"An error occurred: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="layiduser", description="Get user Discord ID")
async def lay_id_discord(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    
    embed = discord.Embed(
        title="🆔 Discord ID",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="👤 User", value=f"{target_user.mention}", inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{target_user.id}`", inline=True)
    embed.add_field(name="📛 Tag", value=f"`{target_user.name}#{target_user.discriminator}`", inline=True)
    embed.add_field(name="📅 Account created", value=f"<t:{int(target_user.created_at.timestamp())}:D>", inline=True)
    embed.add_field(name="👤 Requested by", value=interaction.user.mention, inline=True)
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    log_usage(interaction.user.id, 'layiduser')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="laylinklogoprofile", description="Get profile picture link")
async def lay_link_logo_profile(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    
    embed = discord.Embed(
        title="🖼️ Profile Picture",
        description=f"Profile picture of {target_user.mention}",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="🔗 Image link", value=f"```{target_user.display_avatar.url}```", inline=False)
    embed.add_field(name="👤 User", value=target_user.mention, inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{target_user.id}`", inline=True)
    embed.add_field(name="👤 Requested by", value=interaction.user.mention, inline=True)
    embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
    embed.set_image(url=target_user.display_avatar.url)
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=target_user.display_avatar.url))
    view.add_item(discord.ui.Button(label="🌐 Open Image", style=discord.ButtonStyle.link, url=target_user.display_avatar.url))
    
    log_usage(interaction.user.id, 'laylinklogoprofile')
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="laylogoserver", description="Get server logo from your server list")
async def lay_logo_server(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 No permission to use",
            description="You are not in whitelist. Contact admin to be added.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    user_guilds = [guild for guild in bot.guilds if guild.get_member(interaction.user.id)]
    
    if not user_guilds:
        embed = discord.Embed(
            title="❌ No servers found",
            description="You are not in any servers where bot is active!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    guilds_with_icon = [guild for guild in user_guilds if guild.icon]
    
    if not guilds_with_icon:
        embed = discord.Embed(
            title="❌ No servers have logo",
            description="No servers with logo found in your server list!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏠 Select Server To Get Logo",
        description=f"**🔒 Only you can see**\nSelect server from list below to get logo!",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📊 Total servers", value=f"**{len(user_guilds)}** servers you joined", inline=True)
    embed.add_field(name="🖼️ Servers with logo", value=f"**{len(guilds_with_icon)}** servers with logo", inline=True)
    embed.add_field(name="⏰ Time", value="60 seconds to select", inline=True)
    embed.add_field(name="👤 Requester", value=interaction.user.mention, inline=True)
    
    view = ServerSelectView(guilds_with_icon, "logo")
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="laylinklogoserver", description="Get server logo link from your server list")
async def lay_link_logo_server(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 No permission to use",
            description="You are not in whitelist. Contact admin to be added.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    user_guilds = [guild for guild in bot.guilds if guild.get_member(interaction.user.id)]
    
    if not user_guilds:
        embed = discord.Embed(
            title="❌ No servers found",
            description="You are not in any servers where bot is active!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    guilds_with_icon = [guild for guild in user_guilds if guild.icon]
    
    if not guilds_with_icon:
        embed = discord.Embed(
            title="❌ No servers have logo",
            description="No servers with logo found in your server list!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔗 Select Server To Get Logo Link",
        description=f"**🔒 Only you can see**\nSelect server from list below to get logo link!",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📊 Total servers", value=f"**{len(user_guilds)}** servers you joined", inline=True)
    embed.add_field(name="🖼️ Servers with logo", value=f"**{len(guilds_with_icon)}** servers with logo", inline=True)
    embed.add_field(name="⏰ Time", value="60 seconds to select", inline=True)
    embed.add_field(name="👤 Requester", value=interaction.user.mention, inline=True)
    
    view = ServerSelectView(guilds_with_icon, "link")
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="stats", description="Your usage statistics")
async def stats_command(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    embed = discord.Embed(
        title="📊 Usage Statistics",
        description=f"Statistics of {interaction.user.mention}",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    today_usage = get_user_daily_usage(interaction.user.id)
    remaining = get_remaining_daily_usage(interaction.user.id)
    daily_limit = get_daily_limit(interaction.user.id)
    usage_percentage = (today_usage / daily_limit) * 100 if daily_limit > 0 else 0
    
    embed.add_field(
        name="💾 Today's usage",
        value=f"**Used:** {humanize.naturalsize(today_usage)}\n**Remaining:** {humanize.naturalsize(remaining)}\n**Limit:** {humanize.naturalsize(daily_limit)}\n**Ratio:** {usage_percentage:.1f}%",
        inline=False
    )
    
    current_tcoin = get_user_tcoin(interaction.user.id)
    embed.add_field(name="🪙 Current Tcoin", value=f"**{current_tcoin}** Tcoin", inline=True)
    
    upload_attempts = get_daily_limit_count(interaction.user.id, 'upload')
    link_attempts = get_daily_limit_count(interaction.user.id, 'link')
    embed.add_field(name="📸 Uploads today", value=f"**{upload_attempts}/10** times", inline=True)
    embed.add_field(name="🔗 Links today", value=f"**{link_attempts}/5** times", inline=True)
    
    if user_id in usage_log:
        recent_usage = usage_log[user_id][-10:]
        usage_text = ""
        for usage in reversed(recent_usage):
            time = datetime.fromisoformat(usage['timestamp'])
            size = f" - {humanize.naturalsize(usage['file_size'])}" if usage['file_size'] > 0 else ""
            usage_text += f"• `{usage['command']}`{size} - <t:{int(time.timestamp())}:R>\n"
        
        embed.add_field(name="📝 Recent history", value=usage_text or "No history", inline=False)
    
    total_commands = len(usage_log.get(user_id, []))
    embed.add_field(name="📈 Total commands used", value=f"**{total_commands}** commands", inline=True)
    
    user_backups = sum(1 for backup in backup_data.values() if backup['user_id'] == user_id)
    embed.add_field(name="📦 Backups", value=f"**{user_backups}** backup(s)", inline=True)
    
    status = "✅ Allowed" if is_authorized(interaction.user.id) else "❌ Blocked"
    embed.add_field(name="🔐 Status", value=status, inline=True)
    
    premium_status = "⭐ PREMIUM" if is_premium(interaction.user.id) else "🔹 STANDARD"
    embed.add_field(name="💎 Account type", value=premium_status, inline=True)
    
    embed.add_field(name="📅 Statistics date", value=f"<t:{int(datetime.now().timestamp())}:D>", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="userinfo", description="Detailed information about user")
async def userinfo_command(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    await interaction.response.send_message(embed=get_user_info_embed(target_user), ephemeral=True)

@bot.tree.command(name="report", description="Report bug or suggestion for bot")
async def report_command(interaction: discord.Interaction, issue: str, description: str):
    if not REPORT_CHANNEL_ID:
        embed = discord.Embed(
            title="❌ Configuration error",
            description="Report channel not configured!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    try:
        report_channel = bot.get_channel(int(REPORT_CHANNEL_ID))
        if not report_channel:
            embed = discord.Embed(
                title="❌ Report channel not found",
                description="Report channel doesn't exist!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        report_embed = discord.Embed(
            title="📢 NEW BUG REPORT",
            description=f"**Issue:** {issue}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        
        report_embed.add_field(name="📝 Description", value=description, inline=False)
        report_embed.add_field(name="👤 Reporter", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
        report_embed.add_field(name="🏠 Server", value=f"{interaction.guild.name} (`{interaction.guild.id}`)", inline=True)
        report_embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
        
        await report_channel.send(embed=report_embed)
        
        success_embed = discord.Embed(
            title="✅ Report sent!",
            description="Thank you for reporting the bug. We will check and fix as soon as possible!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        success_embed.add_field(name="📢 Issue", value=issue, inline=False)
        success_embed.add_field(name="📝 Description", value=description[:500] + "..." if len(description) > 500 else description, inline=False)
        
        await interaction.response.send_message(embed=success_embed, ephemeral=True)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Error sending report",
            description=f"An error occurred: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# ==================== INTERACTION HANDLING ====================

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get('custom_id', '')
        
        if custom_id == "report_bug":
            modal = discord.ui.Modal(title="📢 Report Bug")
            modal.add_item(discord.ui.TextInput(
                label="Issue",
                placeholder="Briefly describe the issue...",
                custom_id="issue",
                style=discord.TextStyle.short,
                max_length=100
            ))
            modal.add_item(discord.ui.TextInput(
                label="Detailed description",
                placeholder="Detailed description about bug or suggestion...",
                custom_id="description",
                style=discord.TextStyle.paragraph,
                max_length=1000
            ))
            
            async def modal_callback(interaction: discord.Interaction):
                issue = interaction.data['components'][0]['components'][0]['value']
                description = interaction.data['components'][1]['components'][0]['value']
                
                if REPORT_CHANNEL_ID:
                    try:
                        report_channel = bot.get_channel(int(REPORT_CHANNEL_ID))
                        if report_channel:
                            report_embed = discord.Embed(
                                title="📢 NEW BUG REPORT",
                                description=f"**Issue:** {issue}",
                                color=0xff0000,
                                timestamp=datetime.now()
                            )
                            
                            report_embed.add_field(name="📝 Description", value=description, inline=False)
                            report_embed.add_field(name="👤 Reporter", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
                            report_embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
                            
                            await report_channel.send(embed=report_embed)
                            
                            success_embed = discord.Embed(
                                title="✅ Report sent!",
                                description="Thank you for reporting the bug!",
                                color=0x00ff00
                            )
                            await interaction.response.send_message(embed=success_embed, ephemeral=True)
                    except Exception as e:
                        error_embed = discord.Embed(
                            title="❌ Error sending report",
                            description=str(e),
                            color=0xff0000
                        )
                        await interaction.response.send_message(embed=error_embed, ephemeral=True)
            
            modal.callback = modal_callback
            await interaction.response.send_modal(modal)
        
        elif custom_id == "upload_tcoin":
            if not can_earn_tcoin(interaction.user.id, 'upload'):
                embed = discord.Embed(
                    title="❌ Limit reached",
                    description="You have reached the 10 uploads/day limit!",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📸 Upload Image To Get Tcoin",
                description="Upload 1 image to get +1 Tcoin!",
                color=0xffd700,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif custom_id == "link_tcoin":
            if not can_earn_tcoin(interaction.user.id, 'link'):
                embed = discord.Embed(
                    title="❌ Limit reached",
                    description="You have reached the 5 links/day limit!",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            tcoin_amount = random.randint(2, 5)
            add_user_tcoin(interaction.user.id, tcoin_amount)
            update_daily_limit_count(interaction.user.id, 'link')
            
            embed = discord.Embed(
                title="🔗 Link Completed Successfully!",
                description=f"You received **+{tcoin_amount} Tcoin**!",
                color=0xffd700,
                timestamp=datetime.now()
            )
            
            embed.add_field(name="💰 Current Tcoin", value=f"**{get_user_tcoin(interaction.user.id)}** Tcoin", inline=True)
            embed.add_field(name="🔗 Links today", value=f"**{get_daily_limit_count(interaction.user.id, 'link')}/5**", inline=True)
            embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="🌐 Visit Website",
                style=discord.ButtonStyle.link,
                url=TCOIN_WEB_URL
            ))
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif custom_id == "buy_premium":
            await buy_premium(interaction)

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(
            title="❌ Missing permissions",
            description="You don't have permission to use this command!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.CommandOnCooldown):
        embed = discord.Embed(
            title="⏰ Cooldown",
            description=f"Please try again after {error.retry_after:.1f} seconds!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        print(f"Application error: {error}")
        embed = discord.Embed(
            title="❌ Unknown error",
            description="An error occurred while executing command!",
            color=0xff0000
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

@tasks.loop(hours=24)
async def cleanup_old_data():
    try:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        for user_id, stats in user_stats.items():
            user_stats[user_id] = {date: size for date, size in stats.items() 
                                 if datetime.strptime(date, '%Y-%m-%d') >= thirty_days_ago}
        
        save_json(USER_STATS_FILE, user_stats)
        print("✅ Cleaned up old user stats")
        
    except Exception as e:
        print(f"❌ Error cleaning up data: {e}")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ ERROR: DISCORD_TOKEN not found!")
        exit(1)
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ ERROR: {e}")
