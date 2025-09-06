
# Project-Siesta
![GitHub Repo stars](https://img.shields.io/github/stars/vinayak-7-0-3/Project-Siesta?style=for-the-badge)
![GitHub forks](https://img.shields.io/github/forks/vinayak-7-0-3/Project-Siesta?style=for-the-badge)
![Docker Pulls](https://img.shields.io/docker/pulls/weebzbots/project-siesta?style=for-the-badge)
[![Static Badge](https://img.shields.io/badge/support-pink?style=for-the-badge)](https://t.me/weebzgroup)

AIO Bot for your music needs on Telegram.

Note: This is not a music streaming / VC Bot

## FEATURES

**Currently the project is in early development stage and features are incomplete**

Feels free to check the repo and report bugs / features

**A complete guide for ~~downloading~~ (coughs..) ehmm.... can be found [here](https://rentry.org/project-siesta)**

## INSTALLATION


#### 1) LOCAL DEPLOYMENT

**Requirements**
- Python>=3.10 (3.12 recommended) 
- Git installed (optional)
- Rclone (optional)
- ffmpeg (optional)

**Steps**
- Git clone (or download) the repo
- Create virtual environment and run
```
virtualenv -p python3 VENV
. ./VENV/bin/activate
```
- Edit and fill out the essentials environment variables in `sample.env` (refer [here](#variables-info))
- Rename `sample.env` to `.env`
- Finally run
```
pip install -r requirements.txt
python -m bot
```

#### 2) USING DOCKER (Manual Build)
**Requirements**
- Git installed (optional)
- Of course Docker installed (how would ya do docker method without docker  🤷‍)

**Steps**
- Git clone (or download) the repo
- Fill out the required variables in `sample.env` (refer [here](#variables-info))
- Build the image using the Docker build command
```
sudo docker build . -t project-siesta
```
- Now run the created Docker image
```
sudo docker run -d --env-file sample.env --name siesta project-siesta
```
- At this point your bot will be running (if everything correct)

#### 3) USING DOCKER (Prebuilt Image)

Premade Docker Images are available at Dockerhub repo `weebzbots/project-siesta`
These images are made using GitHub Actions
- Supported architectures
	- `arm64`
	- `amd64`
- Build Tags
	- `latest` - Latest stable releases from main branch
	- `beta` - Latest beta releases from beta branch (early feature testing)
	- `<commit-hash>` - You can use specific commit hash for specific versions

**Requirements**
- Of course Docker installed (how would ya do docker method without docker  🤷‍)

**Steps**
- Pull the Docker image
```
sudo docker pull weebzcloud/project-siesta
```
- Somewhere in your server, create a `.env` file with required variables (refer [here](#variables-info))
- Run the image
```
sudo docker run -d --env-file .env --name siesta project-siesta
```
- At this point your bot will be running (if everything correct)

## VARIABLES INFO

#### ESSENTIAL VARIABLES
- `TG_BOT_TOKEN` - Telegeam bot token (get it from [BotFather](https://t.me/BotFather))
- `APP_ID` - Your Telegram APP ID (get it from my.telegram.org) `(int)`
- `API_HASH` - Your Telegram APP HASH (get it from my.telegram.org) `(str)`
- `DATABASE_URL` - Postgres database URL (self hosted or any service) `(str)`
- `BOT_USERNAME` - Your Telegram Bot username (with or without `@`) `(str)`
- `ADMINS` - List of Admin users for the Bot (seperated by space) `(str)`

#### OPTIONAL VARIABLES
- `DOWNLOAD_BASE_DIR` - Downloads folder for the bot (folder is inside the working directory of bot) `(str)`
- `LOCAL_STORAGE` - Folder (full path needed) where you want to store the downloaded file the server itself rather than uploading `(str)`
- `RCLONE_CONFIG` - Rclone config as text or URL to file (can ignore this if you add file manually to root of repo) `(str)`
- `RCLONE_DEST` - Rclone destination as `remote-name:folder-in-remote` `(str)`
- `INDEX_LINK` - If index link needed for Rclone uploads (testes with alist) (no trailing slashes `/` ) `(str)`
- `MAX_WORKERS` - Multithreading limit (kind of more speed) `(int)`
- `TRACK_NAME_FORMAT` - Naming format for tracks (check [metadata](https://github.com/vinayak-7-0-3/Project-Siesta/blob/2bbea8572d660a92bb182a360e91791583f4523b/bot/helpers/metadata.py#L16) section for tags supported) `(str)`
- `PLAYLIST_NAME_FORMAT` - Similar to `TRACK_NAME_FORMAT` but for Playlists (Note: all tags might not be available) `(str)`
- `TIDAL_NG_DOWNLOAD_PATH` - Overrides the download path for the Tidal NG provider. If set, all Tidal NG downloads will be saved here, bypassing other settings. `(str)`

## CREDITS
- OrpheusDL - https://github.com/yarrm80s/orpheusdl
- Streamrip - https://github.com/nathom/streamrip
- yaronzz - Tidal-Media-Downloader - https://github.com/yaronzz/Tidal-Media-Downloader
- vitiko98 - qobuz-dl - https://github.com/vitiko98/qobuz-dl

## Support Me ❤️
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/I2I7FWQZ4)

TON - `UQBBPkWSnbMWXrM6P-pb96wYxQzLjZ2hhuYfsO-N2pVmznCG`

## Tidal NG Downloader (Beta)

This bot features a modern, robust backend for handling Tidal downloads, referred to as "Tidal NG" (Next Generation). It operates by interfacing with a powerful external command-line tool, `tidal-dl-ng`.

### How It Works

Unlike the legacy provider which used a Python library directly, the Tidal NG handler acts as a smart controller for the `tidal-dl-ng` CLI tool. When you request a Tidal download:
1.  The bot determines the correct, isolated directory for the current download task.
2.  It programmatically modifies the `tidal-dl-ng` tool's own `settings.json` file to set the `download_base_path` and any user-specific settings.
3.  It executes the CLI tool (`python cli.py dl <URL>`), which then downloads the music to the location specified by the bot.
4.  After the download is complete or fails, the bot restores the `settings.json` file to its original state to ensure system integrity.

**Note on First Use**: The configuration directory (`/root/.config/tidal_dl_ng/`) and `settings.json` file for the tool are created automatically the first time you use any Tidal NG feature. No manual setup is required.

### Configuration & Settings

The Tidal NG provider is highly configurable directly from the bot's settings menu. All settings are saved on a per-user basis.

-   **Accessing Settings**: Navigate to `/settings` -> `Provider Settings` -> `Tidal NG`. This will open the main settings panel, which is organized into the following sub-menus.

-   **Available Settings**:
    -   **Audio Settings**:
        -   `Audio Quality`: Choose your preferred audio quality (`LOW`, `HIGH`, `LOSSLESS`, `HI_RES_LOSSLESS`).
        -   `Replay Gain`: Toggle whether to write replay gain information to metadata.
    -   **Metadata Settings**:
        -   `Embed Lyrics`: Toggle embedding lyrics into the audio file.
        -   `Save Lyrics File`: Toggle saving lyrics to a separate `.lrc` file.
        -   `Cover Art Dimension`: Choose the resolution for embedded cover art (`320px`, `640px`, `1280px`).
    -   **File Settings**:
        -   `Create .m3u8 Playlist`: Toggle the creation of a `.m3u8` playlist file for albums and playlists.
        -   `Symlink to Track`: Toggle whether to download tracks to a central folder and create symlinks.
    -   **Video Settings**:
        -   `Download Videos`: Toggle whether to download videos at all.
        -   `Convert Videos to MP4`: Toggle automatic conversion of video files to MP4.
        -   `Video Quality`: Choose your preferred video download quality (`360p`, `480p`, `720p`, `1080p`).
    -   **Login/Logout**: Manage your `tidal-dl-ng` session from the main panel.
    -   **Import Config File**: For advanced users, this allows you to upload any configuration file (e.g., `token.json`, `settings.json`) directly into the Tidal NG configuration directories.
        -   **How it works:** When you click the button, the bot will ask you to choose a destination:
            -   **`main config (tidal_dl_ng)`**: Saves the file to `/root/.config/tidal_dl_ng/`. This is the standard directory used by the tool.
            -   **`dev config (tidal_dl_ng-dev)`**: Saves the file to `/root/.config/tidal_dl_ng-dev/`. This can be used for development or testing purposes.
        -   **Note:** If the chosen directory does not exist, the bot will ask for your permission to create it before proceeding. This feature provides a quick way to manage or update any custom configuration files for the `tidal-dl-ng` tool.

-   **Download Path**: The download location is determined by a 3-level priority system:
    1.  **Environment Variable (Highest Priority)**: If you set `TIDAL_NG_DOWNLOAD_PATH` in your `.env` file, it will be used for all downloads, overriding all other settings.
    2.  **Imported Settings File**: If the environment variable is not set, the bot checks the `settings.json` you may have imported. If the `download_base_path` in that file is set to a custom value, the bot will respect it.
    3.  **Bot Default (Lowest Priority)**: If neither of the above are set, the bot will create a unique directory for each task: `<DOWNLOAD_BASE_DIR>/<user_id>/<task_id>/`.

## Apple Wrapper Controls (Apple Music)

- **Location**: `Settings -> Providers -> Apple Music`
- **Buttons**:
  - `🧩 Setup Wrapper`: Starts an interactive setup that asks for your Apple ID username and password, then runs the wrapper setup script with those credentials. If 2FA is required, the bot will detect it and prompt you to send the 2FA code, then continues automatically.
  - `⏹️ Stop Wrapper`: Stops any running wrapper process. Includes a confirmation step to prevent accidental taps.

### How Setup Works
1. Tap `🧩 Setup Wrapper`.
2. Send your Apple ID username when asked.
3. Send your Apple ID password when asked.
4. The bot runs the setup script with `USERNAME` and `PASSWORD` exported in the environment, equivalent to:
   ```bash
   USERNAME="your_username" PASSWORD="your_password" /usr/src/app/downloader/setup_wrapper.sh
   ```
5. If the wrapper requests 2FA, you will see a prompt. Send the 2FA code as a normal message within 3 minutes.
6. On success, you'll get a confirmation. On failure, the last part of the script output is shown for debugging.

### How Stop Works
- Tap `⏹️ Stop Wrapper` -> Confirm. The bot runs:
  ```bash
  /usr/src/app/downloader/stop_wrapper.sh
  ```
- It kills wrapper processes and frees ports 10020/20020.

### Configuration
- Override script paths with env vars if needed:
  - `APPLE_WRAPPER_SETUP_PATH` (default `/usr/src/app/downloader/setup_wrapper.sh`)
  - `APPLE_WRAPPER_STOP_PATH` (default `/usr/src/app/downloader/stop_wrapper.sh`)

### Notes & Security
- Credentials are only used to start the setup process and are not stored by the bot.
- You can cancel the flow any time by sending `/cancel`.
- If 2FA prompt does not appear (rare), setup continues and completes automatically.

## Commands and Usage

These commands work in any chat where the bot is present. Copy-paste directly into Telegram.

- /start: Show welcome message
- /help: Show available commands
- /settings: Open settings panel
- /download <url> [--options]: Start a download for a supported provider
This build is Apple Music–only. Qobuz, Tidal, and Deezer integrations have been removed. Use Apple Music links like `https://music.apple.com/...`.
  - Examples:
    - ```
/download https://music.apple.com/…
    ```
    - ```
/download --alac-max 192000 https://music.apple.com/…
    ```
    - Reply to a message containing the link and send:
      ```
/download --atmos
      ```
  - On start, the bot replies with a Task ID. Use it to manage the task.
- Queue Mode (sequential downloads/uploads):
  - Turn on: Settings → Core → Queue Mode: ON
  - While ON, /download does not start immediately; it enqueues and replies with a Queue ID and position.
  - See your queue: use /qqueue (alias /queue) or Settings → Core → Open Queue Panel
  - Cancel a queued link: /qcancel <queue_id> or use the ❌ button in Queue Panel
  - Cancel the currently running job: /cancel <task_id>
- /cancel <task_id>: Cancel a specific running task by its ID
  - Example:
    ```
/cancel ab12cd34
    ```
- /cancel_all: Cancel all your running tasks (download, zipping, uploading)
  - Example:
    ```
/cancel_all
    ```

### What happens on cancel
- The bot stops the active step (downloading, zipping, uploading)
- Any partial files/archives are cleaned up automatically
- The progress message is updated to indicate cancellation

### Realtime system usage in progress
- Progress messages now include CPU, RAM, and Disk usage to help monitor server load while tasks run.

## Apple Music Config (config.yaml) via Telegram

Admins can view and edit `/root/amalac/config.yaml` in real time. Changes are written safely with a backup created each time.

Path override: set env `APPLE_CONFIG_YAML_PATH` to a different file if needed.

### Commands

- /config or /cfg: Show quick help and path
- /config_show [keys...]: Show current values for a curated list or specific keys
- /config_get <key>: Show current value of a key (sensitive values are masked)
- /config_set <key> <value>: Set key to value (with validation where applicable)
- /config_toggle <bool-key>: Toggle a boolean key between true/false

### Supported Keys and Validation

- Choice keys:
  - lrc-type: lyrics | syllable-lyrics
  - lrc-format: lrc | ttml
  - cover-format: jpg | png | original
  - mv-audio-type: atmos | ac3 | aac
- Boolean keys:
  - embed-lrc
  - save-lrc-file
  - save-artist-cover
  - save-animated-artwork
  - emby-animated-artwork
  - embed-cover
  - dl-albumcover-for-playlist
- Integer keys:
  - mv-max (e.g., 2160)
- Sensitive keys (masked in outputs; will be auto-quoted on set):
  - media-user-token
  - authorization-token

Other common keys you can set directly with /config_set:
- cover-size (e.g., `5000x5000`)
- alac-save-folder, atmos-save-folder, aac-save-folder (folders are auto-created if missing)
- alac-max, atmos-max, aac-type, storefront, language

### Examples

```text
/config_show
/config_get storefront
/config_set storefront in
/config_set lrc-type lyrics
/config_set lrc-format lrc
/config_toggle embed-lrc
/config_toggle save-artist-cover
/config_set cover-format png
/config_set cover-size 5000x5000
/config_set mv-audio-type atmos
/config_set mv-max 2160
/config_set media-user-token "<your_token_here>"
/config_set alac-save-folder "/usr/src/app/bot/DOWNLOADS/5329535193/Apple Music/alac"
```

Note: If the Apple downloader runs persistently, restart it after updating critical values (tokens, formats) so it reloads the file.

## BotFather command list (copy-paste)

```text
start - Start the bot
help - Show help
settings - Open settings panel
download - Start a download
queue - Show your queue
qqueue - Show your queue (alias)
qcancel - Cancel a queued item by Queue ID
cancel - Cancel a running task by ID
cancel_all - Cancel all your running tasks
config - Config help for Apple Music YAML
config_show - Show config values (or specific keys)
config_get - Get a single config value
config_set - Set a config value
config_toggle - Toggle a boolean config value
log - Get the bot log
auth - Authorize a user or chat
ban - Ban a user or chat
```