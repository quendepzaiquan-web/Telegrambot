# -*- coding: utf-8 -*-

import sys
import random
import time
import string
import os 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, constants
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes, 
    JobQueue
)
# ĐÃ SỬA LỖI: CHỈ SỬ DỤNG CÁC THAM SỐ CƠ BẢN ĐỂ KHÔNG BỊ LỖI CÚ PHÁP
from telegram.ext import PicklePersistence 

# ================== CẤU HÌNH BOT & NHÓM ==================
# LẤY TOKEN TỪ BIẾN MÔI TRƯỜNG RAILWAY
TOKEN = os.getenv("TOKEN") 

# ... (Các hằng số khác giữ nguyên) ...
GROUP_ID = -1002190645469 
ADMIN_ID = 5741051184
START_XU = 2000     
PHIEN_TIME = 45     
GAYGEM_TO_VND = 0.8 

# --- CẤU HÌNH NHÓM BẮT BUỘC ---
REQUIRED_GROUPS = {
    "Cộng đồng": -1002523611589,
    "Nhóm chơi chính": GROUP_ID,
}

# --- PUBLIC LINKS ---
PUBLIC_GROUP_LINKS = {
    "Cộng đồng": "https://t.me/ctnbam",
    "Nhóm chơi chính": "https://t.me/ctbmnnn",
}
# ... (Các hằng số khác giữ nguyên) ...

NEWBIE_BET_LIMIT = 3000         
ADULT_DEPOSIT_THRESHOLD = 10000 
LOSSBACK_THRESHOLD = 100000     
LOSSBACK_PERCENT = 0.02         

# --- CẤU HÌNH ĐẠI LÝ ---
AGENTS = ["daily_a", "daily_b", "hungvan07"] 

AGENT_NOTIFICATION_ID = {
    "hungvan07": ADMIN_ID,
}

# --- CẤU HÌNH REFERRAL MỚI ---
REFERRAL_BONUS_LOC = 750

# ================== DATA KHỞI TẠO (SỬ DỤNG application.bot_data) ==================
GLOBAL_DATA = {
    "HU": 0,
    "users": {},
    "current_bets": {}, 
    "phien_id": 1,
    "phien_start": time.time(),
    "lich_su": [],
    "timer_messages": {},
    "gift_codes": {}, 
    "fixed_kq": None,
    "is_initialized": True 
}

# ================== USER & LOGIC TÂN THỦ/TRƯỞNG THÀNH ==================
def get_global_data(context: ContextTypes.DEFAULT_TYPE):
    """Lấy dữ liệu toàn cục từ Application.bot_data (đã Persistence)."""
    return context.application.bot_data

def get_user_data(uid, context: ContextTypes.DEFAULT_TYPE):
    """Lấy dữ liệu của người dùng, nếu chưa có thì tạo mới."""
    global_data = get_global_data(context)
    users = global_data["users"]
    
    if uid not in users:
        users[uid] = {
            "xu": START_XU, 
            "code_xu": 0,
            "total_deposit": 0, 
            "total_loss": 0,    
            "status": "Newbie", 
            "referrer_id": None
        } 
    
    # Logic kiểm tra trạng thái
    if users[uid]["total_deposit"] >= ADULT_DEPOSIT_THRESHOLD and users[uid]["status"] == "Newbie":
        users[uid]["status"] = "Adult"
    
    # Admin luôn là Adult và có số dư lớn
    if uid == ADMIN_ID:
        users[uid]["xu"] = 10**18 
        users[uid]["status"] = "Adult" 
    
    return users[uid]

def tinh_ty_le(moc):
    if moc <= 10: hs = 0.75
    elif moc <= 20: hs = 0.85
    elif moc <= 50: hs = 0.95
    else: hs = 0.90
    return round((100 / moc) * hs, 2)

