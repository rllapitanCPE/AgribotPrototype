AgribotPrototyping - Design Phase

To get your groupmates set up exactly like you, they need to "Clone" the repository. This creates a perfect copy of your folders, the index.html, and the main.py on their own computers.

Here is the exact guide you can send to them:

Step 1: The Initial Clone
Tell your groupmates to follow these steps:

Open VS Code.

Press Ctrl + Shift + P (or Cmd + Shift + P on Mac) and type "Git: Clone".

Paste the GitHub URL of your project.

Select a folder on their computer where they want to save it.

When asked, click "Open".

Step 2: Install the "Engine" (Python)
Since you are using FastAPI, they need the same libraries you installed:

Open the Terminal in VS Code (Ctrl +  `).

Type this command to install the requirements:

Bash

pip install fastapi uvicorn
Step 3: Running the Project
They need to run the "Brain" and the "Face" separately:

The Brain: In the terminal, type:

Bash

cd backend
python main.py
The Face: Go to the frontend folder, right-click index.html, and select "Open with Live Server" (or just double-click the file in their file explorer).

Step 4: Keeping it Updated (The Most Important Part)
Since you are the one making changes, they need to know how to get your new code. Tell them:

Whenever you say "I updated the code!", they need to go to the Source Control tab (the blue icon) in VS Code.

Click the "..." (three dots) and select Pull.

This will "pull" your latest index.html and main.py onto their laptop instantly.

Troubleshooting for Groupmates
The "Images" Issue: Remind them that GitHub usually doesn't save the images if they are too large or if you didn't commit them. If their dashboard shows "Loading Mock Feed," they need to make sure they also have the mock_images folder with the 3 pictures on their own laptop!

Would you like me to write a README.md file for your GitHub? This acts as a "Manual" that appears on your GitHub homepage so your groupmates (and your teacher) know exactly how to run the project.
