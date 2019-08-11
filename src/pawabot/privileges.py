from privibot import Privilege
from privibot import Privileges as Ps


class Privileges(Ps):
    DOWNLOADER = Privilege(
        "downloader",
        "Downloader",
        "This privilege allows users to request downloads, either through a search or by sending a magnet to the bot. "
        "Another privilege, 'Verified Downloader', allows users to automatically start downloads "
        "without requiring validation by administrators.",
    )
    VERIFIED_DOWNLOADER = Privilege(
        "verified_downloader",
        "Verified Downloader",
        "This privilege allows users to automatically start downloads without requiring validation by administrators.",
    )
    MEDIA_MANAGER = Privilege(
        "media_manager",
        "Media Manager",
        "This privilege allows users to act (accept or reject) on media-related requests.",
    )
    USER_MANAGER = Privilege(
        "user_manager", "User Manager", "This privilege allows users to manage access of other users to the bot."
    )
    TESTER = Privilege("tester", "Tester", "This privilege allows users to test new things.")
