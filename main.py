import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Get the bot token from environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in .env file")

# Configure download path
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import extractor modules
from extractors.youtube import extract_youtube
from extractors.instagram import extract_instagram
from extractors.tiktok import extract_tiktok
from extractors.generic import extract_generic

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Hi! I'm a media downloader bot. Send me a link from YouTube, Instagram, TikTok, or other platforms."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Just send me a link to download media from. I support:\n"
        "- YouTube videos\n"
        "- Instagram photos and videos\n"
        "- TikTok videos\n"
        "- Many other platforms\n\n"
        "Simply paste the URL and I'll try to download the media for you!"
    )
    await update.message.reply_text(help_text)

async def process_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process URLs and download media."""
    url = update.message.text
    
    # Simple URL validation
    if not is_valid_url(url):
        await update.message.reply_text("Please send a valid URL")
        return
    
    await update.message.reply_text("Processing your request, please wait...")
    
    try:
        # Determine which extractor to use based on the URL
        domain = urlparse(url).netloc.lower()
        
        if "youtube.com" in domain or "youtu.be" in domain:
            await extract_and_send(update, url, extract_youtube)
        elif "instagram.com" in domain:
            await extract_and_send(update, url, extract_instagram)
        elif "tiktok.com" in domain:
            await extract_and_send(update, url, extract_tiktok)
        else:
            # Try generic extractor for unsupported sites
            await extract_and_send(update, url, extract_generic)
    
    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        await update.message.reply_text(f"Error processing your request: {str(e)}")

async def extract_and_send(update: Update, url: str, extractor_func) -> None:
    """Extract media and send it to the user."""
    try:
        # Get media info and path from the appropriate extractor
        media_info = await extractor_func(url, DOWNLOAD_PATH)
        
        if not media_info:
            await update.message.reply_text("Could not extract media from this URL.")
            return
        
        # Send the media based on its type
        if media_info["type"] == "video":
            if media_info["file_size"] > int(os.getenv("MAX_FILE_SIZE", 50000000)):  # Default 50MB limit
                await update.message.reply_text(
                    f"Video is too large to send via Telegram. Download link: {media_info.get('direct_url', 'Not available')}"
                )
            else:
                await update.message.reply_video(
                    video=media_info["file_path"],
                    caption=media_info["caption"],
                    supports_streaming=True
                )
        elif media_info["type"] == "photo":
            await update.message.reply_photo(
                photo=media_info["file_path"],
                caption=media_info["caption"]
            )
        elif media_info["type"] == "audio":
            await update.message.reply_audio(
                audio=media_info["file_path"],
                caption=media_info["caption"]
            )
        else:
            await update.message.reply_document(
                document=media_info["file_path"],
                caption=media_info["caption"]
            )
        
        # Clean up the downloaded file to save space
        if os.path.exists(media_info["file_path"]):
            os.remove(media_info["file_path"])
    
    except Exception as e:
        logger.error(f"Error sending media: {e}")
        await update.message.reply_text(f"Error sending media: {str(e)}")

def is_valid_url(url: str) -> bool:
    """Check if the string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_url))

    # Run the bot until the user presses Ctrl-C
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()