# ================== Bàn Phím & Logic Check Nhóm ==================
def get_main_keyboard(uid, context: ContextTypes.DEFAULT_TYPE):
    d = get_user_data(uid, context) 
    
    if d["status"] == "Newbie":
        status_text = "Tân Thủ 👶"
    else:
        status_text = "Trưởng Thành 👑"
        
    keyboard = [
        [
            InlineKeyboardButton(f"💸 Số Dư ({d['xu']} GG)", callback_data='sodu_check'),
            InlineKeyboardButton("Rút Tiền 💵", callback_data='rut_info'),
        ],
        [
            InlineKeyboardButton("Mời Bạn Bè 🎉", callback_data='ref_link'),
            InlineKeyboardButton("Hướng Dẫn ❓", callback_data='help_menu'),
        ],
        [
            InlineKeyboardButton(f"Cấp Độ: {status_text}", callback_data='status_info'),
            InlineKeyboardButton("Vào Nhóm Chơi Chính 🎮", url=PUBLIC_GROUP_LINKS["Nhóm chơi chính"]) 
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    chat_id = update.effective_chat.id
    u = update.effective_user
    
    is_member_group_1 = False
    is_member_group_2 = False

    try:
        status1 = (await context.bot.get_chat_member(REQUIRED_GROUPS["Cộng đồng"], u.id)).status
        if status1 not in ['left', 'kicked']:
            is_member_group_1 = True
    except Exception: pass

    try:
        status2 = (await context.bot.get_chat_member(REQUIRED_GROUPS["Nhóm chơi chính"], u.id)).status
        if status2 not in ['left', 'kicked']:
            is_member_group_2 = True
    except Exception: pass
    
    name = f"@{u.username}" if u.username else u.full_name
    
    if not (is_member_group_1 and is_member_group_2):
        keyboard = [
            [InlineKeyboardButton(f"Tham gia Nhóm Cộng đồng @ctnbam", url=PUBLIC_GROUP_LINKS["Cộng đồng"])],
            [InlineKeyboardButton(f"Tham gia Nhóm Chơi Chính @ctbmnnn", url=PUBLIC_GROUP_LINKS["Nhóm chơi chính"])],
            [InlineKeyboardButton("✅ Tôi Đã Tham Gia!", callback_data='check_join')],
        ]
        
        referral_text = f"🎁 *ƯU ĐÃI NÓNG*: Mời bạn bè tham gia qua link giới thiệu, bạn sẽ nhận được ngay *{REFERRAL_BONUS_LOC} Gay Gem Lộc* khi bạn bè đăng ký thành công! "
        
        msg = (
            f"👋 Chào mừng *{name}* đến với *GAY GEM CLUB*!\n\n"
            f"❗ Để bắt đầu trải nghiệm, bạn vui lòng tham gia đủ 2 nhóm chính thức sau: \n"
            f"1. **Nhóm Cộng đồng**: Nhận thông báo, sự kiện.\n"
            f"2. **Nhóm Chơi Chính**: Nơi đặt cược và xem kết quả.\n\n"
            f"{referral_text}\n\n"
            f"_Sau khi tham gia, nhấn nút 'Tôi Đã Tham Gia!' bên dưới._"
        )
        await update.effective_chat.send_message(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.MARKDOWN)

    else:
        d = get_user_data(u.id, context)
        msg = (
            f"👑 *CHÀO MỪNG ĐẾN VỚI SÂN CHƠI ĐẲNG CẤP* 👑\n\n"
            f"👤 *Người Chơi VIP* : `{name}`\n"
            f"💎 *Số Dư Nạp*: `{d['xu']}` Gay Gem\n\n"
            f"_💡 Nhấn 'Vào Nhóm Chơi Chính' để bắt đầu cược._"
        )
        await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(u.id, context), parse_mode=constants.ParseMode.MARKDOWN)

# ================== Xử lý /start (Async) ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    chat_id = update.effective_chat.id
    global_data = context.application.bot_data
    
    # 1. Xử lý logic Referral 
    referrer_id = None
    if context.args:
        try:
            ref_arg = context.args[0]
            if ref_arg.startswith("cref_"):
                parts = ref_arg.split('_')
                if len(parts) == 3:
                    referrer_id = int(parts[2])
                    
            if referrer_id and referrer_id != u.id:
                d = get_user_data(u.id, context)
                
                if d["referrer_id"] is None:
                    d["referrer_id"] = referrer_id
                    
                    r_data = get_user_data(referrer_id, context)
                    r_data["code_xu"] += REFERRAL_BONUS_LOC
                    
                    try:
                        await context.bot.send_message(
                            referrer_id, 
                            f"🎉 *CHÚC MỪNG!* Bạn nhận được *{REFERRAL_BONUS_LOC}* Gay Gem Lộc từ việc giới thiệu *{u.full_name}*!", 
                            parse_mode=constants.ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        print(f"Không thể gửi tin nhắn cho người giới thiệu {referrer_id}: {e}")

        except Exception:
            pass 
    
    
    # 2. Xử lý theo loại chat
    if chat_id == GROUP_ID:
        d = get_user_data(u.id, context)
        name = f"@{u.username}" if u.username else u.full_name
        phien_id = global_data["phien_id"]
        
        if d["status"] == "Newbie":
            status_info = f"👶 *Tân Thủ* (Giới hạn cược: `{NEWBIE_BET_LIMIT}` Gay Gem/lần)\n"
            deposit_needed = ADULT_DEPOSIT_THRESHOLD - d["total_deposit"]
            if deposit_needed > 0:
                status_info += f"_Cần nạp thêm `{deposit_needed}` Gay Gem để trở thành Trưởng thành._"
            else:
                status_info += f"_Đã đủ điều kiện, hãy nạp để kích hoạt Trưởng thành!_"
        else:
            status_info = f"👑 *Trưởng Thành* (Cược không giới hạn)\n"
            status_info += f"_Hoàn trả {int(LOSSBACK_PERCENT*100)}% nếu thua từ `{LOSSBACK_THRESHOLD}` Gay Gem._"

        msg = (
            f"👑 *CHÀO MỪNG ĐẾN VỚI SÂN CHƠI ĐẲNG CẤP* 👑\n\n"
            f"✨ *Phiên Hiện Tại* #`{phien_id}` ✨\n"
            f"👤 *Người Chơi VIP* : `{name}`\n"
            f"🌟 *Cấp Độ*: {status_info}\n\n"
            f"💎 *Tài Khoản Gay Gem*:\n"
            f"   💸 *Số Dư Nạp (Rút được)* : `{d['xu']}` Gay Gem\n"
            f"   🎁 *Số Dư Code Lộc (Rút được nếu thắng)* : `{d['code_xu']}` Gay Gem\n"
            f"_💡 1 Gay Gem = {GAYGEM_TO_VND} VNĐ_\n\n"
            f"📜 *Hướng Dẫn Lệnh Sang Chảnh*:\n"
            f"   - `/duoi_nap <%> <gay_gem>` : Cược bằng *Tiền Nạp*\n"
            f"   - `/duoi_loc <%> <gay_gem>` : Cược bằng *Tiền Code Lộc*\n"
            f"   - `/code <mã_code>` : *Nhận Gay Gem vào Số Dư Code Lộc*\n"
            f"   - `/sodu` : Kiểm tra số dư & Quy đổi\n"
            f"   - `/rut <tên_đại_lý> <gay_gem> <bank> <stk>` : *Rút Tiền Nạp*\n"
            f"   - `/lichsu` : Xem lịch sử 5 phiên gần nhất\n"
            f"   - `/chuyenxu <gay_gem>` : Chuyển tiền Nạp (Reply tin nhắn)\n\n"
            f"🕰 *Luật Chơi Vàng*:\n"
            f"   - Tiền thắng từ cược Nạp cộng vào *Nạp*. Thắng cược Lộc cộng vào *Lộc*.\n"
            f"   - `2%` mỗi cược được trích vào *HŨ MAY MẮN* 💰\n"
            f"🍾 *Chúc bạn trở thành người chiến thắng lấp lánh!*"
        )
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
        
    elif update.effective_chat.type == constants.ChatType.PRIVATE:
        await send_welcome_message(update, context)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    u = query.from_user
    
    msg_text = ""
    keyboard = None
    
    if data == 'check_join':
        is_member_group_1 = False
        is_member_group_2 = False
        
        try:
            status1 = (await context.bot.get_chat_member(REQUIRED_GROUPS["Cộng đồng"], u.id)).status
            if status1 not in ['left', 'kicked']:
                is_member_group_1 = True
        except Exception: pass
        try:
            status2 = (await context.bot.get_chat_member(REQUIRED_GROUPS["Nhóm chơi chính"], u.id)).status
            if status2 not in ['left', 'kicked']:
                is_member_group_2 = True
        except Exception: pass
        
        referral_text = f"🎁 *ƯU ĐÃI NÓNG*: Mời bạn bè tham gia qua link giới thiệu, bạn sẽ nhận được ngay *{REFERRAL_BONUS_LOC} Gay Gem Lộc* khi bạn bè đăng ký thành công! "
        
        if is_member_group_1 and is_member_group_2:
            d = get_user_data(u.id, context)
            name = f"@{u.username}" if u.username else u.full_name
            msg_text = (
                f"🎉 *XÁC NHẬN THÀNH CÔNG!* 🎉\n"
                f"👑 *CHÀO MỪNG ĐẾN VỚI SÂN CHƠI ĐẲNG CẤP* 👑\n\n"
                f"👤 *Người Chơi VIP* : `{name}`\n"
                f"💎 *Số Dư Nạp*: `{d['xu']}` Gay Gem\n\n"
                f"_💡 Nhấn 'Vào Nhóm Chơi Chính' để bắt đầu cược._"
            )
            keyboard = get_main_keyboard(u.id, context)
        else:
            keyboard = [
                [InlineKeyboardButton(f"Tham gia Nhóm Cộng đồng @ctnbam", url=PUBLIC_GROUP_LINKS["Cộng đồng"])],
                [InlineKeyboardButton(f"Tham gia Nhóm Chơi Chính @ctbmnnn", url=PUBLIC_GROUP_LINKS["Nhóm chơi chính"])],
                [InlineKeyboardButton("✅ Tôi Đã Tham Gia!", callback_data='check_join')],
            ]
            msg_text = f"❌ *Bạn chưa tham gia đủ 2 nhóm bắt buộc!* Vui lòng kiểm tra lại và nhấn nút 'Tôi Đã Tham Gia!'.\n\n{referral_text}"

    elif data == 'sodu_check':
        d = get_user_data(u.id, context)
        tong_xu = d['xu'] + d['code_xu']
        vnd_value = tong_xu * GAYGEM_TO_VND
        
        lossback_msg = ""
        if d["status"] == "Adult" and d["total_loss"] >= LOSSBACK_THRESHOLD:
            lossback_value = int(d["total_loss"] * LOSSBACK_PERCENT)
            lossback_msg = f"   🔄 *Thua Tích Lũy* : `{d['total_loss']}` Gay Gem\n"
            lossback_msg += f"   🎁 *Hoàn Trả Tiềm Năng* : `{lossback_value}` Gay Gem (2%)\n"

        msg_text = (
            f"💎 *Tài Khoản Gay Gem Của Bạn* 💎\n\n"
            f"   💸 *Số Dư Nạp (Rút được)* : `{d['xu']}` Gay Gem\n"
            f"   🎁 *Số Dư Code Lộc* : `{d['code_xu']}` Gay Gem\n"
            f"   💵 *Tổng Nạp*: `{d['total_deposit']}` Gay Gem\n"
            f"{lossback_msg}"
            f"   ✨ *TỔNG GIÁ TRỊ ƯỚC TÍNH* : `{vnd_value:,.0f}` VNĐ\n\n"
            f"_Ghi Chú: 1 Gay Gem = {GAYGEM_TO_VND} VNĐ_"
        )
        keyboard = get_main_keyboard(u.id, context)
        
    elif data == 'rut_info':
        msg_text = (
            f"💵 *HƯỚNG DẪN RÚT TIỀN NẠP* 💵\n\n"
            f"Chỉ có *Số Dư Nạp* (tiền nạp và tiền thắng từ cược Nạp) mới được rút.\n"
            f"Cú pháp lệnh trong nhóm chơi:\n"
            f"   `/rut <tên_đại_lý> <gay_gem> <bank> <stk>`\n\n"
            f"   *Ví dụ*: `/rut hungvan07 10000 vietcombank 123456789`\n"
            f"_Đại lý đang hoạt động: {', '.join(AGENTS)}_"
        )
        keyboard = get_main_keyboard(u.id, context)

    elif data == 'help_menu':
        msg_text = (
            f"❓ *HƯỚNG DẪN CÁC LỆNH CHƠI* ❓\n\n"
            f"1. **Cược Nạp**: `/duoi_nap <%> <tiền>`\n"
            f"2. **Cược Lộc**: `/duoi_loc <%> <tiền>`\n"
            f"3. **Rút Tiền**: `/rut <đại_lý> <tiền> <bank> <stk>`\n"
            f"4. **Nhận Code**: `/code <mã_code>`\n\n"
            f"_💡 Chi tiết luật chơi và tỷ lệ, vui lòng gõ_ `/start` _trong nhóm chơi._"
        )
        keyboard = get_main_keyboard(u.id, context)

    elif data == 'status_info':
        d = get_user_data(u.id, context)
        if d["status"] == "Newbie":
            status_info = f"👶 *Tân Thủ* (Giới hạn cược: `{NEWBIE_BET_LIMIT}` Gay Gem/lần)\n"
            deposit_needed = ADULT_DEPOSIT_THRESHOLD - d["total_deposit"]
            status_info += f"_Cần nạp thêm `{deposit_needed}` Gay Gem để trở thành Trưởng thành._"
        else:
            status_info = f"👑 *Trưởng Thành* (Cược không giới hạn)\n"
            status_info += f"_Hoàn trả {int(LOSSBACK_PERCENT*100)}% nếu thua từ `{LOSSBACK_THRESHOLD}` Gay Gem._"

        msg_text = (
            f"🌟 *THÔNG TIN CẤP ĐỘ* 🌟\n\n"
            f"*{status_info}*"
        )
        keyboard = get_main_keyboard(u.id, context)
        
    elif data == 'ref_link':
        ref_id = u.id
        ref_link = f"https://t.me/{context.bot.username}?start=cref_575_{ref_id}"
        
        msg_text = (
            f"🎁 *MỜI BẠN BÈ - NHẬN CODE CỰC KHỦNG!* 🎁\n\n"
            f"Chia sẻ liên kết này để mời bạn bè tham gia:\n"
            f"`{ref_link}`\n\n"
            f"🔥 *ƯU ĐÃI ĐẶC BIỆT*: Khi bạn bè của bạn dùng link này để START bot, bạn sẽ nhận ngay *{REFERRAL_BONUS_LOC} Gay Gem Lộc* vào tài khoản!\n\n"
            f"Sau đó, khi bạn bè của bạn nạp tiền và tham gia chơi, Admin sẽ gửi Code Lộc dành riêng cho bạn! *Mời càng nhiều, Code càng lớn!*"
        )
        keyboard = get_main_keyboard(u.id, context)


    try:
        if msg_text:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=query.message.message_id,
                text=msg_text,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN
            )
    except Exception as e:
        print(f"Lỗi khi chỉnh sửa tin nhắn: {e}")
        pass

# ================== CÁC HÀM LỆNH (Async) ==================
async def sodu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID: return
    d = get_user_data(update.effective_user.id, context)
    tong_xu = d['xu'] + d['code_xu']
    vnd_value = tong_xu * GAYGEM_TO_VND
    
    lossback_msg = ""
    if d["status"] == "Adult" and d["total_loss"] >= LOSSBACK_THRESHOLD:
        lossback_value = int(d["total_loss"] * LOSSBACK_PERCENT)
        lossback_msg = f"   🔄 *Thua Tích Lũy* : `{d['total_loss']}` Gay Gem\n"
        lossback_msg += f"   🎁 *Hoàn Trả Tiềm Năng* : `{lossback_value}` Gay Gem (2%)\n"


    msg = (
        f"💎 *Tài Khoản Gay Gem Của Bạn* 💎\n\n"
        f"   💸 *Số Dư Nạp (Rút được)* : `{d['xu']}` Gay Gem\n"
        f"   🎁 *Số Dư Code Lộc* : `{d['code_xu']}` Gay Gem\n"
        f"   💵 *Tổng Nạp*: `{d['total_deposit']}` Gay Gem\n"
        f"{lossback_msg}"
        f"   ✨ *TỔNG GIÁ TRỊ ƯỚC TÍNH* : `{vnd_value:,.0f}` VNĐ\n\n"
        f"_Ghi Chú: 1 Gay Gem = {GAYGEM_TO_VND} VNĐ_"
    )
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

async def rut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID: return
    u = update.effective_user
    d = get_user_data(u.id, context)

    try:
        agent = context.args[0].lower() 
        amt = int(context.args[1])      
        bank = context.args[2]          
        stk = context.args[3]           
    except:
        await update.message.reply_text(
            f"❗ Cú pháp sai: `/rut <Tên_Đại_Lý> <Gay_Gem> <Ngân_Hàng> <STK>`\n"
            f"_Lưu ý: Số dư Nạp hiện tại: `{d['xu']}`. Tiền thắng cược Lộc phải chuyển sang Nạp trước._", 
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    if agent not in AGENTS:
        await update.message.reply_text(
            f"❌ *Đại lý* `{agent}` *không tồn tại*.", 
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    if amt <= 0 or amt > d["xu"]:
        await update.message.reply_text("❌ *Số dư Gay Gem Nạp không đủ để rút* 🚫", parse_mode=constants.ParseMode.MARKDOWN)
        return

    notification_id = AGENT_NOTIFICATION_ID.get(agent, ADMIN_ID)
    
    d["xu"] -= amt
    name = f"@{u.username}" if u.username else u.full_name
    vnd_value = amt * GAYGEM_TO_VND

    msg_to_admin_agent = (
        f"🚨 *YÊU CẦU RÚT TIỀN NẠP MỚI* 🚨\n\n"
        f"   👨‍💼 *Đại Lý Xử Lý*: `{agent.upper()}`\n"
        f"   👤 *Khách Hàng*: `{name}` (ID: `{u.id}`)\n"
        f"   💰 *Rút*: `{amt}` Gay Gem Nạp\n"
        f"   💵 *Quy Đổi*: `{vnd_value:,.0f}` VNĐ\n"
        f"   🏦 *Ngân Hàng*: `{bank}`\n"
        f"   💳 *STK*: `{stk}`\n\n"
        f"_❗ Vui lòng kiểm tra và chuyển khoản. Dùng lệnh `/duyet {u.id}` để thông báo hoàn tất._"
    )

    msg_to_group = (
        f"⚜️ *YÊU CẦU RÚT TIỀN NẠP ĐÃ GHI NHẬN* ⚜️\n\n"
        f"   👨‍💼 *Qua Đại Lý*: `{agent.upper()}`\n"
        f"   💰 *Số Lượng*: `{amt}` Gay Gem Nạp\n"
        f"   💵 *Giá Trị*: `{vnd_value:,.0f}` VNĐ\n"
        f"   👤 *Người Chơi*: `{name}`\n\n" 
        f"_Yêu cầu đang được xử lý. Vui lòng chờ đợi._"
    )

    sent = await update.message.reply_text(msg_to_group, parse_mode=constants.ParseMode.MARKDOWN)
    await context.bot.pin_chat_message(
        chat_id=update.effective_chat.id,
        message_id=sent.message_id
    )

    try:
        await context.bot.send_message(chat_id=notification_id, text=msg_to_admin_agent, parse_mode=constants.ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(f"⚠️ Không thể gửi tin nhắn cho đại lý. Hãy bảo họ start bot.")

async def xu_ly_cuoc(update: Update, context: ContextTypes.DEFAULT_TYPE, loai_tien):
    if update.effective_chat.id != GROUP_ID: return
    
    global_data = context.application.bot_data
    u = update.effective_user
    d = get_user_data(u.id, context)
    current_bets = global_data["current_bets"]

    try:
        moc = float(context.args[0])
        tien = int(context.args[1])
    except:
        await update.message.reply_text(f"❗ Cú pháp sai: `/duoi_{loai_tien} <%> <Gay_Gem>`", parse_mode=constants.ParseMode.MARKDOWN)
        return

    if moc <= 0 or moc >= 100:
        await update.message.reply_text("❌ % từ 1–99", parse_mode=constants.ParseMode.MARKDOWN)
        return
    
    if d["status"] == "Newbie" and tien > NEWBIE_BET_LIMIT:
        await update.message.reply_text(
            f"❌ *Bạn là Tân Thủ*. Giới hạn cược tối đa là `{NEWBIE_BET_LIMIT}` Gay Gem/lần.\n"
            f"_Vui lòng nạp đủ `{ADULT_DEPOSIT_THRESHOLD}` Gay Gem để trở thành Trưởng thành._", 
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    if loai_tien == 'nap':
        so_du = d["xu"]
        ten_so_du = "Nạp"
    else:
        so_du = d["code_xu"]
        ten_so_du = "Code Lộc"

    if tien <= 0 or tien > so_du:
        await update.message.reply_text(f"❌ Số dư {ten_so_du} không đủ ({so_du}).", parse_mode=constants.ParseMode.MARKDOWN)
        return

    if loai_tien == 'nap':
        d["xu"] -= tien
    else:
        d["code_xu"] -= tien

    hu = int(tien * 0.02)
    tien_thuc = tien - hu
    global_data["HU"] += hu
    
    current_bets[u.id] = (moc, tien_thuc, loai_tien)
    phien_id = global_data["phien_id"]

    msg = (
        f"🎉 *ĐÃ VÀO CƯỢC PHIÊN* #`{phien_id}`\n"
        f"   💰 *Loại Tiền*: *{ten_so_du}*\n"
        f"   🎯 *Dự đoán dưới*: `{moc}`%\n"
        f"   💸 *Cược*: `{tien}` Gay Gem"
    )
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)


async def duoi_nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await xu_ly_cuoc(update, context, 'nap')

async def duoi_loc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await xu_ly_cuoc(update, context, 'loc')

async def l_n(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID: return
    if update.effective_user.id != ADMIN_ID: return
    
    try:
        target_uid = int(context.args[0])
        amt = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Cú pháp: `/l_n <user_id> <số_gay_gem>`", parse_mode=constants.ParseMode.MARKDOWN)
        return
        
    d = get_user_data(target_uid, context)
    
    if amt <= 0 or amt > d["code_xu"]:
        await update.message.reply_text(f"❌ User ID `{target_uid}` không đủ Gay Gem Lộc ({d['code_xu']}) để chuyển.", parse_mode=constants.ParseMode.MARKDOWN)
        return
        
    d["code_xu"] -= amt
    d["xu"] += amt
    
    try:
        target_user = (await context.bot.get_chat_member(GROUP_ID, target_uid)).user
        name = f"@{target_user.username}" if target_user.username else target_user.full_name
    except Exception:
        name = f"ID:{target_uid}"
    
    msg = (
        f"👑 *ADMIN CONFIRM CHUYỂN ĐỔI* 👑\n\n"
        f"   👤 *Người chơi*: `{name}`\n"
        f"   💰 *Số lượng*: `{amt}` Gay Gem\n"
        f"   ➡️ *Lộc* sang *Nạp* thành công."
    )
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

async def taocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    global_data = context.application.bot_data
    
    try:
        amt = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Cú pháp: `/taocode <số_gay_gem>`", parse_mode=constants.ParseMode.MARKDOWN)
        return
    if amt <= 0: return

    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    global_data["gift_codes"][code] = amt
    
    msg = (
        f"🔑 *CODE LỘC ĐÃ TẠO* 🔑\n"
        f"🎁 Mã: `{code}`\n"
        f"💰 Giá trị: `{amt}` Gay Gem"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode=constants.ParseMode.MARKDOWN)
    await update.message.reply_text("✅ *Đã gửi mã code vào tin nhắn riêng cho Admin*.", parse_mode=constants.ParseMode.MARKDOWN)

async def redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID: return
    global_data = context.application.bot_data
    
    try:
        code = context.args[0].upper()
    except IndexError:
        await update.message.reply_text("❗ Cú pháp: `/code <Mã_Code>`", parse_mode=constants.ParseMode.MARKDOWN)
        return
    
    u = update.effective_user
    d = get_user_data(u.id, context)

    if code in global_data["gift_codes"]:
        amt = global_data["gift_codes"].pop(code)
        d["code_xu"] += amt
        msg = (
            f"🎉 *CHÚC MỪNG! NHẬN CODE THÀNH CÔNG* 🎉\n"
            f"🎁 Mã: `{code}`\n"
            f"💰 Cộng: `{amt}` Gay Gem vào Số Dư Code Lộc"
        )
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ *Mã Code không tồn tại hoặc đã hết hạn*.", parse_mode=constants.ParseMode.MARKDOWN)

async def chuyenxu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID: return
    if not update.message.reply_to_message:
        await update.message.reply_text("❗ Hãy Reply tin nhắn người nhận.", parse_mode=constants.ParseMode.MARKDOWN)
        return
    try:
        amt = int(context.args[0])
    except Exception:
        return
        
    sender = update.effective_user
    sd = get_user_data(sender.id, context)
    
    if amt <= 0 or amt > sd["xu"]:
        await update.message.reply_text("❌ Số dư Nạp không đủ.", parse_mode=constants.ParseMode.MARKDOWN)
        return
      
    target = update.message.reply_to_message.from_user
    td = get_user_data(target.id, context)
    
    sd["xu"] -= amt
    td["xu"] += amt
    
    await update.message.reply_text(f"✅ *Đã chuyển* `{amt}` *Gay Gem (Tiền Nạp) thành công!*", parse_mode=constants.ParseMode.MARKDOWN)

async def nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID: return
    if update.effective_user.id != ADMIN_ID: return
    if not update.message.reply_to_message: return
    try:
        amt = int(context.args[0])
        target = update.message.reply_to_message.from_user
        d = get_user_data(target.id, context)
        
        d["xu"] += amt 
        d["total_deposit"] += amt
        
        if d["total_deposit"] >= ADULT_DEPOSIT_THRESHOLD and d["status"] == "Newbie":
            d["status"] = "Adult"
            msg = f"👑 *Admin đã nạp* `{amt}` *Gay Gem Nạp*. *CHÚC MỪNG! Bạn đã trở thành Trưởng Thành!*"
        else:
            msg = f"👑 *Admin đã nạp* `{amt}` *Gay Gem Nạp*"
            
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
    except Exception: pass

async def lichsu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID: return
    global_data = context.application.bot_data
    lich_su = global_data["lich_su"]
    
    if not lich_su:
        await update.message.reply_text("❌ Chưa có lịch sử.", parse_mode=constants.ParseMode.MARKDOWN)
        return
    msg = "📜 *LỊCH SỬ 5 PHIÊN GẦN NHẤT* 📜\n\n"
    for p in lich_su[-5:]:
        msg += f"   🔹 Phiên #`{p['id']}` | KQ: *{p['kq']:.2f}%* | `{p['nguoi']}` người chơi\n"
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

async def chinhh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID: return
    global_data = context.application.bot_data
    
    if update.effective_user.id != ADMIN_ID:
        return 

    try:
        kq_input = float(context.args[0])
        if not (0 <= kq_input <= 100):
            await update.message.reply_text("❌ *Phần trăm phải nằm trong khoảng từ 0 đến 100*.", parse_mode=constants.ParseMode.MARKDOWN)
            return

        global_data["fixed_kq"] = kq_input
        
        time_elapsed = time.time() - global_data["phien_start"]
        time_left = int(PHIEN_TIME - time_elapsed)
        if time_left < 0: time_left = 0 
        phien_id = global_data["phien_id"]

        msg_admin = (
            f"✅ *ĐÃ CỐ ĐỊNH KẾT QUẢ PHIÊN* #`{phien_id}` *thành* `{kq_input}`%.\n"
            f"_Phiên sẽ đóng tự động sau khoảng {time_left} giây nữa (Đã lưu bí mật)_." 
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg_admin, parse_mode=constants.ParseMode.MARKDOWN)
        
        await update.message.reply_text("✅ *Lệnh can thiệp đã được Admin ghi nhận bí mật*.", parse_mode=constants.ParseMode.MARKDOWN)

    except (IndexError, ValueError):
        await update.message.reply_text("❗ Cú pháp: `/chinhh <số_phần_trăm_từ_0_đến_100>`", parse_mode=constants.ParseMode.MARKDOWN)
        return

async def duyet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return

    try:
        target_uid = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Cú pháp: `/duyet <user_id>` (ID người chơi đã rút tiền).", parse_mode=constants.ParseMode.MARKDOWN)
        return
    
    try:
        target_user = (await context.bot.get_chat_member(GROUP_ID, target_uid)).user
        name = f"@{target_user.username}" if target_user.username else target_user.full_name
    except Exception:
        name = f"ID: `{target_uid}`"

    msg_to_community = (
        f"✅ *THÔNG BÁO XỬ LÝ RÚT TIỀN THÀNH CÔNG* ✅\n\n"
        f"   🎉 *Chúc Mừng* `{name}` *!* 🎉\n"
        f"   💸 *Yêu cầu rút tiền của bạn đã được Admin duyệt và hoàn tất chuyển khoản!* \n\n"
        f"👉 _Tiếp tục chiến thắng tại_ @ctbmnnn"
    )
    
    try:
        await context.bot.send_message(
            chat_id=REQUIRED_GROUPS["Cộng đồng"], 
            text=msg_to_community, 
            parse_mode=constants.ParseMode.MARKDOWN
        )
        await update.message.reply_text(f"✅ *Đã thông báo duyệt rút tiền của {name} lên nhóm Cộng đồng.*", parse_mode=constants.ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ *Lỗi khi thông báo lên nhóm Cộng đồng* (ID: `{REQUIRED_GROUPS['Cộng đồng']}`). Kiểm tra quyền Admin của bot.", parse_mode=constants.ParseMode.MARKDOWN)


async def hoantra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID: return
    if update.effective_user.id != ADMIN_ID: return
    
    try:
        target_uid = int(context.args[0])
        ghi_chu = " ".join(context.args[1:])
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Cú pháp: `/hoantra <user_id> <ghi_chu>`", parse_mode=constants.ParseMode.MARKDOWN)
        return
        
    try:
        target_user = (await context.bot.get_chat_member(GROUP_ID, target_uid)).user
        name = f"@{target_user.username}" if target_user.username else target_user.full_name
    except Exception:
        name = f"ID:{target_uid}"
        
    msg = (
        f"🚨 *YÊU CẦU RÚT TIỀN HOÀN TRẢ/TỪ CHỐI* 🚨\n\n"
        f"   👤 *Người chơi*: `{name}` (ID: `{target_uid}`)\n"
        f"   ❌ *Lý do*: {ghi_chu}\n\n"
        f"_❗ Admin đã hoàn trả tiền vào tài khoản Nạp của bạn hoặc xử lý theo hình thức khác._"
    )
    
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
    
    try:
        await context.bot.send_message(target_uid, msg, parse_mode=constants.ParseMode.MARKDOWN)
    except Exception:
        pass 


async def phien_timer(context: ContextTypes.DEFAULT_TYPE):
    global PHIEN_TIME, GROUP_ID
    global_data = context.application.bot_data
    
    time_left = context.job.data["time_left"]
    chat_id = context.job.data["chat_id"]
    phien_id = global_data["phien_id"]
    timer_messages = global_data["timer_messages"]

    if time_left == 15:
        msg_text = f"⏱️ *15 GIÂY CUỐI CÙNG PHIÊN* #`{phien_id}`!"
    elif time_left == 10: 
        msg_text = f"🔟 *10 GIÂY! HÃY VÀO CƯỢC NGAY* #`{phien_id}`!"
    elif time_left == 5:
        msg_text = f"⏳ *5 GIÂY! SẮP ĐÓNG PHIÊN* #`{phien_id}` 🚨"
    else:
        return

    m = await context.bot.send_message(chat_id, msg_text, parse_mode=constants.ParseMode.MARKDOWN)
    timer_messages[time_left] = m.message_id
    
    if time_left == 10 and 15 in timer_messages:
        try: await context.bot.delete_message(chat_id, timer_messages.pop(15))
        except Exception: pass
    elif time_left == 5 and 10 in timer_messages:
        try: await context.bot.delete_message(chat_id, timer_messages.pop(10))
        except Exception: pass

def schedule_next_phien(application: Application):
    global PHIEN_TIME, GROUP_ID
    global_data = application.bot_data
    phien_id = global_data["phien_id"]
    jq = application.job_queue
    
    jq.run_once(ket_thuc, PHIEN_TIME, name=f"ket_thuc_{phien_id}")
    
    jq.run_once(phien_timer, PHIEN_TIME - 15, data={"chat_id": GROUP_ID, "time_left": 15}, name=f"t15_{phien_id}")
    jq.run_once(phien_timer, PHIEN_TIME - 10, data={"chat_id": GROUP_ID, "time_left": 10}, name=f"t10_{phien_id}")
    jq.run_once(phien_timer, PHIEN_TIME - 5, data={"chat_id": GROUP_ID, "time_left": 5}, name=f"t5_{phien_id}")


async def ket_thuc(context: ContextTypes.DEFAULT_TYPE):
    global ADULT_DEPOSIT_THRESHOLD, LOSSBACK_THRESHOLD, LOSSBACK_PERCENT, GROUP_ID
    
    global_data = context.application.bot_data
    current_bets = global_data["current_bets"]
    phien_id = global_data["phien_id"]
    timer_messages = global_data["timer_messages"]
    
    if 5 in timer_messages:
        try: await context.bot.delete_message(GROUP_ID, timer_messages.pop(5))
        except Exception: pass
    timer_messages.clear()
    
    is_fixed = (global_data["fixed_kq"] is not None)
    
    if is_fixed:
        kq = global_data["fixed_kq"]
        global_data["fixed_kq"] = None
        msg_header = f"✨ *KẾT QUẢ PHIÊN* #`{phien_id}` (Admin Fixed) ✨\n"
    else:
        ranges = [(0, 50), (50, 100)]
        weights = [1.0, 1.0] 
        selected_range = random.choices(ranges, weights=weights, k=1)[0]
        kq = random.uniform(selected_range[0], selected_range[1])
        msg_header = f"✨ *KẾT QUẢ PHIÊN* #`{phien_id}` ✨\n"
        
    msg = msg_header + f"🔮 *CON SỐ*: `{kq:.2f}`%\n\n"
    
    if current_bets:
        details = ""
        for uid, (moc, tien, loai_tien) in current_bets.items(): 
            try: u = (await context.bot.get_chat_member(GROUP_ID, uid)).user 
            except Exception: name = f"ID:{uid}"
            else: name = f"@{u.username}" if u.username else u.full_name
            
            d = get_user_data(uid, context)
            
            is_win = False
            win_amount = 0
            
            if moc == 1 and kq < 1:
                win_amount = global_data["HU"] + tien
                d["xu"] += win_amount 
                global_data["HU"] = 0
                details += f"   💥 *{name}* (Nạp/Lộc) | NỔ HŨ | +`{win_amount}` Gay Gem Nạp\n"
                is_win = True
            elif kq < moc:
                hs = tinh_ty_le(moc)
                win_amount = int(tien * hs)
    
                if loai_tien == 'nap':
                    d["xu"] += win_amount 
                    loai_nhan = "Nạp"
                else: 
                    d["code_xu"] += win_amount
                    loai_nhan = "Lộc"
                    
                details += f"   ✅ *{name}* ({loai_tien.upper()}) | ĂN | +`{win_amount}` Gay Gem {loai_nhan}\n"
                is_win = True
            else:
                details += f"   ❌ *{name}* ({loai_tien.upper()}) | Tạch (`{tien}`)\n"
                is_win = False

            if not is_win and loai_tien == 'nap':
                d["total_loss"] += (tien - int(tien * 0.02))
               
            lossback_msg = ""
            if d["status"] == "Adult" and d["total_loss"] >= LOSSBACK_THRESHOLD:
                lossback_value = int(d["total_loss"] * LOSSBACK_PERCENT)
                if lossback_value > 0:
                    d["xu"] += lossback_value
                    d["total_loss"] = 0
                    lossback_msg = f"\n   💰 *HOÀN TRẢ 2%*: +`{lossback_value}` Gay Gem Nạp!"
    
            details += lossback_msg
            
        msg += details
    else:
        msg += "⚠️ _Không có người chơi._\n"

    msg += f"\n💰 *HŨ*: `{global_data['HU']}` Gay Gem"
    
    await context.bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode=constants.ParseMode.MARKDOWN)

    global_data["lich_su"].append({"id": phien_id, "kq": kq, "nguoi": len(current_bets)})
    if len(global_data["lich_su"]) > 5: global_data["lich_su"].pop(0)

    global_data["current_bets"].clear()
    global_data["phien_id"] += 1
    global_data["phien_start"] = time.time()
    
    schedule_next_phien(context.application)


# ================== MAIN (ĐÃ ĐIỀU CHỈNH RUN_WEBHOOK VÀ SỬA LỖI PERSISTENCE) ==================
def main() -> None:
    # 1. >>> KHỞI TẠO PERSISTENCE (ĐÃ FIX TẤT CẢ LỖI CÚ PHÁP) <<<
    # Chỉ truyền filepath và store_data=True là cách ổn định nhất với PTB V20+
    persistence = PicklePersistence(
        filepath="bot_data.pkl", 
        store_data=True
    )
    
    # Khởi tạo Application, truyền Persistence vào
    application = Application.builder().token(TOKEN).persistence(persistence).build()
    
    # 2. Khởi tạo dữ liệu toàn cục nếu tệp Persistence chưa tồn tại 
    if not application.bot_data:
        application.bot_data.update(GLOBAL_DATA)
    
    # 3. Khai báo Handlers (giữ nguyên)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sodu", sodu))
    application.add_handler(CommandHandler("rut", rut))
    application.add_handler(CommandHandler("duyet", duyet))
    application.add_handler(CommandHandler("duoi_nap", duoi_nap)) 
    application.add_handler(CommandHandler("duoi_loc", duoi_loc)) 
    application.add_handler(CommandHandler("l_n", l_n)) 
    
    application.add_handler(CommandHandler("lichsu", lichsu_cmd))
    application.add_handler(CommandHandler("taocode", taocode))
    application.add_handler(CommandHandler("code", redeem_code))
    application.add_handler(CommandHandler("chuyenxu", chuyenxu))
    application.add_handler(CommandHandler("nap", nap))
    application.add_handler(CommandHandler("hoantra", hoantra)) 
    
    application.add_handler(CommandHandler("chinhh", chinhh_cmd)) 

    application.add_handler(CallbackQueryHandler(button_callback))

    # 4. Lên lịch cho phiên đầu tiên 
    if not application.job_queue.get_jobs_by_name(name=f"ket_thuc_{application.bot_data.get('phien_id', 1)}"):
        schedule_next_phien(application)

    # 5. >>> KHỞI ĐỘNG BOT DƯỚI DẠNG WEBHOOK CHO RAILWAY <<<
    
    # Lấy các biến môi trường
    try:
        WEBHOOK_TOKEN = os.getenv("TOKEN")
        WEBHOOK_PORT = int(os.environ.get("PORT", "8080")) 
        
        # Lấy tên miền do Railway cung cấp tự động 
        RAILWAY_APP_DOMAIN = os.environ.get("RAILWAY_STATIC_URL") 
        
        if not RAILWAY_APP_DOMAIN:
            # Fallback nếu biến không tồn tại
            print("⚠️ CẢNH BÁO: RAILWAY_STATIC_URL không tồn tại, sử dụng tên miền mẫu. HÃY KIỂM TRA LẠI RAILWAY.")
            # Bạn cần lấy tên miền thực tế từ Railway và thay vào dòng dưới nếu lỗi:
            RAILWAY_APP_DOMAIN = "your-app-name-production.up.railway.app" 
        
        WEBHOOK_URL = f"https://{RAILWAY_APP_DOMAIN}/{WEBHOOK_TOKEN}"

    except Exception as e:
        print(f"Lỗi khi lấy biến môi trường: {e}")
        sys.exit(1) 

    print("👑 BOT GAY GEM ĐANG CHẠY (FINAL CONFIG: WEBHOOK, PERSISTENCE FIX)...")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=WEBHOOK_PORT,
        url_path=WEBHOOK_TOKEN,  # Sử dụng Token làm url_path để bảo mật
        webhook_url=WEBHOOK_URL,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
