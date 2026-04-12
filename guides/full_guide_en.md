# [START OF SECTION: API_KEY]

### 🔑 How to Choose a Backend and Set an API Key

The bot supports two backends: **Google Gemini** and **OpenAI**.

An API key is your personal access credential for the selected AI service. The bot encrypts and stores your key and does not share it with third parties.

#### Step by Step

1. **Open `/settings`** and choose a backend:
   * `Google Gemini`
   * `OpenAI`

2. **Send the `/set_api_key` command**.

3. **Send the key for the currently selected backend**:
   * For Gemini: a key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   * For OpenAI: a key from your OpenAI account

4. After verification, the bot will save the key and let you choose a model in `/settings`.

#### If you use Gemini

1. Go to [Google AI Studio](https://makersuite.google.com/app).
2. Open **Get API key**.
3. Create a key and copy it.
4. Return to the bot and send it via `/set_api_key`.

#### If you use OpenAI

1. Open your OpenAI account dashboard.
2. Create a new API key.
3. Copy the key.
4. Return to the bot and send it via `/set_api_key`.

# [END OF SECTION: API_KEY]

---

# [START OF SECTION: FEATURES]

### 🚀 Bot Features

After setting an API key, you get access to the following features:

#### 🧠 Main Chat
Just type your questions or tasks. The bot keeps conversation context within the active dialog.

#### 🖼️ Image Analysis
Send an image as a photo. Image analysis works for both Gemini and OpenAI.

#### 🗂️ Dialog Management (`/dialogs`)
The bot supports multiple independent conversations.
* **Create:** Click “➕ Create New”.
* **Switch:** Click a dialog name.
* **Rename:** Use the “✏️” button.
* **Delete:** Use the “❌” button for an inactive dialog.

#### 📜 Message History (`/history`)
You can view the history for the current active dialog on a selected date.

#### 📊 Usage Statistics (`/usage`)
Shows token usage for today and this month, the active backend, the current model, and estimated cost where pricing is configured.

#### 👤 My Account (`/account`)
Shows your profile, active backend, current model, message count, and a short analysis of topics in the current dialog.

#### 🎙️ Voice Messages
* For Gemini: supported.
* For OpenAI: not supported yet.

# [END OF SECTION: FEATURES]

---

# [START OF SECTION: SETTINGS]

### ⚙️ Settings (`/settings`)

Use this menu to configure the bot.

#### 🧠 Backend
First choose which backend should power replies:
* `Google Gemini`
* `OpenAI`

#### 🤖 Model
After choosing a backend and setting an API key, you can choose a model available for that backend.

#### 🎭 Persona
A persona defines the assistant role: Python expert, historian, copywriter, etc.

#### 👔 Communication Style
Applies to the default assistant persona and controls the tone of replies.

#### 🌐 Interface Language
Switches button and system message language between Russian and English.

# [END OF SECTION: SETTINGS]
