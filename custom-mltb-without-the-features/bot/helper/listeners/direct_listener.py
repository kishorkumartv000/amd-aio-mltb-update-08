from ... import LOGGER


class DirectListener:
    def __init__(self, path, listener, a2c_opt):
        self.listener = listener
        self._path = path
        self._a2c_opt = a2c_opt
        self._proc_bytes = 0
        self._failed = 0
        self.download_task = None
        self.name = self.listener.name

    @property
    def processed_bytes(self):
        return 0

    @property
    def speed(self):
        return 0

    async def download(self, contents):
        LOGGER.error("Direct download requires aria2c, which has been removed.")
        await self.listener.on_download_error(
            "Direct download functionality has been removed."
        )

    async def cancel_task(self):
        self.listener.is_cancelled = True
        LOGGER.info(f"Cancelling Download: {self.listener.name}")
        await self.listener.on_download_error("Download Cancelled by User!")
