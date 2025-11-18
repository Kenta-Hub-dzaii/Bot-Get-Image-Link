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

# Load biến môi trường
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

def load_json(filename):
    """Load dữ liệu từ file JSON"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(filename, data):
    """Lưu dữ liệu vào file JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Load dữ liệu
whitelist_data = load_json(WHITELIST_FILE)
blacklist_data = load_json(BLACKLIST_FILE)
violation_log_data = load_json(VIOLATION_LOG_FILE)
usage_log = load_json(USAGE_LOG_FILE)
user_stats = load_json(USER_STATS_FILE)
server_settings = load_json(SERVER_SETTINGS_FILE)
backup_data = load_json(BACKUP_DATA_FILE)
premium_users = load_json(PREMIUM_USERS_FILE)
tcoin_data = load_json(TCOIN_DATA_FILE)

# Khởi tạo dữ liệu mặc định
whitelist = whitelist_data.get('users', []) if isinstance(whitelist_data, dict) else whitelist_data
blacklist = blacklist_data.get('users', []) if isinstance(blacklist_data, dict) else blacklist_data
violation_log = violation_log_data.get('logs', []) if isinstance(violation_log_data, dict) else violation_log_data
premium_users = premium_users.get('users', []) if isinstance(premium_users, dict) else premium_users
tcoin_users = tcoin_data.get('users', {}) if isinstance(tcoin_data, dict) else tcoin_data
daily_limits = tcoin_data.get('daily_limits', {}) if isinstance(tcoin_data, dict) else {}

# Cấu hình từ .env
BOT_MODE = os.getenv('BOT_MODE', 'whitelist')
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
        """Upload ảnh từ URL lên ImgBB"""
        if not self.api_key:
            return None, "ImgBB API Key chưa được cấu hình"
        
        try:
            # Tải ảnh từ URL
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return None, f"Không thể tải ảnh từ URL: {response.status}"
                    
                    image_data = await response.read()
                    
                    if len(image_data) > MAX_FILE_SIZE_BYTES:
                        return None, f"Ảnh quá lớn (giới hạn {MAX_FILE_SIZE_MB}MB)"
                    
                    # Chuyển sang base64
                    base64_image = base64.b64encode(image_data).decode()
                    
                    # Upload lên ImgBB
                    form_data = aiohttp.FormData()
                    form_data.add_field('key', self.api_key)
                    form_data.add_field('image', base64_image)
                    if filename:
                        form_data.add_field('name', filename)
                    
                    async with session.post(self.base_url, data=form_data) as upload_response:
                        result = await upload_response.json()
                        print(f"ImgBB Response: {result}")  # Debug log
                        
                        if upload_response.status == 200 and result.get('success', False):
                            data = result['data']
                            
                            # Xử lý response an toàn
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
            return None, "Timeout khi kết nối đến ImgBB"
        except Exception as e:
            return None, f"Lỗi upload: {str(e)}"
    
    def _get_file_extension(self, data):
        """Lấy định dạng file từ response data"""
        # Thử các trường khác nhau có thể chứa thông tin định dạng
        if data.get('extension'):
            return data['extension']
        elif data.get('image', {}).get('extension'):
            return data['image']['extension']
        elif data.get('url'):
            # Lấy extension từ URL
            url = data['url']
            if '.' in url:
                return url.split('.')[-1].lower()
        return 'unknown'
# Khởi tạo ImgBB Uploader
imgbb_uploader = ImgBBUploader(IMGUR_CLIENT_ID) if IMGUR_CLIENT_ID else None

def is_authorized(user_id):
    """Kiểm tra user có được phép sử dụng bot không"""
    user_id = str(user_id)
    
    if BOT_MODE.lower() == 'whitelist':
        if not whitelist:
            return True
        return user_id in whitelist
    else:
        if user_id in blacklist:
            return False
        return True

def is_premium(user_id):
    """Kiểm tra user có premium không"""
    user_id = str(user_id)
    return user_id in premium_users

def is_admin(user_id):
    """Kiểm tra user có phải admin không"""
    return user_id in ADMIN_USER_IDS

def get_user_tcoin(user_id):
    """Lấy số Tcoin của user"""
    user_id = str(user_id)
    return tcoin_users.get(user_id, 0)

def add_user_tcoin(user_id, amount):
    """Thêm Tcoin cho user"""
    user_id = str(user_id)
    if user_id not in tcoin_users:
        tcoin_users[user_id] = 0
    tcoin_users[user_id] += amount
    save_json(TCOIN_DATA_FILE, {'users': tcoin_users, 'daily_limits': daily_limits})

