\# Voice Changer App Tutorial

Simple voice effects application for recording and modifying audio\.

\## Installation

\`\`\`bash
pip install tkinter sounddevice numpy librosa scipy praat\-parselmouth
\`\`\`

\## Quick Start

\### 1\. Record Audio
\- Set duration in seconds
\- Click "Record Audio"
\- Use Pause/Stop to control recording

\### 2\. Apply Effects
\- \*\*Pitch Shift\*\*: Make voice higher/lower (\-5 to \+5)
\- \*\*Formant Shift\*\*: Change voice character (0\.5 to 2\.0)
\- \*\*Tempo\*\*: Speed up/slow down speech (0\.5 to 2\.0)
\- \*\*Distortion\*\*: Add roughness (0\.0 to 0\.5)
\- \*\*Volume\*\*: Adjust loudness (0\.5 to 2\.0)

\### 3\. Process & Save
\- Select recorded file from dropdown
\- Adjust effect sliders
\- Click "Edit and Save"
\- Find output in \`edited/\` folder

\## Presets
\- Save current settings: "Save Preset"
\- Load saved settings: Select from dropdown
\- Delete presets: Click "X" button

\## Popular Effects
\- \*\*Robot Voice\*\*: Pitch \+4, Distortion 0\.3
\- \*\*Deep Voice\*\*: Pitch \-4, Formant 0\.7
\- \*\*Chipmunk\*\*: Pitch \+5, Tempo 1\.8

\## Run App
\`\`\`bash
python voice\_changer\.py
\`\`\`

Files saved as \`recorded/record\_timestamp\.wav\` and \`edited/edited\_filename\.wav\`
