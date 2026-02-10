# utils/decorators.py
from functools import wraps
import config

def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config.ALLOWED_USERS:
            print(f"Unauthorized access denied for {user_id}.")
            # Tambahkan await di sini juga!
            await update.message.reply_text(
                f"🚫 Akses Ditolak. ID Anda ({user_id}) tidak terdaftar."
            )
            return # Ini akan mengembalikan None, dan itu tidak apa-apa
        
        # WAJIB ada return await di sini
        return await func(update, context, *args, **kwargs)
    return wrapped