def get_daily_limit_count(user_id, limit_type):
    """Lấy số lần đã sử dụng trong ngày"""
    user_id = str(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    key = f"{user_id}_{limit_type}_{today}"
    return daily_limits.get(key, 0)

def update_daily_limit_count(user_id, limit_type):
    """Cập nhật số lần đã sử dụng trong ngày"""
    user_id = str(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    key = f"{user_id}_{limit_type}_{today}"
    daily_limits[key] = daily_limits.get(key, 0) + 1
    save_json(TCOIN_DATA_FILE, {'users': tcoin_users, 'daily_limits': daily_limits})

def can_earn_tcoin(user_id, limit_type):
    """Kiểm tra user có thể nhận Tcoin không"""
    max_attempts = 10 if limit_type == 'upload' else 5
    return get_daily_limit_count(user_id, limit_type) < max_attempts

def get_user_daily_usage(user_id):
    """Lấy dung lượng sử dụng trong ngày của user"""
    user_id = str(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if user_id not in user_stats:
        user_stats[user_id] = {}
    
    if today not in user_stats[user_id]:
        user_stats[user_id][today] = 0
    
    return user_stats[user_id][today]

def update_user_daily_usage(user_id, size_bytes):
    """Cập nhật dung lượng sử dụng của user"""
    user_id = str(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if user_id not in user_stats:
        user_stats[user_id] = {}
    
    if today not in user_stats[user_id]:
        user_stats[user_id][today] = 0
    
    user_stats[user_id][today] += size_bytes
    save_json(USER_STATS_FILE, user_stats)

def get_remaining_daily_usage(user_id):
    """Lấy dung lượng còn lại trong ngày"""
    used = get_user_daily_usage(user_id)
    remaining = DAILY_LIMIT_BYTES - used
    return max(0, remaining)

def can_upload(user_id, file_size):
    """Kiểm tra user có thể upload file không"""
    if is_premium(user_id):
        return True
    return get_remaining_daily_usage(user_id) >= file_size

def get_daily_limit(user_id):
    """Lấy giới hạn dung lượng hàng ngày"""
    if is_premium(user_id):
        return DAILY_LIMIT_BYTES * 5  # Premium users có giới hạn gấp 5 lần
    return DAILY_LIMIT_BYTES

async def log_violation(user: discord.User, attachment_url: str, reason: str):
    """Ghi log vi phạm"""
    violation_data = {
        'user_id': str(user.id),
        'user_name': f"{user.name}#{user.discriminator}",
        'attachment_url': attachment_url,
        'reason': reason,
        'timestamp': datetime.now().isoformat()
    }
    
    violation_log.append(violation_data)
    save_json(VIOLATION_LOG_FILE, {'logs': violation_log})
    
    # Tự động thêm vào blacklist
    if str(user.id) not in blacklist:
        blacklist.append(str(user.id))
        save_json(BLACKLIST_FILE, {'users': blacklist})
    
    # Gửi thông báo đến channel log
    if VIOLATION_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(VIOLATION_CHANNEL_ID))
            if channel:
                embed = discord.Embed(
                    title="🚨 VI PHẠM NỘI DUNG - ĐÃ TỰ ĐỘNG BLACKLIST",
                    description=f"User đã bị tự động thêm vào blacklist",
                    color=0xff0000,
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="👤 User vi phạm", value=f"{user.mention} (`{user.id}`)", inline=False)
                embed.add_field(name="📄 Lý do", value=reason, inline=False)
                embed.add_field(name="🔗 Link ảnh", value=f"[Xem ảnh]({attachment_url})", inline=False)
                embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
                
                await channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Lỗi khi gửi log vi phạm: {e}")

def log_usage(user_id, command: str, file_size: int = 0):
    """Ghi log sử dụng"""
    user_id = str(user_id)
    timestamp = datetime.now().isoformat()
    
    if user_id not in usage_log:
        usage_log[user_id] = []
    
    usage_log[user_id].append({
        'command': command,
        'file_size': file_size,
        'timestamp': timestamp
    })
    
    # Giữ tối đa 100 bản ghi gần nhất
    usage_log[user_id] = usage_log[user_id][-100:]
    save_json(USAGE_LOG_FILE, usage_log)

async def backup_image(user_id, image_url, image_data):
    """Backup ảnh vào database"""
    backup_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    backup_data[backup_id] = {
        'user_id': str(user_id),
        'image_url': image_url,
        'image_data': image_data,
        'timestamp': datetime.now().isoformat(),
        'backup_id': backup_id
    }
    
    save_json(BACKUP_DATA_FILE, backup_data)
    
    # Gửi backup đến channel nếu được cấu hình
    if AUTO_BACKUP and BACKUP_CHANNEL_IDS:
        for channel_id in BACKUP_CHANNEL_IDS:
            try:
                channel = bot.get_channel(channel_id)
                if channel:
                    embed = discord.Embed(
                        title="📦 BACKUP ẢNH",
                        color=0x00ff00,
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="👤 User", value=f"<@{user_id}>", inline=True)
                    embed.add_field(name="🆔 Backup ID", value=backup_id, inline=True)
                    embed.add_field(name="🔗 URL", value=f"[Link ảnh]({image_url})", inline=True)
                    embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
                    
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"❌ Lỗi khi backup ảnh đến channel {channel_id}: {e}")
    
    return backup_id

def get_user_info_embed(user: discord.User):
    """Tạo embed thông tin user"""
    user_id = str(user.id)
    
    embed = discord.Embed(
        title=f"👤 Thông Tin {user.display_name}",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="📛 Tên đầy đủ", value=f"{user.name}#{user.discriminator}", inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{user.id}`", inline=True)
    embed.add_field(name="📅 Tạo tài khoản", value=f"<t:{int(user.created_at.timestamp())}:D>", inline=True)
    
    # Thống kê sử dụng
    today_usage = get_user_daily_usage(user.id)
    remaining = get_remaining_daily_usage(user.id)
    daily_limit = get_daily_limit(user.id)
    
    embed.add_field(
        name="📊 Dung lượng hôm nay",
        value=f"**Đã dùng:** {humanize.naturalsize(today_usage)}\n**Còn lại:** {humanize.naturalsize(remaining)}\n**Giới hạn:** {humanize.naturalsize(daily_limit)}",
        inline=False
    )
    
    # Tcoin info
    tcoin_amount = get_user_tcoin(user.id)
    embed.add_field(name="🪙 Tcoin", value=f"**{tcoin_amount}** Tcoin", inline=True)
    
    # Trạng thái
    status = "✅ Được phép sử dụng" if is_authorized(user.id) else "❌ Bị chặn"
    embed.add_field(name="🔐 Trạng thái", value=status, inline=True)
    
    # Premium status
    premium_status = "⭐ PREMIUM" if is_premium(user.id) else "🔹 STANDARD"
    embed.add_field(name="💎 Loại tài khoản", value=premium_status, inline=True)
    
    # Chế độ bot
    embed.add_field(name="🔧 Chế độ bot", value=BOT_MODE.upper(), inline=True)
    
    # Tổng lệnh đã sử dụng
    total_commands = len(usage_log.get(user_id, []))
    embed.add_field(name="📈 Tổng lệnh", value=f"**{total_commands}** lệnh", inline=True)
    
    embed.set_footer(text=f"User ID: {user.id}")
    
    return embed

def add_report_button(embed):
    """Thêm nút report vào embed"""
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
        for guild in guilds[:25]:  # Giới hạn 25 server
            guild_name = guild.name[:25] + "..." if len(guild.name) > 25 else guild.name
            options.append(
                discord.SelectOption(
                    label=guild_name,
                    value=str(guild.id),
                    description=f"Thành viên: {guild.member_count}",
                    emoji="🏠"
                )
            )
        
        placeholder = "Chọn server để lấy logo..." if command_type == "logo" else "Chọn server để lấy link logo..."
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
            embed = discord.Embed(title="❌ Không tìm thấy server", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Lấy logo server
        server_icon = guild.icon
        if not server_icon:
            embed = discord.Embed(
                title="❌ Server không có logo",
                description=f"Server **{guild.name}** không có logo!",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Tạo embed kết quả
        if self.command_type == "logo":
            embed = discord.Embed(
                title=f"🏠 Logo Server: {guild.name}",
                description=f"Logo của server **{guild.name}**",
                color=0x0099ff,
                timestamp=datetime.now()
            )
            embed.set_image(url=server_icon.url)
        else:
            embed = discord.Embed(
                title=f"🔗 Link Logo Server: {guild.name}",
                description=f"Link logo của server **{guild.name}**",
                color=0x0099ff,
                timestamp=datetime.now()
            )
            embed.add_field(name="🔗 Link logo", value=f"```{server_icon.url}```", inline=False)
        
        # Thông tin server
        embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👥 Thành viên", value=f"`{guild.member_count}`", inline=True)
        embed.add_field(name="📅 Tạo server", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="👤 Yêu cầu bởi", value=interaction.user.mention, inline=True)
        embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
        
        # Tạo view với nút
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=server_icon.url))
        view.add_item(discord.ui.Button(label="🌐 Mở Ảnh", style=discord.ButtonStyle.link, url=server_icon.url))
        
        log_usage(interaction.user.id, f'lay{"logo" if self.command_type == "logo" else "linklogo"}server')
        
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
        placeholder="Chọn định dạng muốn chuyển đổi...",
        options=[
            discord.SelectOption(label="PNG", value="png", description="Chuyển sang PNG", emoji="🖼️"),
            discord.SelectOption(label="JPEG", value="jpeg", description="Chuyển sang JPEG", emoji="📷"),
            discord.SelectOption(label="WEBP", value="webp", description="Chuyển sang WEBP", emoji="🌐"),
        ]
    )
    async def convert_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không thể sử dụng menu này!", ephemeral=True)
            return
        
        format_type = select.values[0]
        
        if not self.original_image:
            await interaction.response.send_message("❌ Không tìm thấy ảnh gốc!", ephemeral=True)
            return
        
        try:
            # Hiển thị thông báo đang xử lý
            await interaction.response.defer(ephemeral=True)
            
            # Upload ảnh gốc lên ImgBB và để ImgBB xử lý chuyển đổi
            imgbb_data, error = await imgbb_uploader.upload_image(self.original_image, f"converted_image.{format_type}")
            
            if error:
                await interaction.followup.send(f"❌ Lỗi khi chuyển đổi: {error}", ephemeral=True)
                return
            
            # Tạo embed kết quả
            embed = discord.Embed(
                title="✅ Chuyển đổi thành công!",
                description=f"Đã chuyển ảnh sang định dạng **{format_type.upper()}**",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            embed.add_field(name="🔗 Link ảnh mới", value=f"```{imgbb_data['url']}```", inline=False)
            embed.add_field(name="🖼️ Định dạng", value=format_type.upper(), inline=True)
            embed.add_field(name="👤 Người dùng", value=interaction.user.mention, inline=True)
            embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=imgbb_data['url']))
            view.add_item(discord.ui.Button(label="🌐 Mở Ảnh", style=discord.ButtonStyle.link, url=imgbb_data['url']))
            
            log_usage(interaction.user.id, f'convert_to_{format_type}')
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi khi chuyển đổi: {str(e)}", ephemeral=True)

@bot.event
async def on_ready():
    print(f'✅ {bot.user} đã kết nối thành công!')
    print(f'📊 Đang hoạt động trên {len(bot.guilds)} server')
    print(f'🔧 Chế độ: {BOT_MODE.upper()}')
    print(f'💾 Giới hạn: {DAILY_LIMIT_MB}MB/ngày')
    print(f'📋 Whitelist: {len(whitelist)} users')
    print(f'🚫 Blacklist: {len(blacklist)} users')
    print(f'⭐ Premium users: {len(premium_users)} users')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Đã đồng bộ {len(synced)} slash command(s)')
    except Exception as e:
        print(f'❌ Lỗi đồng bộ commands: {e}')

    # Set trạng thái bot
    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers | /help")
    await bot.change_presence(activity=activity)
    
    # KHỞI ĐỘNG TASK
    if not cleanup_old_data.is_running():
        cleanup_old_data.start()
        print("✅ Đã khởi động task dọn dẹp dữ liệu")

# ==================== COMMANDS QUẢN LÝ ====================

@bot.tree.command(name="addwhitelist", description="Thêm user vào whitelist (chỉ admin)")
@app_commands.default_permissions(administrator=True)
async def add_whitelist(interaction: discord.Interaction, user: discord.User):
    """Thêm user vào whitelist"""
    user_id = str(user.id)
    
    if user_id in whitelist:
        embed = discord.Embed(title="❌ User đã có trong whitelist", color=0xff0000)
    else:
        whitelist.append(user_id)
        save_json(WHITELIST_FILE, {'users': whitelist})
        embed = discord.Embed(
            title="✅ Đã thêm vào whitelist",
            description=f"Đã thêm {user.mention} vào whitelist!",
            color=0x00ff00
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removewhitelist", description="Xóa user khỏi whitelist (chỉ admin)")
@app_commands.default_permissions(administrator=True)
async def remove_whitelist(interaction: discord.Interaction, user: discord.User):
    """Xóa user khỏi whitelist"""
    user_id = str(user.id)
    
    if user_id in whitelist:
        whitelist.remove(user_id)
        save_json(WHITELIST_FILE, {'users': whitelist})
        embed = discord.Embed(
            title="✅ Đã xóa khỏi whitelist",
            description=f"Đã xóa {user.mention} khỏi whitelist!",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(title="❌ User không có trong whitelist", color=0xff0000)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addblacklist", description="Thêm user vào blacklist (chỉ admin)")
@app_commands.default_permissions(administrator=True)
async def add_blacklist(interaction: discord.Interaction, user: discord.User):
    """Thêm user vào blacklist"""
    user_id = str(user.id)
    
    if user_id in blacklist:
        embed = discord.Embed(title="❌ User đã có trong blacklist", color=0xff0000)
    else:
        blacklist.append(user_id)
        save_json(BLACKLIST_FILE, {'users': blacklist})
        embed = discord.Embed(
            title="✅ Đã thêm vào blacklist",
            description=f"Đã thêm {user.mention} vào blacklist!",
            color=0x00ff00
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removeblacklist", description="Gỡ user khỏi blacklist (chỉ admin)")
@app_commands.default_permissions(administrator=True)
async def remove_blacklist(interaction: discord.Interaction, user: discord.User):
    """Gỡ user khỏi blacklist"""
    user_id = str(user.id)
    
    if user_id in blacklist:
        blacklist.remove(user_id)
        save_json(BLACKLIST_FILE, {'users': blacklist})
        embed = discord.Embed(
            title="✅ Đã gỡ khỏi blacklist",
            description=f"Đã gỡ {user.mention} khỏi blacklist!",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(title="❌ User không có trong blacklist", color=0xff0000)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="whitelist", description="Xem danh sách whitelist (chỉ admin)")
@app_commands.default_permissions(administrator=True)
async def show_whitelist(interaction: discord.Interaction):
    """Hiển thị danh sách whitelist"""
    if not whitelist:
        embed = discord.Embed(title="📋 Whitelist", description="Whitelist đang trống!", color=0xffa500)
    else:
        users_list = []
        for user_id in whitelist[:20]:  # Hiển thị tối đa 20 user
            try:
                user = await bot.fetch_user(int(user_id))
                users_list.append(f"{user.mention} (`{user_id}`)")
            except:
                users_list.append(f"`{user_id}`")
        
        embed = discord.Embed(title="📋 Whitelist", description="\n".join(users_list), color=0x00ff00)
        embed.set_footer(text=f"Tổng cộng: {len(whitelist)} users")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="blacklist", description="Xem danh sách blacklist (chỉ admin)")
@app_commands.default_permissions(administrator=True)
async def show_blacklist(interaction: discord.Interaction):
    """Hiển thị danh sách blacklist"""
    if not blacklist:
        embed = discord.Embed(title="🚫 Blacklist", description="Blacklist đang trống!", color=0xffa500)
    else:
        users_list = []
        for user_id in blacklist[:20]:  # Hiển thị tối đa 20 user
            try:
                user = await bot.fetch_user(int(user_id))
                users_list.append(f"{user.mention} (`{user_id}`)")
            except:
                users_list.append(f"`{user_id}`")
        
        embed = discord.Embed(title="🚫 Blacklist", description="\n".join(users_list), color=0xff0000)
        embed.set_footer(text=f"Tổng cộng: {len(blacklist)} users")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addpremium", description="Thêm user vào premium (chỉ admin)")
@app_commands.default_permissions(administrator=True)
async def add_premium(interaction: discord.Interaction, user: discord.User):
    """Thêm user vào premium"""
    user_id = str(user.id)
    
    if user_id in premium_users:
        embed = discord.Embed(title="❌ User đã có trong premium", color=0xff0000)
    else:
        premium_users.append(user_id)
        save_json(PREMIUM_USERS_FILE, {'users': premium_users})
        embed = discord.Embed(
            title="⭐ Đã thêm vào premium",
            description=f"Đã thêm {user.mention} vào danh sách premium!",
            color=0xffd700
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removepremium", description="Xóa user khỏi premium (chỉ admin)")
@app_commands.default_permissions(administrator=True)
async def remove_premium(interaction: discord.Interaction, user: discord.User):
    """Xóa user khỏi premium"""
    user_id = str(user.id)
    
    if user_id in premium_users:
        premium_users.remove(user_id)
        save_json(PREMIUM_USERS_FILE, {'users': premium_users})
        embed = discord.Embed(
            title="✅ Đã xóa khỏi premium",
            description=f"Đã xóa {user.mention} khỏi danh sách premium!",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(title="❌ User không có trong premium", color=0xff0000)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== HỆ THỐNG TCOIN ====================

@bot.tree.command(name="gettcoin", description="Nhận Tcoin miễn phí")
async def get_tcoin(interaction: discord.Interaction):
    """Nhận Tcoin miễn phí"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🪙 Nhận Tcoin Miễn Phí",
        description="Chọn phương thức nhận Tcoin bên dưới:",
        color=0xffd700,
        timestamp=datetime.now()
    )
    
    # Thông tin Tcoin hiện tại
    current_tcoin = get_user_tcoin(interaction.user.id)
    embed.add_field(name="💰 Tcoin hiện tại", value=f"**{current_tcoin}** Tcoin", inline=True)
    
    # Giới hạn còn lại
    upload_attempts = get_daily_limit_count(interaction.user.id, 'upload')
    link_attempts = get_daily_limit_count(interaction.user.id, 'link')
    
    embed.add_field(name="📸 Upload ảnh", value=f"**{10 - upload_attempts}/10** lần còn", inline=True)
    embed.add_field(name="🔗 Vượt link", value=f"**{5 - link_attempts}/5** lần còn", inline=True)
    
    # Tạo view với các nút
    view = discord.ui.View()
    
    # Nút upload ảnh
    upload_button = discord.ui.Button(
        label="📸 Upload Ảnh (+1 Tcoin)",
        style=discord.ButtonStyle.primary,
        custom_id="upload_tcoin"
    )
    
    # Nút vượt link
    link_button = discord.ui.Button(
        label="🔗 Vượt Link (+2-5 Tcoin)",
        style=discord.ButtonStyle.success,
        custom_id="link_tcoin"
    )
    
    # Nút mua premium
    premium_button = discord.ui.Button(
        label="💎 Mua Premium (500 Tcoin/3 ngày)",
        style=discord.ButtonStyle.danger,
        custom_id="buy_premium"
    )
    
    view.add_item(upload_button)
    view.add_item(link_button)
    view.add_item(premium_button)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="buypremium", description="Mua Premium bằng Tcoin")
async def buy_premium(interaction: discord.Interaction):
    """Mua Premium bằng Tcoin"""
    user_id = str(interaction.user.id)
    current_tcoin = get_user_tcoin(interaction.user.id)
    
    if current_tcoin < 500:
        embed = discord.Embed(
            title="❌ Không đủ Tcoin",
            description=f"Bạn cần 500 Tcoin để mua Premium 3 ngày!\nHiện tại: **{current_tcoin}** Tcoin",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Trừ Tcoin và thêm premium
    add_user_tcoin(interaction.user.id, -500)
    
    # Thêm vào premium users (3 ngày)
    if user_id not in premium_users:
        premium_users.append(user_id)
        save_json(PREMIUM_USERS_FILE, {'users': premium_users})
    
    embed = discord.Embed(
        title="⭐ Đã mua Premium thành công!",
        description="Bạn đã được kích hoạt Premium trong 3 ngày!",
        color=0xffd700,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💰 Tcoin còn lại", value=f"**{get_user_tcoin(interaction.user.id)}** Tcoin", inline=True)
    embed.add_field(name="⏰ Thời hạn", value="3 ngày", inline=True)
    embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="tcoin", description="Xem số Tcoin của bạn")
async def tcoin_info(interaction: discord.Interaction):
    """Xem thông tin Tcoin"""
    user_id = str(interaction.user.id)
    current_tcoin = get_user_tcoin(interaction.user.id)
    
    embed = discord.Embed(
        title="🪙 Thông Tin Tcoin",
        description=f"Tcoin của {interaction.user.mention}",
        color=0xffd700,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💰 Số dư", value=f"**{current_tcoin}** Tcoin", inline=True)
    
    # Giới hạn còn lại
    upload_attempts = get_daily_limit_count(interaction.user.id, 'upload')
    link_attempts = get_daily_limit_count(interaction.user.id, 'link')
    
    embed.add_field(name="📸 Upload ảnh hôm nay", value=f"**{upload_attempts}/10** lần", inline=True)
    embed.add_field(name="🔗 Vượt link hôm nay", value=f"**{link_attempts}/5** lần", inline=True)
    
    # Thông tin premium
    premium_status = "⭐ ĐANG KÍCH HOẠT" if is_premium(interaction.user.id) else "🔹 CHƯA KÍCH HOẠT"
    embed.add_field(name="💎 Premium", value=premium_status, inline=True)
    
    # Hướng dẫn kiếm Tcoin
    embed.add_field(
        name="📈 Cách kiếm Tcoin",
        value="""• 📸 **Upload ảnh**: +1 Tcoin/lần (10 lần/ngày)
• 🔗 **Vượt link**: +2-5 Tcoin/lần (5 lần/ngày)
• ⭐ **Mua Premium**: 500 Tcoin/3 ngày""",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== LỆNH REPORT ====================

@bot.tree.command(name="report", description="Report bug hoặc góp ý cho bot")
async def report_command(interaction: discord.Interaction, issue: str, description: str):
    """Report bug hoặc góp ý"""
    if not REPORT_CHANNEL_ID:
        embed = discord.Embed(
            title="❌ Lỗi cấu hình",
            description="Kênh report chưa được cấu hình!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    try:
        report_channel = bot.get_channel(int(REPORT_CHANNEL_ID))
        if not report_channel:
            embed = discord.Embed(
                title="❌ Không tìm thấy kênh report",
                description="Kênh report không tồn tại!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Tạo embed report
        report_embed = discord.Embed(
            title="📢 BÁO CÁO LỖI MỚI",
            description=f"**Vấn đề:** {issue}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        
        report_embed.add_field(name="📝 Mô tả", value=description, inline=False)
        report_embed.add_field(name="👤 Người report", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
        report_embed.add_field(name="🏠 Server", value=f"{interaction.guild.name} (`{interaction.guild.id}`)", inline=True)
        report_embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
        
        await report_channel.send(embed=report_embed)
        
        # Phản hồi cho user
        success_embed = discord.Embed(
            title="✅ Đã gửi report!",
            description="Cảm ơn bạn đã báo cáo lỗi. Chúng tôi sẽ kiểm tra và khắc phục sớm nhất!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        success_embed.add_field(name="📢 Vấn đề", value=issue, inline=False)
        success_embed.add_field(name="📝 Mô tả", value=description[:500] + "..." if len(description) > 500 else description, inline=False)
        
        await interaction.response.send_message(embed=success_embed, ephemeral=True)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Lỗi khi gửi report",
            description=f"Đã xảy ra lỗi: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# ==================== COMMANDS CHÍNH ====================

@bot.tree.command(name="help", description="Hướng dẫn sử dụng bot")
async def help_command(interaction: discord.Interaction):
    """Hiển thị hướng dẫn sử dụng"""
    embed = discord.Embed(
        title="📖 Hướng Dẫn Sử Dụng Bot",
        description="Bot upload ảnh và quản lý nội dung thông minh",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    # Lệnh chính
    embed.add_field(
        name="🖼️ Lệnh Upload Ảnh",
        value="""• `/laylinkanh` - Upload 1 ảnh lên ImgBB
• `/laynhieulink` - Upload nhiều ảnh lên ImgBB (tối đa 10 ảnh)
• `/laylinkanhdiscord` - Lấy link Discord CDN (10 giây)
• `/uploadimgbb` - Upload ảnh lên ImgBB với tùy chọn
• `/uploadmulti` - Upload nhiều ảnh cùng lúc""",
        inline=False
    )
    
    # Lệnh thông tin
    embed.add_field(
        name="ℹ️ Lệnh Thông Tin",
        value="""• `/help` - Hiển thị hướng dẫn này
• `/stats` - Thống kê sử dụng của bạn
• `/userinfo` - Thông tin user
• `/serverinfo` - Thông tin server
• `/botinfo` - Thông tin bot""",
        inline=False
    )
    
    # Lệnh ảnh profile & server
    embed.add_field(
        name="👤 Lệnh Ảnh Profile & Server",
        value="""• `/layiduser` - Lấy ID Discord của user
• `/laylinklogoprofile` - Lấy link ảnh profile
• `/laylogoserver` - Lấy logo server
• `/laylinklogoserver` - Lấy link logo server
• `/banneruser` - Lấy banner của user
• `/bannerserver` - Lấy banner của server""",
        inline=False
    )
    
    # Lệnh Tcoin
    embed.add_field(
        name="🪙 Lệnh Tcoin",
        value="""• `/getTcoin` - Nhận Tcoin miễn phí
• `/Tcoin` - Xem thông tin Tcoin
• `/buyPremium` - Mua Premium bằng Tcoin""",
        inline=False
    )
    
    # Lệnh tiện ích
    embed.add_field(
        name="🔧 Lệnh Tiện Ích",
        value="""• `/convertimage` - Chuyển đổi định dạng ảnh
• `/backupimage` - Backup ảnh
• `/restoreimage` - Khôi phục ảnh từ backup
• `/listbackups` - Danh sách backups
• `/deletebackup` - Xóa backup
• `/report` - Report bug hoặc góp ý""",
        inline=False
    )
    
    # Lệnh quản lý
    embed.add_field(
        name="⚙️ Lệnh Quản Lý (Admin)",
        value="""• `/addwhitelist` - Thêm user vào whitelist
• `/removewhitelist` - Xóa user khỏi whitelist
• `/addblacklist` - Thêm user vào blacklist
• `/removeblacklist` - Xóa user khỏi blacklist
• `/addpremium` - Thêm user vào premium
• `/removepremium` - Xóa user khỏi premium""",
        inline=False
    )
    
    # Quy định
    embed.add_field(
        name="📜 Quy Định Sử Dụng",
        value="""• ✅ **Được phép**: Ảnh thường, meme, artwork, ảnh cá nhân
• ❌ **Cấm**: 18+, máu me, bạo lực, nội dung nhạy cảm, ảnh phản cảm
• 💾 **Giới hạn**: 100MB/ngày/user (Standard), 500MB/ngày (Premium)
• ⏰ **Thời gian upload**: 1 giờ/lệnh
• 📸 **Số ảnh**: Tối đa 10 ảnh/lần upload
• 🔒 **Chế độ**: WHITELIST (chỉ user được phép mới dùng được)""",
        inline=False
    )
    
    embed.add_field(
        name="📊 Thống Kê",
        value=f"• **Chế độ**: {BOT_MODE.upper()}\n• **Whitelist**: {len(whitelist)} users\n• **Blacklist**: {len(blacklist)} users\n• **Premium**: {len(premium_users)} users\n• **Server**: {len(bot.guilds)} servers",
        inline=False
    )
    
    embed.set_footer(text="Tuân thủ quy định để tránh bị chặn sử dụng bot")
    
    # Thêm nút report
    view = add_report_button(embed)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="laylinkanh", description="Upload 1 ảnh lên ImgBB và lấy link")
async def lay_link_anh(interaction: discord.Interaction):
    """Upload 1 ảnh lên ImgBB"""
    # Kiểm tra authorization
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not imgbb_uploader:
        embed = discord.Embed(
            title="❌ Lỗi cấu hình ImgBB", 
            description="ImgBB API Key chưa được cấu hình!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Kiểm tra dung lượng
    remaining = get_remaining_daily_usage(interaction.user.id)
    if remaining <= 0 and not is_premium(interaction.user.id):
        embed = discord.Embed(
            title="💾 Đã hết dung lượng hôm nay",
            description=f"Bạn đã sử dụng hết {DAILY_LIMIT_MB}MB cho hôm nay. Vui lòng quay lại vào ngày mai!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📸 Upload Ảnh Lên ImgBB",
        description="**🔒 Chỉ bạn nhìn thấy**\nHãy upload 1 ảnh trong tin nhắn tiếp theo!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="⏰ Thời gian", value="1 giờ để upload", inline=True)
    embed.add_field(name="💾 Dung lượng còn", value=humanize.naturalsize(remaining), inline=True)
    embed.add_field(name="📝 Định dạng", value=", ".join(ALLOWED_EXTENSIONS), inline=True)
    embed.add_field(name="👤 Người upload", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Trạng thái", value="🟢 Đang chờ ảnh...", inline=True)
    
    if is_premium(interaction.user.id):
        embed.add_field(name="💎 Tài khoản", value="⭐ PREMIUM", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.attachments
    
    try:
        wait_msg = await bot.wait_for('message', timeout=3600.0, check=check)
        
        if wait_msg.attachments:
            attachment = wait_msg.attachments[0]
            
            if any(attachment.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                # Kiểm tra dung lượng file
                if not can_upload(interaction.user.id, attachment.size):
                    embed = discord.Embed(
                        title="💾 Không đủ dung lượng",
                        description=f"File {humanize.naturalsize(attachment.size)} vượt quá dung lượng còn lại {humanize.naturalsize(remaining)}!",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Upload
                uploading_embed = discord.Embed(
                    title="⏳ Đang upload...",
                    description=f"**{interaction.user.mention}** đang upload ảnh lên ImgBB",
                    color=0xffa500,
                    timestamp=datetime.now()
                )
                uploading_embed.set_image(url=UPLOADING_GIF)
                uploading_embed.add_field(name="📁 File", value=attachment.filename, inline=True)
                uploading_embed.add_field(name="📏 Kích thước", value=humanize.naturalsize(attachment.size), inline=True)
                await interaction.followup.send(embed=uploading_embed, ephemeral=True)
                
                imgbb_data, error = await imgbb_uploader.upload_image(attachment.url, attachment.filename)
                
                if error:
                    error_embed = discord.Embed(
                        title="❌ Upload thất bại", 
                        description=error, 
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                    return
                
                # Cập nhật dung lượng
                update_user_daily_usage(interaction.user.id, attachment.size)
                log_usage(interaction.user.id, 'laylinkanh', attachment.size)
                
                # Thêm Tcoin nếu chưa vượt giới hạn
                if can_earn_tcoin(interaction.user.id, 'upload'):
                    add_user_tcoin(interaction.user.id, 1)
                    update_daily_limit_count(interaction.user.id, 'upload')
                    tcoin_earned = True
                else:
                    tcoin_earned = False
                
                # Backup ảnh
                backup_id = await backup_image(interaction.user.id, imgbb_data['url'], imgbb_data)
                
                # Kết quả
                result_embed = discord.Embed(
                    title="✅ Upload thành công!",
                    description=f"**{interaction.user.mention}** đã upload ảnh lên ImgBB",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                result_embed.add_field(name="🔗 Link ảnh", value=f"```{imgbb_data['url']}```", inline=False)
                result_embed.add_field(name="🔗 Link thumbnail", value=f"```{imgbb_data['thumb']}```", inline=False)
                result_embed.add_field(name="📁 Tên file", value=attachment.filename, inline=True)
                result_embed.add_field(name="📏 Kích thước", value=humanize.naturalsize(attachment.size), inline=True)
                result_embed.add_field(name="🖼️ Định dạng", value=imgbb_data['format'].upper(), inline=True)
                result_embed.add_field(name="📐 Kích thước ảnh", value=f"{imgbb_data['width']}x{imgbb_data['height']}", inline=True)
                result_embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
                result_embed.add_field(name="💾 Dung lượng còn", value=humanize.naturalsize(get_remaining_daily_usage(interaction.user.id)), inline=True)
                result_embed.add_field(name="📦 Backup ID", value=f"`{backup_id}`", inline=True)
                
                if tcoin_earned:
                    result_embed.add_field(name="🪙 Tcoin", value="+1 Tcoin", inline=True)
                
                result_embed.set_image(url=imgbb_data['url'])
                result_embed.set_thumbnail(url=SUCCESS_GIF)
                
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=imgbb_data['url']))
                view.add_item(discord.ui.Button(label="🔗 Copy Thumb", style=discord.ButtonStyle.link, url=imgbb_data['thumb']))
                view.add_item(discord.ui.Button(label="🌐 Mở Ảnh", style=discord.ButtonStyle.link, url=imgbb_data['url']))
                
                await interaction.followup.send(embed=result_embed, view=view, ephemeral=True)
                
                # Xóa tin nhắn chờ
                try:
                    await wait_msg.delete()
                except:
                    pass
                
            else:
                error_embed = discord.Embed(
                    title="❌ Định dạng không hỗ trợ", 
                    description=f"Chỉ hỗ trợ: {', '.join(ALLOWED_EXTENSIONS)}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            error_embed = discord.Embed(
                title="❌ Không tìm thấy ảnh",
                description="Vui lòng đính kèm ảnh khi sử dụng lệnh này",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏰ Hết thời gian chờ",
            description="Bạn đã không upload ảnh trong 1 giờ!",
            color=0xffa500
        )
        await interaction.followup.send(embed=timeout_embed, ephemeral=True)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Lỗi không xác định",
            description=f"Đã xảy ra lỗi: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="laynhieulink", description="Upload nhiều ảnh lên ImgBB (tối đa 10 ảnh)")
async def lay_nhieu_link(interaction: discord.Interaction):
    """Upload nhiều ảnh lên ImgBB"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not imgbb_uploader:
        embed = discord.Embed(
            title="❌ Lỗi cấu hình ImgBB", 
            description="ImgBB API Key chưa được cấu hình!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    remaining = get_remaining_daily_usage(interaction.user.id)
    if remaining <= 0 and not is_premium(interaction.user.id):
        embed = discord.Embed(
            title="💾 Đã hết dung lượng hôm nay",
            description=f"Bạn đã sử dụng hết {DAILY_LIMIT_MB}MB cho hôm nay. Vui lòng quay lại vào ngày mai!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🖼️ Upload Nhiều Ảnh",
        description="**🔒 Chỉ bạn nhìn thấy**\nUpload tối đa 10 ảnh trong tin nhắn tiếp theo!",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="⏰ Thời gian", value="1 giờ để upload", inline=True)
    embed.add_field(name="💾 Dung lượng còn", value=humanize.naturalsize(remaining), inline=True)
    embed.add_field(name="📸 Số ảnh tối đa", value=f"{MAX_IMAGES} ảnh", inline=True)
    embed.add_field(name="👤 Người upload", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Trạng thái", value="🟢 Đang chờ ảnh...", inline=True)
    
    if is_premium(interaction.user.id):
        embed.add_field(name="💎 Tài khoản", value="⭐ PREMIUM", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.attachments
    
    try:
        wait_msg = await bot.wait_for('message', timeout=3600.0, check=check)
        
        if wait_msg.attachments:
            attachments = [att for att in wait_msg.attachments if any(
                att.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS
            )][:MAX_IMAGES]  # Giới hạn số ảnh
            
            if not attachments:
                embed = discord.Embed(
                    title="❌ Không có ảnh hợp lệ",
                    description=f"Không tìm thấy ảnh nào có định dạng hỗ trợ ({', '.join(ALLOWED_EXTENSIONS)})",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Kiểm tra tổng dung lượng
            total_size = sum(att.size for att in attachments)
            if not can_upload(interaction.user.id, total_size):
                embed = discord.Embed(
                    title="💾 Không đủ dung lượng",
                    description=f"Tổng {humanize.naturalsize(total_size)} vượt quá dung lượng còn lại {humanize.naturalsize(remaining)}!",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Upload
            uploading_embed = discord.Embed(
                title=f"⏳ Đang upload {len(attachments)} ảnh...",
                description=f"**{interaction.user.mention}** đang upload ảnh lên ImgBB",
                color=0xffa500,
                timestamp=datetime.now()
            )
            uploading_embed.set_image(url=UPLOADING_GIF)
            uploading_embed.add_field(name="📊 Tổng dung lượng", value=humanize.naturalsize(total_size), inline=True)
            uploading_embed.add_field(name="📸 Số ảnh", value=len(attachments), inline=True)
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
                    
                    # Thêm Tcoin nếu chưa vượt giới hạn
                    if can_earn_tcoin(interaction.user.id, 'upload'):
                        add_user_tcoin(interaction.user.id, 1)
                        update_daily_limit_count(interaction.user.id, 'upload')
                        tcoin_earned += 1
                    
                    # Backup từng ảnh
                    await backup_image(interaction.user.id, imgbb_data['url'], imgbb_data)
                else:
                    failed_uploads.append({
                        'filename': attachment.filename,
                        'error': error
                    })
            
            # Cập nhật dung lượng và log
            update_user_daily_usage(interaction.user.id, total_uploaded_size)
            log_usage(interaction.user.id, 'laynhieulink', total_uploaded_size)
            
            # Kết quả
            result_embed = discord.Embed(
                title=f"✅ Đã upload {len(uploaded_images)} ảnh!",
                description=f"**{interaction.user.mention}** đã upload thành công",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            # Tạo view với nút copy cho từng ảnh
            view = discord.ui.View()
            
            # Hiển thị links
            links_text = ""
            for i, img in enumerate(uploaded_images, 1):
                links_text += f"{i}. **{img['filename']}**\n```{img['url']}```\n"
                # Thêm nút copy cho mỗi ảnh
                view.add_item(discord.ui.Button(
                    label=f"📋 Ảnh {i}",
                    style=discord.ButtonStyle.link,
                    url=img['url']
                ))
            
            if links_text:
                result_embed.add_field(name="🔗 Danh sách links", value=links_text[:1024], inline=False)
            
            result_embed.add_field(name="📊 Tổng dung lượng", value=humanize.naturalsize(total_uploaded_size), inline=True)
            result_embed.add_field(name="💾 Dung lượng còn", value=humanize.naturalsize(get_remaining_daily_usage(interaction.user.id)), inline=True)
            result_embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
            result_embed.add_field(name="📅 Ngày upload", value=f"<t:{int(datetime.now().timestamp())}:D>", inline=True)
            result_embed.add_field(name="👤 Người upload", value=interaction.user.mention, inline=True)
            
            if tcoin_earned > 0:
                result_embed.add_field(name="🪙 Tcoin nhận được", value=f"+{tcoin_earned} Tcoin", inline=True)
            
            if failed_uploads:
                failed_text = "\n".join([f"• {f['filename']}: {f['error']}" for f in failed_uploads[:3]])
                result_embed.add_field(name="❌ Upload thất bại", value=failed_text, inline=False)
            
            result_embed.set_thumbnail(url=SUCCESS_GIF)
            
            await interaction.followup.send(embed=result_embed, view=view, ephemeral=True)
            
            # Xóa tin nhắn chờ
            try:
                await wait_msg.delete()
            except:
                pass
            
        else:
            embed = discord.Embed(
                title="❌ Không tìm thấy ảnh",
                description="Vui lòng đính kèm ảnh khi sử dụng lệnh này",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="⏰ Hết thời gian chờ",
            description="Bạn đã không upload ảnh trong 1 giờ!",
            color=0xffa500
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Lỗi không xác định",
            description=f"Đã xảy ra lỗi: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

# ==================== 30 LỆNH BỔ SUNG ====================

@bot.tree.command(name="uploadimgbb", description="Upload ảnh lên ImgBB với tùy chọn nâng cao")
async def upload_imgbb(interaction: discord.Interaction):
    """Upload ảnh lên ImgBB với tùy chọn"""
    await lay_link_anh(interaction)

@bot.tree.command(name="uploadmulti", description="Upload nhiều ảnh cùng lúc lên ImgBB")
async def upload_multi(interaction: discord.Interaction):
    """Upload nhiều ảnh cùng lúc"""
    await lay_nhieu_link(interaction)

@bot.tree.command(name="serverinfo", description="Thông tin về server hiện tại")
async def server_info(interaction: discord.Interaction):
    """Hiển thị thông tin server"""
    guild = interaction.guild
    
    embed = discord.Embed(
        title=f"🏠 Thông Tin Server: {guild.name}",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="👑 Chủ server", value=guild.owner.mention, inline=True)
    embed.add_field(name="📅 Tạo server", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
    embed.add_field(name="👥 Thành viên", value=f"`{guild.member_count}`", inline=True)
    embed.add_field(name="📊 Online", value=f"`{sum(1 for m in guild.members if m.status != discord.Status.offline)}`", inline=True)
    embed.add_field(name="💬 Số kênh", value=f"`{len(guild.channels)}`", inline=True)
    embed.add_field(name="🎭 Số role", value=f"`{len(guild.roles)}`", inline=True)
    embed.add_field(name="🚀 Boost Level", value=f"`{guild.premium_tier}`", inline=True)
    embed.add_field(name="⭐ Boosts", value=f"`{guild.premium_subscription_count}`", inline=True)
    
    if guild.banner:
        embed.add_field(name="🎨 Banner", value=f"[Xem banner]({guild.banner.url})", inline=True)
    
    embed.set_footer(text=f"Server: {guild.name}")
    
    log_usage(interaction.user.id, 'serverinfo')
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="botinfo", description="Thông tin về bot")
async def bot_info(interaction: discord.Interaction):
    """Hiển thị thông tin bot"""
    embed = discord.Embed(
        title="🤖 Thông Tin Bot",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    # Thông tin cơ bản
    embed.add_field(name="📛 Tên bot", value=bot.user.name, inline=True)
    embed.add_field(name="🆔 Bot ID", value=f"`{bot.user.id}`", inline=True)
    embed.add_field(name="📅 Tạo bot", value=f"<t:{int(bot.user.created_at.timestamp())}:D>", inline=True)
    
    # Thống kê
    total_members = sum(guild.member_count for guild in bot.guilds)
    total_commands = sum(len(logs) for logs in usage_log.values())
    
    embed.add_field(name="🏠 Số server", value=f"`{len(bot.guilds)}`", inline=True)
    embed.add_field(name="👥 Tổng thành viên", value=f"`{total_members}`", inline=True)
    embed.add_field(name="📈 Tổng lệnh", value=f"`{total_commands}`", inline=True)
    
    # Hiệu suất
    latency = round(bot.latency * 1000)
    embed.add_field(name="🏓 Độ trễ", value=f"`{latency}ms`", inline=True)
    
    # Cấu hình
    embed.add_field(name="🔧 Chế độ", value=BOT_MODE.upper(), inline=True)
    embed.add_field(name="💾 Giới hạn/ngày", value=f"`{DAILY_LIMIT_MB}MB`", inline=True)
    embed.add_field(name="📋 Whitelist", value=f"`{len(whitelist)}` users", inline=True)
    embed.add_field(name="🚫 Blacklist", value=f"`{len(blacklist)}` users", inline=True)
    embed.add_field(name="⭐ Premium", value=f"`{len(premium_users)}` users", inline=True)
    
    # Phiên bản
    embed.add_field(name="🔢 Phiên bản", value="`2.0.0`", inline=True)
    embed.add_field(name="📚 Thư viện", value="`discord.py`", inline=True)
    embed.add_field(name="🐍 Python", value="`3.8+`", inline=True)
    
    embed.set_footer(text=f"Bot ID: {bot.user.id}")
    
    log_usage(interaction.user.id, 'botinfo')
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="banneruser", description="Lấy banner của user")
async def banner_user(interaction: discord.Interaction, user: discord.User = None):
    """Lấy banner của user"""
    target_user = user or interaction.user
    
    try:
        # Fetch user để lấy thông tin đầy đủ
        user_info = await bot.fetch_user(target_user.id)
        
        if not user_info.banner:
            embed = discord.Embed(
                title="❌ User không có banner",
                description=f"{target_user.mention} không có banner!",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🎨 Banner của {target_user.display_name}",
            description=f"Banner của {target_user.mention}",
            color=0x0099ff,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🔗 Link banner", value=f"```{user_info.banner.url}```", inline=False)
        embed.add_field(name="👤 User", value=target_user.mention, inline=True)
        embed.add_field(name="🆔 User ID", value=f"`{target_user.id}`", inline=True)
        embed.add_field(name="👤 Yêu cầu bởi", value=interaction.user.mention, inline=True)
        embed.set_image(url=user_info.banner.url)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=user_info.banner.url))
        view.add_item(discord.ui.Button(label="🌐 Mở Banner", style=discord.ButtonStyle.link, url=user_info.banner.url))
        
        log_usage(interaction.user.id, 'banneruser')
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Lỗi khi lấy banner",
            description=f"Không thể lấy banner của {target_user.mention}: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="bannerserver", description="Lấy banner của server")
async def banner_server(interaction: discord.Interaction):
    """Lấy banner của server"""
    guild = interaction.guild
    
    if not guild.banner:
        embed = discord.Embed(
            title="❌ Server không có banner",
            description=f"Server **{guild.name}** không có banner!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"🎨 Banner Server: {guild.name}",
        description=f"Banner của server **{guild.name}**",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="🔗 Link banner", value=f"```{guild.banner.url}```", inline=False)
    embed.add_field(name="🏠 Server", value=guild.name, inline=True)
    embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="👤 Yêu cầu bởi", value=interaction.user.mention, inline=True)
    embed.set_image(url=guild.banner.url)
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=guild.banner.url))
    view.add_item(discord.ui.Button(label="🌐 Mở Banner", style=discord.ButtonStyle.link, url=guild.banner.url))
    
    log_usage(interaction.user.id, 'bannerserver')
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="convertimage", description="Chuyển đổi định dạng ảnh")
async def convert_image(interaction: discord.Interaction):
    """Chuyển đổi định dạng ảnh"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not IMGUR_CLIENT_ID:
        embed = discord.Embed(
            title="❌ Lỗi cấu hình",
            description="ImgBB API Key chưa được cấu hình!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔄 Chuyển Đổi Định Dạng Ảnh",
        description="**🔒 Chỉ bạn nhìn thấy**\nHãy upload ảnh trong tin nhắn tiếp theo để chuyển đổi định dạng!",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="⏰ Thời gian", value="5 phút để upload", inline=True)
    embed.add_field(name="🖼️ Định dạng hỗ trợ", value="PNG, JPEG, WEBP", inline=True)
    embed.add_field(name="👤 Người dùng", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Trạng thái", value="🟢 Đang chờ ảnh...", inline=True)
    
    view = ImageConverterView(interaction.user.id)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.attachments
    
    try:
        wait_msg = await bot.wait_for('message', timeout=300.0, check=check)
        
        if wait_msg.attachments:
            attachment = wait_msg.attachments[0]
            
            if any(attachment.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                # Lưu ảnh gốc vào view
                view.original_image = attachment.url
                
                embed = discord.Embed(
                    title="✅ Đã nhận ảnh!",
                    description=f"Đã nhận ảnh **{attachment.filename}**\nHãy chọn định dạng muốn chuyển đổi từ menu bên dưới:",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="📁 File", value=attachment.filename, inline=True)
                embed.add_field(name="📏 Kích thước", value=humanize.naturalsize(attachment.size), inline=True)
                embed.set_thumbnail(url=attachment.url)
                
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                
                # Xóa tin nhắn chờ
                try:
                    await wait_msg.delete()
                except:
                    pass
            else:
                error_embed = discord.Embed(
                    title="❌ Định dạng không hỗ trợ",
                    description=f"Chỉ hỗ trợ: {', '.join(ALLOWED_EXTENSIONS)}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            error_embed = discord.Embed(
                title="❌ Không tìm thấy ảnh",
                description="Vui lòng đính kèm ảnh khi sử dụng lệnh này",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏰ Hết thời gian chờ",
            description="Bạn đã không upload ảnh trong 5 phút!",
            color=0xffa500
        )
        await interaction.followup.send(embed=timeout_embed, ephemeral=True)

@bot.tree.command(name="backupimage", description="Backup ảnh vào database")
async def backup_image_cmd(interaction: discord.Interaction, image_url: str):
    """Backup ảnh vào database"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    try:
        # Kiểm tra URL hợp lệ
        if not image_url.startswith(('http://', 'https://')):
            embed = discord.Embed(
                title="❌ URL không hợp lệ",
                description="URL phải bắt đầu với http:// hoặc https://",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Tải ảnh để kiểm tra
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    embed = discord.Embed(
                        title="❌ Không thể tải ảnh",
                        description="URL không trả về ảnh hợp lệ!",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                image_data = await response.read()
                
                # Upload lên ImgBB để backup
                imgbb_data, error = await imgbb_uploader.upload_image(image_url, "backup_image")
                
                if error:
                    embed = discord.Embed(
                        title="❌ Lỗi khi backup",
                        description=error,
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                # Backup vào database
                backup_id = await backup_image(interaction.user.id, imgbb_data['url'], imgbb_data)
                
                # Kết quả
                embed = discord.Embed(
                    title="✅ Backup thành công!",
                    description=f"Đã backup ảnh thành công",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="🔗 Link ảnh", value=f"```{imgbb_data['url']}```", inline=False)
                embed.add_field(name="📦 Backup ID", value=f"`{backup_id}`", inline=True)
                embed.add_field(name="👤 Người backup", value=interaction.user.mention, inline=True)
                embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
                embed.add_field(name="🖼️ Định dạng", value=imgbb_data['format'].upper(), inline=True)
                embed.add_field(name="📐 Kích thước", value=f"{imgbb_data['width']}x{imgbb_data['height']}", inline=True)
                
                embed.set_image(url=imgbb_data['url'])
                
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=imgbb_data['url']))
                view.add_item(discord.ui.Button(label="🌐 Mở Ảnh", style=discord.ButtonStyle.link, url=imgbb_data['url']))
                
                log_usage(interaction.user.id, 'backupimage')
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Lỗi khi backup",
            description=f"Đã xảy ra lỗi: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="restoreimage", description="Khôi phục ảnh từ backup")
async def restore_image(interaction: discord.Interaction, backup_id: str):
    """Khôi phục ảnh từ backup"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if backup_id not in backup_data:
        embed = discord.Embed(
            title="❌ Backup ID không tồn tại",
            description="Không tìm thấy backup với ID này!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    backup = backup_data[backup_id]
    
    # Kiểm tra quyền truy cập
    if str(interaction.user.id) != backup['user_id'] and not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="❌ Không có quyền truy cập",
            description="Bạn không có quyền truy cập backup này!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Hiển thị thông tin backup
    embed = discord.Embed(
        title="📦 Thông Tin Backup",
        description=f"Backup ID: `{backup_id}`",
        color=0x0099ff,
        timestamp=datetime.fromisoformat(backup['timestamp'])
    )
    
    embed.add_field(name="🔗 Link ảnh", value=f"```{backup['image_url']}```", inline=False)
    embed.add_field(name="👤 Người backup", value=f"<@{backup['user_id']}>", inline=True)
    embed.add_field(name="⏰ Thời gian backup", value=f"<t:{int(datetime.fromisoformat(backup['timestamp']).timestamp())}:F>", inline=True)
    
    if 'image_data' in backup:
        img_data = backup['image_data']
        embed.add_field(name="🖼️ Định dạng", value=img_data.get('format', 'Unknown').upper(), inline=True)
        embed.add_field(name="📐 Kích thước", value=f"{img_data.get('width', 'Unknown')}x{img_data.get('height', 'Unknown')}", inline=True)
    
    embed.set_image(url=backup['image_url'])
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=backup['image_url']))
    view.add_item(discord.ui.Button(label="🌐 Mở Ảnh", style=discord.ButtonStyle.link, url=backup['image_url']))
    
    log_usage(interaction.user.id, 'restoreimage')
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="listbackups", description="Danh sách backups của bạn")
async def list_backups(interaction: discord.Interaction):
    """Danh sách backups"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    user_backups = {k: v for k, v in backup_data.items() if v['user_id'] == str(interaction.user.id)}
    
    if not user_backups:
        embed = discord.Embed(
            title="📦 Danh Sách Backup",
            description="Bạn chưa có backup nào!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Sắp xếp theo thời gian mới nhất
    sorted_backups = sorted(user_backups.items(), key=lambda x: x[1]['timestamp'], reverse=True)[:10]
    
    embed = discord.Embed(
        title="📦 Danh Sách Backup Của Bạn",
        description=f"Tổng cộng: **{len(user_backups)}** backup(s)",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    for backup_id, backup in sorted_backups:
        time = datetime.fromisoformat(backup['timestamp'])
        embed.add_field(
            name=f"🆔 {backup_id}",
            value=f"⏰ <t:{int(time.timestamp())}:R>\n🔗 [Xem ảnh]({backup['image_url']})",
            inline=True
        )
    
    embed.set_footer(text="Sử dụng /restoreimage <backup_id> để khôi phục")
    
    log_usage(interaction.user.id, 'listbackups')
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="deletebackup", description="Xóa backup")
async def delete_backup(interaction: discord.Interaction, backup_id: str):
    """Xóa backup"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if backup_id not in backup_data:
        embed = discord.Embed(
            title="❌ Backup ID không tồn tại",
            description="Không tìm thấy backup với ID này!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    backup = backup_data[backup_id]
    
    # Kiểm tra quyền truy cập
    if str(interaction.user.id) != backup['user_id'] and not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="❌ Không có quyền xóa",
            description="Bạn không có quyền xóa backup này!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Xóa backup
    del backup_data[backup_id]
    save_json(BACKUP_DATA_FILE, backup_data)
    
    embed = discord.Embed(
        title="✅ Đã xóa backup!",
        description=f"Đã xóa backup `{backup_id}` thành công",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="🔗 Link ảnh", value=f"[{backup['image_url']}]({backup['image_url']})", inline=False)
    embed.add_field(name="👤 Người xóa", value=interaction.user.mention, inline=True)
    
    log_usage(interaction.user.id, 'deletebackup')
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="cleardata", description="Xóa dữ liệu sử dụng của bạn")
async def clear_data(interaction: discord.Interaction):
    """Xóa dữ liệu sử dụng"""
    user_id = str(interaction.user.id)
    
    if user_id in user_stats:
        del user_stats[user_id]
        save_json(USER_STATS_FILE, user_stats)
    
    if user_id in usage_log:
        del usage_log[user_id]
        save_json(USAGE_LOG_FILE, usage_log)
    
    # Xóa backups của user
    user_backups = {k: v for k, v in backup_data.items() if v['user_id'] == user_id}
    for backup_id in user_backups.keys():
        del backup_data[backup_id]
    save_json(BACKUP_DATA_FILE, backup_data)
    
    embed = discord.Embed(
        title="✅ Đã xóa dữ liệu!",
        description="Đã xóa tất cả dữ liệu sử dụng và backups của bạn",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📊 Đã xóa", value="• Thống kê sử dụng\n• Lịch sử lệnh\n• Backups ảnh", inline=False)
    embed.add_field(name="👤 Người dùng", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Kiểm tra độ trễ của bot")
async def ping_command(interaction: discord.Interaction):
    """Kiểm tra ping"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Độ trễ: **{latency}ms**",
        color=0x00ff00 if latency < 100 else 0xffa500 if latency < 200 else 0xff0000,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Trạng thái", value="✅ Hoạt động tốt" if latency < 100 else "⚠️ Độ trễ trung bình" if latency < 200 else "❌ Độ trễ cao", inline=True)
    embed.add_field(name="🏠 Số server", value=f"`{len(bot.guilds)}`", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== CÁC LỆNH CÓ SẴN ====================

@bot.tree.command(name="laylinkanhdiscord", description="Lấy link ảnh từ Discord CDN (nhanh)")
async def lay_link_anh_discord(interaction: discord.Interaction):
    """Lấy link Discord CDN"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="⚡ Lấy Link Discord CDN",
        description="**🔒 Chỉ bạn nhìn thấy**\nUpload ảnh trong 10 giây để lấy link!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="⏰ Thời gian", value="10 giây để upload", inline=True)
    embed.add_field(name="⚡ Tốc độ", value="Link Discord CDN - cực nhanh", inline=True)
    embed.add_field(name="👤 Người upload", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Trạng thái", value="🟢 Đang chờ ảnh...", inline=True)
    
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
                    title="❌ Không có ảnh hợp lệ",
                    description=f"Không tìm thấy ảnh nào có định dạng hỗ trợ ({', '.join(ALLOWED_EXTENSIONS)})",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Tạo view với nút copy
            view = discord.ui.View()
            links_text = ""
            
            for i, attachment in enumerate(attachments, 1):
                links_text += f"{i}. **{attachment.filename}**\n```{attachment.url}```\n"
                view.add_item(discord.ui.Button(
                    label=f"📋 Ảnh {i}",
                    style=discord.ButtonStyle.link,
                    url=attachment.url
                ))
            
            result_embed = discord.Embed(
                title=f"✅ Đã lấy {len(attachments)} link!",
                description=f"**{interaction.user.mention}** - Link Discord CDN",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            result_embed.add_field(name="🔗 Danh sách links", value=links_text[:1024], inline=False)
            result_embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
            result_embed.add_field(name="📅 Ngày", value=f"<t:{int(datetime.now().timestamp())}:D>", inline=True)
            result_embed.add_field(name="👤 Người upload", value=interaction.user.mention, inline=True)
            result_embed.set_thumbnail(url=SUCCESS_GIF)
            
            log_usage(interaction.user.id, 'laylinkanhdiscord')
            
            await interaction.followup.send(embed=result_embed, view=view, ephemeral=True)
            
            # Xóa tin nhắn chờ
            try:
                await wait_msg.delete()
            except:
                pass
            
        else:
            embed = discord.Embed(
                title="❌ Không tìm thấy ảnh",
                description="Vui lòng đính kèm ảnh khi sử dụng lệnh này",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="⏰ Hết thời gian chờ",
            description="Bạn đã không upload ảnh trong 10 giây!",
            color=0xffa500
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Lỗi không xác định",
            description=f"Đã xảy ra lỗi: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="layiduser", description="Lấy ID Discord của user")
async def lay_id_discord(interaction: discord.Interaction, user: discord.User = None):
    """Lấy ID Discord"""
    target_user = user or interaction.user
    
    embed = discord.Embed(
        title="🆔 ID Discord",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="👤 User", value=f"{target_user.mention}", inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{target_user.id}`", inline=True)
    embed.add_field(name="📛 Tag", value=f"`{target_user.name}#{target_user.discriminator}`", inline=True)
    embed.add_field(name="📅 Tạo tài khoản", value=f"<t:{int(target_user.created_at.timestamp())}:D>", inline=True)
    embed.add_field(name="👤 Yêu cầu bởi", value=interaction.user.mention, inline=True)
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    log_usage(interaction.user.id, 'layiduser')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="laylinklogoprofile", description="Lấy link ảnh profile")
async def lay_link_logo_profile(interaction: discord.Interaction, user: discord.User = None):
    """Lấy link ảnh profile"""
    target_user = user or interaction.user
    
    embed = discord.Embed(
        title="🖼️ Ảnh Profile",
        description=f"Ảnh profile của {target_user.mention}",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="🔗 Link ảnh", value=f"```{target_user.display_avatar.url}```", inline=False)
    embed.add_field(name="👤 User", value=target_user.mention, inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{target_user.id}`", inline=True)
    embed.add_field(name="👤 Yêu cầu bởi", value=interaction.user.mention, inline=True)
    embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
    embed.set_image(url=target_user.display_avatar.url)
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="📋 Copy Link", style=discord.ButtonStyle.link, url=target_user.display_avatar.url))
    view.add_item(discord.ui.Button(label="🌐 Mở Ảnh", style=discord.ButtonStyle.link, url=target_user.display_avatar.url))
    
    log_usage(interaction.user.id, 'laylinklogoprofile')
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="laylogoserver", description="Lấy logo server từ danh sách server của bạn")
async def lay_logo_server(interaction: discord.Interaction):
    """Lấy logo server - hiển thị dropdown chọn server"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Lấy danh sách server mà user có mặt
    user_guilds = [guild for guild in bot.guilds if guild.get_member(interaction.user.id)]
    
    if not user_guilds:
        embed = discord.Embed(
            title="❌ Không tìm thấy server",
            description="Bạn không có trong bất kỳ server nào mà bot đang hoạt động!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Lọc các server có logo
    guilds_with_icon = [guild for guild in user_guilds if guild.icon]
    
    if not guilds_with_icon:
        embed = discord.Embed(
            title="❌ Không có server nào có logo",
            description="Không tìm thấy server nào có logo trong danh sách server của bạn!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏠 Chọn Server Để Lấy Logo",
        description=f"**🔒 Chỉ bạn nhìn thấy**\nChọn server từ danh sách dưới đây để lấy logo!",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📊 Tổng số server", value=f"**{len(user_guilds)}** server bạn đang tham gia", inline=True)
    embed.add_field(name="🖼️ Server có logo", value=f"**{len(guilds_with_icon)}** server có logo", inline=True)
    embed.add_field(name="⏰ Thời gian", value="60 giây để chọn", inline=True)
    embed.add_field(name="👤 Người yêu cầu", value=interaction.user.mention, inline=True)
    
    # Tạo dropdown chọn server
    view = ServerSelectView(guilds_with_icon, "logo")
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="laylinklogoserver", description="Lấy link logo server từ danh sách server của bạn")
async def lay_link_logo_server(interaction: discord.Interaction):
    """Lấy link logo server - hiển thị dropdown chọn server"""
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền sử dụng",
            description="Bạn không có trong whitelist. Liên hệ admin để được thêm vào.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Lấy danh sách server mà user có mặt
    user_guilds = [guild for guild in bot.guilds if guild.get_member(interaction.user.id)]
    
    if not user_guilds:
        embed = discord.Embed(
            title="❌ Không tìm thấy server",
            description="Bạn không có trong bất kỳ server nào mà bot đang hoạt động!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Lọc các server có logo
    guilds_with_icon = [guild for guild in user_guilds if guild.icon]
    
    if not guilds_with_icon:
        embed = discord.Embed(
            title="❌ Không có server nào có logo",
            description="Không tìm thấy server nào có logo trong danh sách server của bạn!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔗 Chọn Server Để Lấy Link Logo",
        description=f"**🔒 Chỉ bạn nhìn thấy**\nChọn server từ danh sách dưới đây để lấy link logo!",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📊 Tổng số server", value=f"**{len(user_guilds)}** server bạn đang tham gia", inline=True)
    embed.add_field(name="🖼️ Server có logo", value=f"**{len(guilds_with_icon)}** server có logo", inline=True)
    embed.add_field(name="⏰ Thời gian", value="60 giây để chọn", inline=True)
    embed.add_field(name="👤 Người yêu cầu", value=interaction.user.mention, inline=True)
    
    # Tạo dropdown chọn server
    view = ServerSelectView(guilds_with_icon, "link")
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="stats", description="Thống kê sử dụng của bạn")
async def stats_command(interaction: discord.Interaction):
    """Thống kê sử dụng"""
    user_id = str(interaction.user.id)
    
    embed = discord.Embed(
        title="📊 Thống Kê Sử Dụng",
        description=f"Thống kê của {interaction.user.mention}",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    # Dung lượng hôm nay
    today_usage = get_user_daily_usage(interaction.user.id)
    remaining = get_remaining_daily_usage(interaction.user.id)
    daily_limit = get_daily_limit(interaction.user.id)
    usage_percentage = (today_usage / daily_limit) * 100 if daily_limit > 0 else 0
    
    embed.add_field(
        name="💾 Dung lượng hôm nay",
        value=f"**Đã dùng:** {humanize.naturalsize(today_usage)}\n**Còn lại:** {humanize.naturalsize(remaining)}\n**Giới hạn:** {humanize.naturalsize(daily_limit)}\n**Tỉ lệ:** {usage_percentage:.1f}%",
        inline=False
    )
    
    # Tcoin info
    current_tcoin = get_user_tcoin(interaction.user.id)
    embed.add_field(name="🪙 Tcoin hiện tại", value=f"**{current_tcoin}** Tcoin", inline=True)
    
    # Giới hạn Tcoin
    upload_attempts = get_daily_limit_count(interaction.user.id, 'upload')
    link_attempts = get_daily_limit_count(interaction.user.id, 'link')
    embed.add_field(name="📸 Upload hôm nay", value=f"**{upload_attempts}/10** lần", inline=True)
    embed.add_field(name="🔗 Vượt link hôm nay", value=f"**{link_attempts}/5** lần", inline=True)
    
    # Lịch sử sử dụng
    if user_id in usage_log:
        recent_usage = usage_log[user_id][-10:]  # 10 lần gần nhất
        usage_text = ""
        for usage in reversed(recent_usage):
            time = datetime.fromisoformat(usage['timestamp'])
            size = f" - {humanize.naturalsize(usage['file_size'])}" if usage['file_size'] > 0 else ""
            usage_text += f"• `{usage['command']}`{size} - <t:{int(time.timestamp())}:R>\n"
        
        embed.add_field(name="📝 Lịch sử gần đây", value=usage_text or "Chưa có lịch sử", inline=False)
    
    # Tổng số lệnh
    total_commands = len(usage_log.get(user_id, []))
    embed.add_field(name="📈 Tổng lệnh đã dùng", value=f"**{total_commands}** lệnh", inline=True)
    
    # Số backups
    user_backups = sum(1 for backup in backup_data.values() if backup['user_id'] == user_id)
    embed.add_field(name="📦 Số backups", value=f"**{user_backups}** backup(s)", inline=True)
    
    # Trạng thái
    status = "✅ Được phép" if is_authorized(interaction.user.id) else "❌ Bị chặn"
    embed.add_field(name="🔐 Trạng thái", value=status, inline=True)
    
    # Premium status
    premium_status = "⭐ PREMIUM" if is_premium(interaction.user.id) else "🔹 STANDARD"
    embed.add_field(name="💎 Loại tài khoản", value=premium_status, inline=True)
    
    # Ngày thống kê
    embed.add_field(name="📅 Ngày thống kê", value=f"<t:{int(datetime.now().timestamp())}:D>", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="userinfo", description="Thông tin chi tiết về user")
async def userinfo_command(interaction: discord.Interaction, user: discord.User = None):
    """Thông tin user"""
    target_user = user or interaction.user
    await interaction.response.send_message(embed=get_user_info_embed(target_user), ephemeral=True)

# ==================== XỬ LÝ INTERACTION ====================

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Xử lý các interaction"""
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get('custom_id', '')
        
        if custom_id == "report_bug":
            # Mở modal report bug
            modal = discord.ui.Modal(title="📢 Report Bug")
            modal.add_item(discord.ui.TextInput(
                label="Vấn đề",
                placeholder="Mô tả ngắn gọn vấn đề...",
                custom_id="issue",
                style=discord.TextStyle.short,
                max_length=100
            ))
            modal.add_item(discord.ui.TextInput(
                label="Mô tả chi tiết",
                placeholder="Mô tả chi tiết về bug hoặc góp ý...",
                custom_id="description",
                style=discord.TextStyle.paragraph,
                max_length=1000
            ))
            
            async def modal_callback(interaction: discord.Interaction):
                issue = interaction.data['components'][0]['components'][0]['value']
                description = interaction.data['components'][1]['components'][0]['value']
                
                # Gửi report
                if REPORT_CHANNEL_ID:
                    try:
                        report_channel = bot.get_channel(int(REPORT_CHANNEL_ID))
                        if report_channel:
                            report_embed = discord.Embed(
                                title="📢 BÁO CÁO LỖI MỚI",
                                description=f"**Vấn đề:** {issue}",
                                color=0xff0000,
                                timestamp=datetime.now()
                            )
                            
                            report_embed.add_field(name="📝 Mô tả", value=description, inline=False)
                            report_embed.add_field(name="👤 Người report", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
                            report_embed.add_field(name="⏰ Thời gian", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
                            
                            await report_channel.send(embed=report_embed)
                            
                            # Phản hồi
                            success_embed = discord.Embed(
                                title="✅ Đã gửi report!",
                                description="Cảm ơn bạn đã báo cáo lỗi!",
                                color=0x00ff00
                            )
                            await interaction.response.send_message(embed=success_embed, ephemeral=True)
                    except Exception as e:
                        error_embed = discord.Embed(
                            title="❌ Lỗi khi gửi report",
                            description=str(e),
                            color=0xff0000
                        )
                        await interaction.response.send_message(embed=error_embed, ephemeral=True)
            
            modal.callback = modal_callback
            await interaction.response.send_modal(modal)
        
        elif custom_id == "upload_tcoin":
            # Xử lý upload ảnh để nhận Tcoin
            if not can_earn_tcoin(interaction.user.id, 'upload'):
                embed = discord.Embed(
                    title="❌ Đã đạt giới hạn",
                    description="Bạn đã đạt giới hạn 10 lần upload/ngày!",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📸 Upload Ảnh Để Nhận Tcoin",
                description="Upload 1 ảnh để nhận +1 Tcoin!",
                color=0xffd700,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif custom_id == "link_tcoin":
            # Xử lý vượt link để nhận Tcoin
            if not can_earn_tcoin(interaction.user.id, 'link'):
                embed = discord.Embed(
                    title="❌ Đã đạt giới hạn",
                    description="Bạn đã đạt giới hạn 5 lần vượt link/ngày!",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Tạo link ngẫu nhiên
            tcoin_amount = random.randint(2, 5)
            add_user_tcoin(interaction.user.id, tcoin_amount)
            update_daily_limit_count(interaction.user.id, 'link')
            
            embed = discord.Embed(
                title="🔗 Vượt Link Thành Công!",
                description=f"Bạn đã nhận được **+{tcoin_amount} Tcoin**!",
                color=0xffd700,
                timestamp=datetime.now()
            )
            
            embed.add_field(name="💰 Tcoin hiện tại", value=f"**{get_user_tcoin(interaction.user.id)}** Tcoin", inline=True)
            embed.add_field(name="🔗 Lần vượt link hôm nay", value=f"**{get_daily_limit_count(interaction.user.id, 'link')}/5**", inline=True)
            embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="🌐 Truy cập Website",
                style=discord.ButtonStyle.link,
                url=TCOIN_WEB_URL
            ))
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif custom_id == "buy_premium":
            # Chuyển hướng đến lệnh mua premium
            await buy_premium(interaction)

# Xử lý lỗi ứng dụng
@bot.event
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(
            title="❌ Thiếu quyền",
            description="Bạn không có quyền sử dụng lệnh này!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.CommandOnCooldown):
        embed = discord.Embed(
            title="⏰ Đang trong thời gian chờ",
            description=f"Vui lòng thử lại sau {error.retry_after:.1f} giây!",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        print(f"Lỗi ứng dụng: {error}")
        embed = discord.Embed(
            title="❌ Lỗi không xác định",
            description="Đã xảy ra lỗi khi thực hiện lệnh!",
            color=0xff0000
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

# Task tự động dọn dẹp dữ liệu cũ
@tasks.loop(hours=24)
async def cleanup_old_data():
    """Dọn dẹp dữ liệu cũ hàng ngày"""
    try:
        # Dọn dẹp user stats cũ (giữ 30 ngày)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        for user_id, stats in user_stats.items():
            user_stats[user_id] = {date: size for date, size in stats.items() 
                                 if datetime.strptime(date, '%Y-%m-%d') >= thirty_days_ago}
        
        save_json(USER_STATS_FILE, user_stats)
        print("✅ Đã dọn dẹp user stats cũ")
        
    except Exception as e:
        print(f"❌ Lỗi khi dọn dẹp dữ liệu: {e}")

# Chạy bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ LỖI: Không tìm thấy DISCORD_TOKEN!")
        exit(1)
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ LỖI: {e}")
